"""
backend/app/core/embeddings.py

Embedding provider abstraction for semantic search.
Supports OpenAI, local models (via sentence-transformers), and Cohere.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

# v1 storage/search contract. The database column is VECTOR(1536), so every
# document and query embedding must use this exact dimensionality.
EMBEDDING_VECTOR_DIMENSION = 1536
DEFAULT_EMBEDDING_PROVIDER = "openai"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: List[List[float]]
    model: str
    dimensions: int
    tokens_used: int
    cost_usd: float
    latency_ms: float


def validate_embedding_dimensions(dimensions: int, *, model_name: str) -> None:
    """Fail closed when a provider cannot satisfy the v1 pgvector contract."""
    if dimensions != EMBEDDING_VECTOR_DIMENSION:
        raise ValueError(
            f"Embedding contract violation: model '{model_name}' produces "
            f"{dimensions} dimensions; v1 requires {EMBEDDING_VECTOR_DIMENSION}. "
            "Regenerate the vector schema before using a different dimension."
        )


def validate_embedding_result(result: EmbeddingResult) -> None:
    """Validate both provider metadata and actual vector lengths."""
    validate_embedding_dimensions(result.dimensions, model_name=result.model)
    if len(result.embeddings) == 0:
        return
    actual_dimensions = {len(vector) for vector in result.embeddings}
    if actual_dimensions != {EMBEDDING_VECTOR_DIMENSION}:
        raise ValueError(
            f"Embedding payload dimension mismatch for model '{result.model}': "
            f"got {sorted(actual_dimensions)}, expected {EMBEDDING_VECTOR_DIMENSION}."
        )


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Output dimensions of the embedding."""
        pass
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a list of texts."""
        pass
    
    def _chunk_texts(self, texts: List[str], max_tokens: int = 8000) -> List[List[str]]:
        """Split texts into chunks that fit within token limits."""
        # Simple word-based chunking (approximate)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for text in texts:
            text_tokens = len(text.split()) * 1.3  # Rough estimate
            if current_tokens + text_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [text]
                current_tokens = text_tokens
            else:
                current_chunk.append(text)
                current_tokens += text_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider (text-embedding-3-small/large, ada-002)."""
    
    # Pricing per 1M tokens (as of 2024)
    PRICING = {
        "text-embedding-3-small": 0.020,  # $0.020 per 1M tokens
        "text-embedding-3-large": 0.130,  # $0.130 per 1M tokens
        "text-embedding-ada-002": 0.100,  # $0.100 per 1M tokens
    }
    
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.max_retries = max_retries
        self.timeout = timeout
        
        if model not in self.DIMENSIONS:
            raise ValueError(f"Unknown model: {model}. Supported: {list(self.DIMENSIONS.keys())}")
    
    @property
    def model_name(self) -> str:
        return self.model
    
    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS[self.model]
    
    async def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings using OpenAI API."""
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Prepare request
        data = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=data,
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # Extract embeddings
                    embeddings = [item["embedding"] for item in result["data"]]
                    
                    # Calculate tokens and cost
                    tokens_used = result["usage"]["total_tokens"]
                    cost_per_million = self.PRICING.get(self.model, 0)
                    cost_usd = (tokens_used / 1_000_000) * cost_per_million
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    logger.info(
                        f"Generated {len(embeddings)} embeddings "
                        f"({tokens_used} tokens, ${cost_usd:.6f}, {latency_ms:.0f}ms)"
                    )
                    
                    return EmbeddingResult(
                        embeddings=embeddings,
                        model=self.model,
                        dimensions=self.dimensions,
                        tokens_used=tokens_used,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                    )
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limit
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError("Max retries exceeded")


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere embedding provider."""
    
    PRICING = {
        "embed-english-v3.0": 0.100,  # $0.10 per 1M tokens
        "embed-multilingual-v3.0": 0.100,
        "embed-english-light-v3.0": 0.020,
    }
    
    DIMENSIONS = {
        "embed-english-v3.0": 1024,
        "embed-multilingual-v3.0": 1024,
        "embed-english-light-v3.0": 384,
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "embed-english-v3.0",
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError("COHERE_API_KEY not configured")
        
        self.model = model
        self.base_url = base_url or "https://api.cohere.ai/v1"
        self.max_retries = max_retries
        self.timeout = timeout
        
        if model not in self.DIMENSIONS:
            raise ValueError(f"Unknown model: {model}. Supported: {list(self.DIMENSIONS.keys())}")
    
    @property
    def model_name(self) -> str:
        return self.model
    
    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS[self.model]
    
    async def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings using Cohere API."""
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "texts": texts,
            "input_type": "search_document",
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        f"{self.base_url}/embed",
                        headers=headers,
                        json=data,
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    embeddings = result["embeddings"]
                    tokens_used = result.get("meta", {}).get("billed_units", {}).get("input_tokens", 0)
                    
                    cost_per_million = self.PRICING.get(self.model, 0)
                    cost_usd = (tokens_used / 1_000_000) * cost_per_million
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    logger.info(
                        f"Generated {len(embeddings)} embeddings "
                        f"({tokens_used} tokens, ${cost_usd:.6f}, {latency_ms:.0f}ms)"
                    )
                    
                    return EmbeddingResult(
                        embeddings=embeddings,
                        model=self.model,
                        dimensions=self.dimensions,
                        tokens_used=tokens_used,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                    )
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError("Max retries exceeded")


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: Optional[str] = None,
        batch_size: int = 32,
    ):
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model = None
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    @property
    def dimensions(self) -> int:
        # Load model to get dimensions if not loaded
        if self._model is None:
            self._load_model()
        return self._model.get_sentence_embedding_dimension()
    
    def _load_model(self):
        """Lazy load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            if self._device is None:
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self._model = SentenceTransformer(self._model_name, device=self._device)
            logger.info(f"Loaded local embedding model: {self._model_name} on {self._device}")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers torch"
            )
    
    async def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings using local model."""
        if self._model is None:
            self._load_model()
        
        start_time = time.time()
        
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist()
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Generated {len(embeddings)} local embeddings "
            f"({latency_ms:.0f}ms, free)"
        )
        
        return EmbeddingResult(
            embeddings=embeddings,
            model=self._model_name,
            dimensions=self.dimensions,
            tokens_used=0,  # Not applicable for local
            cost_usd=0.0,
            latency_ms=latency_ms,
        )


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""
    
    @staticmethod
    def create(provider: str = "openai", **kwargs) -> EmbeddingProvider:
        """Create an embedding provider by name."""
        providers = {
            "openai": OpenAIEmbeddingProvider,
            "cohere": CohereEmbeddingProvider,
            "local": LocalEmbeddingProvider,
        }
        
        if provider not in providers:
            raise ValueError(f"Unknown provider: {provider}. Supported: {list(providers.keys())}")
        
        instance = providers[provider](**kwargs)
        validate_embedding_dimensions(instance.dimensions, model_name=instance.model_name)
        return instance
    
    @staticmethod
    def create_from_env() -> EmbeddingProvider:
        """Create provider from environment variables."""
        provider_type = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        
        if provider_type == "openai":
            return EmbeddingProviderFactory.create(
                "openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL),
            )
        elif provider_type == "cohere":
            return EmbeddingProviderFactory.create(
                "cohere",
                api_key=os.getenv("COHERE_API_KEY"),
                model=os.getenv("COHERE_EMBEDDING_MODEL", "embed-english-v3.0"),
            )
        elif provider_type == "local":
            return EmbeddingProviderFactory.create(
                "local",
                model_name=os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            )
        else:
            raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider_type}")


# Global provider instance (lazy initialization)
_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """Get or create the global embedding provider."""
    global _provider
    if _provider is None:
        _provider = EmbeddingProviderFactory.create_from_env()
    return _provider


def set_embedding_provider(provider: EmbeddingProvider) -> None:
    """Set a test/provider override after enforcing the v1 contract."""
    validate_embedding_dimensions(provider.dimensions, model_name=provider.model_name)
    global _provider
    _provider = provider


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Convenience function to generate embeddings using global provider."""
    provider = get_embedding_provider()
    result = await provider.embed(texts)
    validate_embedding_result(result)
    return result.embeddings


def validate_embedding_configuration() -> None:
    """Validate configured model/dimension compatibility without API calls."""
    provider_type = os.getenv("EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER).lower()
    if provider_type == "openai":
        model = os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL)
        dimensions = OpenAIEmbeddingProvider.DIMENSIONS.get(model)
        if dimensions is None:
            raise ValueError(f"Unknown OpenAI embedding model: {model}")
    elif provider_type == "cohere":
        model = os.getenv("COHERE_EMBEDDING_MODEL", "embed-english-v3.0")
        dimensions = CohereEmbeddingProvider.DIMENSIONS.get(model)
        if dimensions is None:
            raise ValueError(f"Unknown Cohere embedding model: {model}")
    elif provider_type == "local":
        model = os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        # The local provider determines dimensions from the loaded model. Keep
        # startup validation conservative for known bundled/default models.
        if model == "sentence-transformers/all-MiniLM-L6-v2":
            dimensions = 384
        else:
            raise ValueError(
                "Local embedding model dimensions cannot be validated without loading the model; "
                "use the v1 OpenAI contract or add an explicit 1536-dimension local model mapping."
            )
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider_type}")
    validate_embedding_dimensions(dimensions, model_name=model)


def compute_text_hash(text: str) -> str:
    """Compute SHA256 hash of text for caching."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]