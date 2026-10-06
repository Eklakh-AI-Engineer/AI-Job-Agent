import os

os.environ.setdefault("APP_ENV", "development")

from fastapi.testclient import TestClient

from app.main import app


def test_root_exposes_security_headers():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_production_docs_are_configured_outside_default_schema():
    assert app.openapi_url == "/openapi.json"
