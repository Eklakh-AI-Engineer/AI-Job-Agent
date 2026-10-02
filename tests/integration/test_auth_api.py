"""
Integration tests for the authentication endpoints.

These assert the HTTP contract: status codes, token issuance, and — most
importantly — that every failure path fails closed without leaking whether an
account exists.
"""


async def test_register_returns_created_user_without_secrets(api_client):
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "supersecret123", "full_name": "Ada"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["full_name"] == "Ada"
    assert body["is_active"] is True
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_normalises_email(api_client):
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "  Mixed.Case@Example.com  ", "password": "supersecret123"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "mixed.case@example.com"


async def test_register_rejects_duplicate_email(api_client, registered_user):
    credentials, _ = registered_user
    response = await api_client.post("/api/v1/auth/register", json=credentials)
    assert response.status_code == 409, response.text


async def test_register_rejects_short_password(api_client):
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert response.status_code == 422, response.text


async def test_register_rejects_malformed_email(api_client):
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "supersecret123"},
    )
    assert response.status_code == 422, response.text


async def test_login_returns_bearer_token(api_client, registered_user):
    credentials, _ = registered_user
    response = await api_client.post("/api/v1/auth/login", json=credentials)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert len(body["access_token"].split(".")) == 3  # header.payload.signature


async def test_login_rejects_wrong_password(api_client, registered_user):
    credentials, _ = registered_user
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": "definitely-wrong"},
    )
    assert response.status_code == 401, response.text


async def test_login_error_is_identical_for_unknown_email(api_client, registered_user):
    """Unknown email and wrong password must be indistinguishable."""
    credentials, _ = registered_user

    wrong_password = await api_client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": "definitely-wrong"},
    )
    unknown_email = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": credentials["password"]},
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


async def test_login_rejects_disabled_account(api_client, db_session, registered_user):
    from sqlalchemy import select

    from app.models.user import User

    credentials, created = registered_user

    # Disable the account out-of-band: there is no admin API yet.
    result = await db_session.execute(select(User).where(User.id == created["id"]))
    user = result.scalar_one()
    user.is_active = False
    await db_session.commit()

    response = await api_client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 403, response.text


async def test_protected_route_requires_token(api_client):
    response = await api_client.get("/api/v1/users/me")
    assert response.status_code == 401, response.text


async def test_protected_route_rejects_malformed_token(api_client):
    response = await api_client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401, response.text


async def test_protected_route_rejects_token_without_bearer_prefix(api_client, auth_headers):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    response = await api_client.get("/api/v1/users/me", headers={"Authorization": token})
    assert response.status_code == 401, response.text
