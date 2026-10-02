"""
Integration-test fixtures.

Two client flavours are provided on purpose:

``client``
    The real application with its real database configuration. Used for probes
    (``/``, ``/health``) that must exercise the production wiring, including
    the failure path when the database is unreachable.

``api_client``
    The same application with ``get_db`` swapped for a throwaway SQLite
    database. Used for resource endpoints (auth, users, jobs) so the suite is
    deterministic, needs no running PostgreSQL, and never depends on Alembic
    having been applied.

``api_client`` and ``db_session`` share one SQLite engine, so a test can mutate
state directly (for example, disabling an account) and then observe the effect
through the HTTP API.

The SQLite override exists because the API contract is what these tests assert,
not the database dialect. The pgvector ``embedding`` column is accepted by
SQLite as an opaque type name and is never read or written by the API.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base


def _build_sqlite_engine():
    # StaticPool keeps a single connection so the in-memory database survives
    # across sessions for the lifetime of the test.
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        future=True,
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """App under test with its real database configuration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def sqlite_db():
    """A fresh in-memory SQLite database with the schema created."""
    engine = _build_sqlite_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield engine, session_factory
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(sqlite_db):
    """A session on the same database the API client is pointed at."""
    _, session_factory = sqlite_db
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def api_client(sqlite_db):
    """App under test with ``get_db`` overridden to the shared SQLite database."""
    _, session_factory = sqlite_db

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
    """Register a user and return ``(credentials, created_user)``."""
    payload = {"email": "candidate@example.com", "password": "supersecret123"}
    response = await api_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload, response.json()


@pytest_asyncio.fixture
async def auth_headers(api_client, registered_user):
    """Log the registered user in and return an ``Authorization`` header dict."""
    credentials, _ = registered_user
    response = await api_client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
