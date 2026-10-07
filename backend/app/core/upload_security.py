"""Security policy for files uploaded to external ATS forms."""

from __future__ import annotations

from pathlib import Path


class UnsafeUpload(ValueError):
    pass


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_SIGNATURES = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
}


def validate_upload(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise UnsafeUpload("Upload file does not exist")
    if candidate.is_symlink():
        raise UnsafeUpload("Symlink uploads are not allowed")
    suffix = candidate.suffix.casefold()
    if suffix not in ALLOWED_SIGNATURES:
        raise UnsafeUpload("Only PDF and DOCX uploads are allowed")
    size = candidate.stat().st_size
    if size <= 0 or size > MAX_UPLOAD_BYTES:
        raise UnsafeUpload("Upload size is outside the permitted range")
    with candidate.open("rb") as handle:
        signature = handle.read(5)
    expected = ALLOWED_SIGNATURES[suffix]
    if not signature.startswith(expected):
        raise UnsafeUpload("File signature does not match its extension")
    return candidate
