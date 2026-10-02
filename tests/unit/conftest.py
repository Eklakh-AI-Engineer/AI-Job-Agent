"""
Unit-test fixtures that need real database sessions.

Service functions take an ``AsyncSession``, so exercising them against a real
(SQLite) session is far more meaningful than mocking the ORM. SQLite is used
because these tests assert business rules, not SQL dialect behaviour.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base


def _build_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        future=True,
    )


@pytest_asyncio.fixture
async def db_session():
    """A session backed by a fresh, isolated in-memory database."""
    engine = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
