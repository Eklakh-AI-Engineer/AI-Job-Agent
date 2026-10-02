"""Alembic migrations applied to a real Postgres database.

These are *synchronous* tests: ``alembic.command.upgrade`` runs its own asyncio
loop internally (see ``backend/alembic/env.py``), so calling it from inside a
running event loop deadlocks. Spawning a fresh subprocess per assertion makes
the boundary explicit and keeps each test independent of the pytest-asyncio
loop scope.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.postgres


def _run(cmd: list[str], env: dict[str, str], cwd: Path | None = None) -> str:
    """Run a subprocess and raise with full output on failure."""
    result = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"command {cmd!r} failed with code {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    return result.stdout


def _alembic_env(pg_database: str) -> dict[str, str]:
    """Build an env dict so ``alembic`` talks to the throwaway DB."""
    base, _, _ = os.environ["DATABASE_URL"].rpartition("/")
    url = f"{base}/{pg_database}"
    env = dict(os.environ)
    env["DATABASE_URL"] = url
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "backend")
    return env


@pytest.fixture
def alembic_subprocess_env(migrated_engine, pg_database_name: str) -> dict[str, str]:
    return _alembic_env(pg_database_name)


@pytest.fixture
def pg_database_name(migrated_engine) -> str:
    """Extract the DB name from the live engine URL so subprocess tests can reuse it."""
    return migrated_engine.url.database


def test_alembic_upgrade_head_creates_expected_tables(alembic_subprocess_env):
    """Drop everything, run ``alembic upgrade head``, verify the API models' tables exist."""
    from app.models import Base

    expected = set(Base.metadata.tables)
    assert expected, "Base.metadata must declare at least one table for this check to mean anything"

    backend_dir = Path(__file__).resolve().parents[2] / "backend"

    # Drop everything the test's create_all left behind.
    drop_script = (
        "import asyncio\n"
        "from sqlalchemy.ext.asyncio import create_async_engine\n"
        "from app.models import Base\n"
        f"DB = {alembic_subprocess_env['DATABASE_URL']!r}\n"
        "async def m():\n"
        "    e = create_async_engine(DB)\n"
        "    async with e.begin() as c:\n"
        "        await c.run_sync(Base.metadata.drop_all)\n"
        "asyncio.run(m())\n"
    )
    _run([sys.executable, "-c", drop_script], env=alembic_subprocess_env, cwd=backend_dir)

    _run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=alembic_subprocess_env,
        cwd=backend_dir,
    )

    script = (
        "import asyncio\n"
        "from sqlalchemy.ext.asyncio import create_async_engine\n"
        f"DB = {alembic_subprocess_env['DATABASE_URL']!r}\n"
        "async def m():\n"
        "    e = create_async_engine(DB)\n"
        "    async with e.connect() as c:\n"
        "        rows = await c.exec_driver_sql(\n"
        "            \"SELECT tablename FROM pg_tables WHERE schemaname = 'public'\"\n"
        "        )\n"
        "        names = {r[0] for r in rows}\n"
        "    print(','.join(sorted(names)))\n"
        "asyncio.run(m())\n"
    )
    out = _run([sys.executable, "-c", script], env=os.environ.copy(), cwd=backend_dir)
    actual = set(out.strip().split(",")) if out.strip() else set()

    missing = expected - actual
    assert not missing, f"tables Alembic did not create: {sorted(missing)}"


def test_alembic_downgrade_then_upgrade_is_idempotent(alembic_subprocess_env):
    """Downgrade to ``base``, then upgrade back — every model table reappears."""
    from app.models import Base

    backend_dir = Path(__file__).resolve().parents[2] / "backend"

    # Drop the test's create_all output so alembic starts from an empty DB.
    drop_script = (
        "import asyncio\n"
        "from sqlalchemy.ext.asyncio import create_async_engine\n"
        "from app.models import Base\n"
        f"DB = {alembic_subprocess_env['DATABASE_URL']!r}\n"
        "async def m():\n"
        "    e = create_async_engine(DB)\n"
        "    async with e.begin() as c:\n"
        "        await c.run_sync(Base.metadata.drop_all)\n"
        "asyncio.run(m())\n"
    )
    _run([sys.executable, "-c", drop_script], env=alembic_subprocess_env, cwd=backend_dir)

    _run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=alembic_subprocess_env,
        cwd=backend_dir,
    )
    _run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        env=alembic_subprocess_env,
        cwd=backend_dir,
    )

    script_after_downgrade = (
        "import asyncio\n"
        "from sqlalchemy.ext.asyncio import create_async_engine\n"
        f"DB = {alembic_subprocess_env['DATABASE_URL']!r}\n"
        "async def m():\n"
        "    e = create_async_engine(DB)\n"
        "    async with e.connect() as c:\n"
        "        rows = await c.exec_driver_sql(\n"
        "            \"SELECT tablename FROM pg_tables WHERE schemaname = 'public'\"\n"
        "        )\n"
        "        print(','.join(sorted({r[0] for r in rows})))\n"
        "asyncio.run(m())\n"
    )
    out = _run(
        [sys.executable, "-c", script_after_downgrade],
        env=os.environ.copy(),
        cwd=backend_dir,
    )
    after_downgrade = set(out.strip().split(",")) if out.strip() else set()
    assert "users" not in after_downgrade, "downgrade must drop users table"

    _run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=alembic_subprocess_env,
        cwd=backend_dir,
    )
    out2 = _run(
        [sys.executable, "-c", script_after_downgrade],
        env=os.environ.copy(),
        cwd=backend_dir,
    )
    after_upgrade = set(out2.strip().split(",")) if out2.strip() else set()
    assert "users" in after_upgrade, "re-upgrade must recreate users table"
