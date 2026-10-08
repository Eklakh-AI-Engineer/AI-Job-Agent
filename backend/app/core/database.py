from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()
database_url = settings.effective_database_url
parsed = urlparse(database_url)
is_transaction_pooler = parsed.port == 6543 or "pooler.supabase.com" in (parsed.hostname or "") and parsed.port == 6543

engine_kwargs = {
    "echo": settings.app_debug,
    "future": True,
}

if settings.is_production:
    # Serverless instances should not hold a large SQLAlchemy connection pool.
    engine_kwargs["poolclass"] = NullPool

if is_transaction_pooler:
    # Supabase transaction pooling does not support prepared statements.
    engine_kwargs["connect_args"] = {"statement_cache_size": 0}

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
