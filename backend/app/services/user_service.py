"""
backend/app/services/user_service.py

User business logic: registration, lookup, authentication, profile updates.

Passwords are hashed at the boundary of this module and never leave it in
plain text. Authentication failures always raise the same
:class:`AuthenticationError` so the API cannot leak whether an email exists.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.errors import (
    AuthenticationError,
    InactiveUserError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Return the user with ``user_id``, or None."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Return the user with ``email`` (case-insensitive), or None."""
    normalized = (email or "").strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    """
    Register a new user.

    Raises:
        UserAlreadyExistsError: if the email is already registered.
    """
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise UserAlreadyExistsError("An account with this email already exists")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """
    Verify credentials and return the authenticated user.

    Raises:
        AuthenticationError: for unknown email, wrong password, or empty input.
        InactiveUserError: if the account exists but is disabled.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        # Same error as a wrong password: never reveal account existence.
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise InactiveUserError("This account is disabled")

    return user


async def update_user(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    """
    Apply a partial profile update.

    Only fields explicitly present in ``payload`` are written, so a caller
    omitting ``full_name`` does not clear it.

    Raises:
        UserNotFoundError: if ``user`` is None.
    """
    if user is None:
        raise UserNotFoundError("User not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user
