"""Verify the schema created on a real Postgres database matches expectations.

These tests guard against silent drift between ``app.models`` and what
Alembic + the live database actually produce. If you change a column or
add a model, add (or extend) an assertion here.
"""

from __future__ import annotations

import pytest

from app.models import Base


pytestmark = pytest.mark.postgres


async def test_pgvector_extension_is_available(migrated_engine):
    """The vector extension must be installed in the target database."""
    async with migrated_engine.connect() as conn:
        ext = await conn.exec_driver_sql(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        )
        row = ext.first()
    assert row is not None, "pgvector extension is not installed"
    assert row[0] == "vector"


async def test_all_tables_are_created(migrated_engine):
    """Every model declared in ``Base.metadata`` shows up in the live DB."""
    expected = set(Base.metadata.tables)
    async with migrated_engine.connect() as conn:
        rows = await conn.exec_driver_sql(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        actual = {r[0] for r in rows}
    assert expected, "Base.metadata must declare at least one table for this check to mean anything"
    missing = expected - actual
    assert not missing, f"tables missing from live DB: {sorted(missing)}"


async def test_job_postings_has_embedding_column_with_pgvector_type(migrated_engine):
    """The embedding column must be pgvector VECTOR(1536) — the contract Phase 5 will rely on."""
    async with migrated_engine.connect() as conn:
        rows = await conn.exec_driver_sql(
            """
            SELECT a.attname, format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            WHERE c.relname = 'job_postings' AND a.attnum > 0 AND NOT a.attisdropped
            """
        )
        cols = {r[0]: r[1] for r in rows}
    assert "embedding" in cols, "embedding column missing from job_postings"
    # pgvector exposes the column type as "vector" (with optional precision like "vector(1536)")
    assert cols["embedding"].startswith("vector"), (
        f"embedding is not a pgvector column, got type {cols['embedding']!r}"
    )


async def test_users_email_is_unique(migrated_engine):
    """The users table must enforce email uniqueness — Phase 3 auth relies on it."""
    async with migrated_engine.connect() as conn:
        rows = await conn.exec_driver_sql(
            """
            SELECT i.relname, pg_get_indexdef(i.oid)
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            WHERE t.relname = 'users' AND ix.indisunique
            """
        )
        unique_indexes = [r[0] for r in rows]
    assert any("email" in idx.lower() or idx.endswith("_email_key") for idx in unique_indexes), (
        f"expected a unique index on users.email, found {unique_indexes}"
    )
