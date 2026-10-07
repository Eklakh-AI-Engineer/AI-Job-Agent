"""Regression tests for Celery embedding task helper wiring."""

from types import SimpleNamespace

import pytest

import app.tasks.embeddings as tasks


class _FakeQuery:
    def where(self, _condition):
        return self


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _query):
        job = SimpleNamespace(id=101, title="AI Engineer")
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [job]))


class _FakeProvider:
    async def embed(self, texts):
        assert texts == ["AI Engineer text"]
        return SimpleNamespace(
            embeddings=[[0.1, 0.2]],
            model="test-model",
            dimensions=2,
        )


@pytest.mark.asyncio
async def test_regenerate_embeddings_uses_lazy_dependency_helpers(monkeypatch):
    """The regeneration path must not depend on undefined globals."""

    class _FakeJob:
        id = SimpleNamespace(in_=lambda _values: object())

    updates = []

    async def _update_job_embedding(_db, job_id, embedding):
        updates.append((job_id, embedding))

    monkeypatch.setattr(tasks, "_get_db_session", lambda: _FakeSession)
    monkeypatch.setattr(tasks, "_get_job_model", lambda: _FakeJob)
    monkeypatch.setattr(
        tasks,
        "_get_embedding_service",
        lambda: {
            "build_job_text": lambda job: "AI Engineer text",
            "update_job_embedding": _update_job_embedding,
        },
    )
    monkeypatch.setattr(tasks, "get_embedding_provider", lambda: _FakeProvider())

    import sqlalchemy

    monkeypatch.setattr(sqlalchemy, "select", lambda _model: _FakeQuery())

    result = await tasks._regenerate_embeddings_async([101], None)

    assert result["processed"] == 1
    assert result["succeeded"] == 1
    assert result["failed"] == 0
    assert updates == [(101, [0.1, 0.2])]
