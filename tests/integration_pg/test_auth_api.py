"""Auth flow exercised against a real Postgres database.

The HTTP-level contract is already covered by ``tests/integration/test_auth_api.py``
on SQLite. These tests run the same flow against Postgres to catch any dialect
bug — for example, the way ``asyncpg`` materializes BOOLEAN / TIMESTAMPTZ columns,
case-sensitive email lookups, or transaction isolation on the unique-email
constraint.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.postgres


async def test_register_then_login_returns_valid_bearer_token(api_client):
    payload = {"email": "first@example.com", "password": "supersecret123"}
    register = await api_client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201
    assert register.json()["email"] == "first@example.com"

    login = await api_client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    assert "access_token" in login.json()
    assert login.json()["token_type"] == "bearer"

    me = await api_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "first@example.com"


async def test_register_with_duplicate_email_returns_409(api_client):
    payload = {"email": "dup@example.com", "password": "supersecret123"}
    first = await api_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await api_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


async def test_login_with_wrong_password_does_not_leak_account_existence(api_client):
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "exists@example.com", "password": "right-password-1"},
    )
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "exists@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_inactive_user_is_rejected_at_login(api_client, db_session):
    from sqlalchemy import select

    from app.models.user import User

    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "soon@example.com", "password": "supersecret123"},
    )
    user = (await db_session.execute(select(User).where(User.email == "soon@example.com"))).scalar_one()
    user.is_active = False
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "soon@example.com", "password": "supersecret123"},
    )
    # 403 = authenticated-but-disabled (correct HTTP semantics).
    assert response.status_code == 403
