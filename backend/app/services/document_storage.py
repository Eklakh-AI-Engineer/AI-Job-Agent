"""Artifact storage abstraction for generated documents."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentStorage(ABC):
    """Abstract storage for text and binary document artifacts."""

    @abstractmethod
    async def put(self, key: str, content: str, content_type: str = "text/plain") -> str:
        """Store text content."""

    async def put_bytes(
        self, key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Store binary content. Backends used for artifacts override this."""
        raise NotImplementedError("Binary artifact storage is not implemented")

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Retrieve text content."""

    async def get_bytes(self, key: str) -> Optional[bytes]:
        """Retrieve binary content."""
        raise NotImplementedError("Binary artifact storage is not implemented")

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a stored object."""


class LocalFilesystemStorage(DocumentStorage):
    """Filesystem-backed storage for development and single-node deployments."""

    def __init__(self, root: str = "data/documents"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        if key.startswith(("/", "\\")) or ".." in key.split("/"):
            raise ValueError(f"Invalid storage key: {key}")
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"Invalid storage key: {key}")
        return path

    async def put(self, key: str, content: str, content_type: str = "text/plain") -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return key

    async def put_bytes(
        self, key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    async def get(self, key: str) -> Optional[str]:
        path = self._path_for(key)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    async def get_bytes(self, key: str) -> Optional[bytes]:
        path = self._path_for(key)
        if not path.is_file():
            return None
        return path.read_bytes()

    async def delete(self, key: str) -> bool:
        path = self._path_for(key)
        if path.is_file():
            path.unlink()
            return True
        return False


class S3Storage(DocumentStorage):
    """S3-compatible object storage."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "documents",
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        self.endpoint_url = endpoint_url
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv(
            "AWS_SECRET_ACCESS_KEY"
        )

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def _client(self):
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3 document storage. "
                "Install with: pip install boto3"
            ) from exc
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    async def put(self, key: str, content: str, content_type: str = "text/plain") -> str:
        return await self.put_bytes(key, content.encode("utf-8"), content_type)

    async def put_bytes(
        self, key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        import asyncio
        full_key = self._full_key(key)
        client = self._client()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.put_object(
                Bucket=self.bucket,
                Key=full_key,
                Body=content,
                ContentType=content_type,
            ),
        )
        return full_key

    async def get(self, key: str) -> Optional[str]:
        payload = await self.get_bytes(key)
        return payload.decode("utf-8") if payload is not None else None

    async def get_bytes(self, key: str) -> Optional[bytes]:
        import asyncio
        full_key = self._full_key(key)
        client = self._client()
        loop = asyncio.get_event_loop()

        def _get() -> Optional[bytes]:
            try:
                obj = client.get_object(Bucket=self.bucket, Key=full_key)
                return obj["Body"].read()
            except client.exceptions.NoSuchKey:
                return None

        return await loop.run_in_executor(None, _get)

    async def delete(self, key: str) -> bool:
        import asyncio
        full_key = self._full_key(key)
        client = self._client()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: client.delete_object(Bucket=self.bucket, Key=full_key)
        )
        return True


_storage: Optional[DocumentStorage] = None


def get_document_storage() -> DocumentStorage:
    """Get or create the configured document storage backend."""
    global _storage
    if _storage is not None:
        return _storage

    backend = os.getenv("DOCUMENT_STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        bucket = os.getenv("DOCUMENT_STORAGE_BUCKET")
        if not bucket:
            raise ValueError("DOCUMENT_STORAGE_BUCKET is required for S3 storage")
        _storage = S3Storage(
            bucket=bucket,
            prefix=os.getenv("DOCUMENT_STORAGE_PREFIX", "documents"),
            endpoint_url=os.getenv("DOCUMENT_STORAGE_ENDPOINT"),
        )
    else:
        _storage = LocalFilesystemStorage(
            root=os.getenv("DOCUMENT_STORAGE_ROOT", "data/documents")
        )
    return _storage


def set_document_storage(storage: DocumentStorage) -> None:
    """Override the global storage backend for testing."""
    global _storage
    _storage = storage


def build_document_key(
    user_id: int, job_id: int, doc_type: str, version: int, extension: str = "txt"
) -> str:
    """Build a deterministic storage key for a generated artifact."""
    extension = extension.lstrip(".")
    return f"users/{user_id}/jobs/{job_id}/{doc_type}/v{version}.{extension}"
