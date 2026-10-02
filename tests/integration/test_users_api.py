"""
Integration tests for the user profile endpoints.
"""

from sqlalchemy import select

from app.models.user import User


async def test_read_current_user(api_client, auth_headers, registered_user):
    _, created = registered_user

    response = await api_client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == created["id"]
    assert body["email"] == "candidate@example.com"
    assert "hashed_password" not in body


async def test_read_current_user_requires_authentication(api_client):
    response = await api_client.get("/api/v1/users/me")
    assert response.status_code == 401, response.text


async def test_read_current_user_rejects_token_for_deleted_user(
    api_client, auth_headers, db_session, registered_user
):
    """A valid token must stop working once the account behind it is gone."""
    _, created = registered_user

    result = await db_session.execute(select(User).where(User.id == created["id"]))
    await db_session.delete(result.scalar_one())
    await db_session.commit()

    response = await api_client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 401, response.text


async def test_update_current_user(api_client, auth_headers):
    response = await api_client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"full_name": "Grace Hopper"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["full_name"] == "Grace Hopper"


async def test_update_current_user_is_partial(api_client, auth_headers, registered_user):
    """Omitting a field must leave it untouched."""
    _, created = registered_user

    response = await api_client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"profile_data": '{"target_roles": ["AI Engineer"]}'},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == created["email"]
    assert body["profile_data"] == '{"target_roles": ["AI Engineer"]}'


async def test_update_current_user_requires_authentication(api_client):
    response = await api_client.patch("/api/v1/users/me", json={"full_name": "Nobody"})
    assert response.status_code == 401, response.text
