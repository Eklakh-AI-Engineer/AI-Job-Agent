"""
Unit tests for backend/app/services/user_service.py
"""

import pytest

from app.schemas.user import UserCreate, UserUpdate
from app.services.errors import (
    AuthenticationError,
    InactiveUserError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
)


def make_payload(email: str = "candidate@example.com", password: str = "supersecret123"):
    return UserCreate(email=email, password=password, full_name="  Ada Lovelace  ")


async def test_create_user_persists_and_hashes_password(db_session):
    user = await create_user(db_session, make_payload())

    assert user.id is not None
    assert user.email == "candidate@example.com"
    assert user.is_active is True
    assert user.full_name == "Ada Lovelace"
    # The hash must never equal the plain text, and must be a bcrypt hash.
    assert user.hashed_password != "supersecret123"
    assert user.hashed_password.startswith("$2b$")


async def test_create_user_is_case_insensitive_on_email(db_session):
    await create_user(db_session, make_payload(email="Mixed.Case@Example.com"))
    found = await get_user_by_email(db_session, "mixed.case@example.com")
    assert found is not None


async def test_create_user_rejects_duplicate_email(db_session):
    await create_user(db_session, make_payload())
    with pytest.raises(UserAlreadyExistsError):
        await create_user(db_session, make_payload())


async def test_get_user_by_id_returns_none_when_missing(db_session):
    assert await get_user_by_id(db_session, 12345) is None


async def test_get_user_by_email_returns_none_when_missing(db_session):
    assert await get_user_by_email(db_session, "nobody@example.com") is None


async def test_authenticate_user_returns_user_on_valid_credentials(db_session):
    created = await create_user(db_session, make_payload())
    user = await authenticate_user(db_session, "candidate@example.com", "supersecret123")
    assert user.id == created.id


async def test_authenticate_user_rejects_wrong_password(db_session):
    await create_user(db_session, make_payload())
    with pytest.raises(AuthenticationError):
        await authenticate_user(db_session, "candidate@example.com", "wrong-password")


async def test_authentication_error_message_is_identical_for_unknown_email(db_session):
    """
    Account-enumeration guard: an unknown email and a wrong password must be
    indistinguishable to the caller.
    """
    await create_user(db_session, make_payload())

    with pytest.raises(AuthenticationError) as wrong_password:
        await authenticate_user(db_session, "candidate@example.com", "nope")
    with pytest.raises(AuthenticationError) as unknown_email:
        await authenticate_user(db_session, "nobody@example.com", "supersecret123")

    assert str(wrong_password.value) == str(unknown_email.value)


async def test_authenticate_user_rejects_inactive_account(db_session):
    user = await create_user(db_session, make_payload())
    user.is_active = False
    await db_session.commit()

    with pytest.raises(InactiveUserError):
        await authenticate_user(db_session, "candidate@example.com", "supersecret123")


async def test_update_user_applies_only_supplied_fields(db_session):
    user = await create_user(db_session, make_payload())
    updated = await update_user(db_session, user, UserUpdate(full_name="Grace Hopper"))

    assert updated.full_name == "Grace Hopper"
    # Untouched fields must survive a partial update.
    assert updated.email == "candidate@example.com"


async def test_update_user_preserves_omitted_fields(db_session):
    user = await create_user(db_session, make_payload())
    await update_user(db_session, user, UserUpdate(profile_data='{"target_roles": []}'))

    # full_name was not part of the update payload and must be left alone.
    assert user.full_name == "Ada Lovelace"
    assert user.profile_data == '{"target_roles": []}'


async def test_update_user_rejects_missing_user(db_session):
    with pytest.raises(UserNotFoundError):
        await update_user(db_session, None, UserUpdate(full_name="Nobody"))
