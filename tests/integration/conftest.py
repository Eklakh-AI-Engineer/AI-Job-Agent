"""
Integration-test fixtures.
These require the FastAPI app and a running database.
They are DEFERRED — do not run these until the FastAPI layer is approved.
"""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    # Deferred: FastAPI app only usable once Phase 3 (API layer) is approved.
    from backend.app.main import app  # noqa: PLC0415
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
