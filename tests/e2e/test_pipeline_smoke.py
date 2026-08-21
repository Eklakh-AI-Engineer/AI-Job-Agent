"""
End-to-end smoke test placeholder.

Full pipeline e2e tests (discovery -> matching -> resume optimization ->
application assembly) will be implemented in Phase 4-6 once the
corresponding agents exist. This smoke test verifies the API is reachable
end-to-end, standing in for the full pipeline test until agents land.
"""
import pytest


@pytest.mark.asyncio
async def test_api_is_reachable(client):
    response = await client.get("/health")
    assert response.status_code == 200
