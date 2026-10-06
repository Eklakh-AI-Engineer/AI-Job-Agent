"""Regression tests for the v1 embedding storage/search contract."""

import pytest

from app.core.embeddings import (
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    EMBEDDING_VECTOR_DIMENSION,
    EmbeddingResult,
    OpenAIEmbeddingProvider,
    validate_embedding_configuration,
    validate_embedding_dimensions,
    validate_embedding_result,
)


def test_v1_embedding_dimension_is_1536():
    assert EMBEDDING_VECTOR_DIMENSION == 1536
    assert OpenAIEmbeddingProvider.DIMENSIONS[DEFAULT_OPENAI_EMBEDDING_MODEL] == 1536


@pytest.mark.parametrize(
    ("dimensions", "valid"),
    [(1536, True), (3072, False), (1024, False), (384, False)],
)
def test_embedding_dimension_contract(dimensions, valid):
    if valid:
        validate_embedding_dimensions(dimensions, model_name="test-model")
    else:
        with pytest.raises(ValueError, match="v1 requires 1536"):
            validate_embedding_dimensions(dimensions, model_name="test-model")


def test_embedding_result_rejects_wrong_payload_length():
    result = EmbeddingResult(
        embeddings=[[0.0] * 1024],
        model="invalid-model",
        dimensions=1024,
        tokens_used=0,
        cost_usd=0.0,
        latency_ms=0.0,
    )
    with pytest.raises(ValueError, match="v1 requires 1536"):
        validate_embedding_result(result)


def test_startup_configuration_accepts_default_openai_contract(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)
    validate_embedding_configuration()


def test_startup_configuration_rejects_non_1536_model(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    with pytest.raises(ValueError, match="v1 requires 1536"):
        validate_embedding_configuration()
