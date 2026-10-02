"""
Integration tests against a real PostgreSQL + pgvector database.

These tests are *opt-in*: they only run when ``DATABASE_URL`` is set and points
at a real Postgres server. The default ``pytest`` invocation skips them so
local development on a laptop without Postgres stays fast and hermetic.

Why a separate directory?
    ``tests/integration/`` exercises the FastAPI contract over HTTP using an
    in-memory SQLite database. SQLite accepts the ``VECTOR(1536)`` column as
    an opaque type, which keeps the unit-of-behaviour small and deterministic,
    but it cannot reproduce pgvector's coercion rules, type coercion, or
    extension requirements.

    Anything that must be true about *Postgres specifically* — the pgvector
    extension, ``CREATE EXTENSION``, the VECTOR column, transactional
    rollback semantics, real ``asyncpg`` typing, the Alembic migration
    history — lives here.

Run them explicitly:

    export DATABASE_URL=postgresql+asyncpg://aijobagent:aijobagent@localhost:5433/aijobagent_test
    pytest tests/integration_pg -m postgres

Or in CI, where the same command runs against the job's Postgres service.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        pytest.skip(
            "DATABASE_URL is not set — skipping real-Postgres integration tests",
            allow_module_level=True,
        )
    if not url.startswith(("postgresql+asyncpg://", "postgresql+psycopg://")):
        pytest.skip(
            f"DATABASE_URL must point at Postgres (got {url!r}); skipping",
            allow_module_level=True,
        )
    return url


# Resolve the URL at collection time so module-level skips surface immediately.
DATABASE_URL = _database_url()


def _admin_url() -> str:
    """Connection URL to the ``postgres`` maintenance DB for create/drop."""
    head, _, _ = DATABASE_URL.rpartition("/")
    return f"{head}/postgres"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def pg_schema(migrated_engine):
    """Per-test schema using SAVEPOINT rollback so each test starts clean."""
    # migrated_engine already created the schema; just yield it.
    yield migrated_engine


@pytest_asyncio.fixture
async def migrated_engine():
    """Function-scoped engine on a throwaway DB.

    A fresh DB per test would be too slow (CREATE DATABASE + extensions every
    test), so we keep the DB alive across tests and reset state by dropping
    and recreating the public-schema tables before each test.
    """
    base, _, _ = DATABASE_URL.rpartition("/")
    db_name = f"aijobagent_test_{uuid.uuid4().hex[:10]}"
    url = f"{base}/{db_name}"

    admin_engine = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await conn.exec_driver_sql(f'CREATE DATABASE "{db_name}"')

        engine = create_async_engine(url, future=True)
        async with engine.begin() as conn:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.run_sync(Base.metadata.create_all)
        try:
            yield engine
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
    finally:
        async with admin_engine.connect() as conn:
            await conn.exec_driver_sql(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
            )
            await conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{db_name}"')
        await admin_engine.dispose()


@pytest_asyncio.fixture
async def db_session(migrated_engine) -> AsyncSession:
    """A session against the migrated DB. Each test runs in a transaction
    that is rolled back at teardown so tests stay isolated.
    """
    session_factory = async_sessionmaker(bind=migrated_engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def api_client(migrated_engine) -> AsyncClient:
    """The real FastAPI app wired to the migrated Postgres engine."""
    session_factory = async_sessionmaker(bind=migrated_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def registered_user(api_client):
    """Register a user through the API and return ``(credentials, user_dict)``."""
    payload = {"email": "candidate@example.com", "password": "supersecret123"}
    response = await api_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload, response.json()


@pytest_asyncio.fixture
async def auth_headers(api_client, registered_user):
    """Bearer auth headers for the registered user."""
    credentials, _ = registered_user
    response = await api_client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


pytestmark = pytest.mark.postgres
