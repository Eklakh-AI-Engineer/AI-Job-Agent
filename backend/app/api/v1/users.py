"""
backend/app/api/v1/users.py

Endpoints for the authenticated user's own profile.

There is deliberately no "list all users" or "get user by id" endpoint: user
records are private to their owner, and administrative listing belongs to a
separate admin surface that does not exist yet.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.errors import UserNotFoundError
from app.services.user_service import update_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead, summary="Get the current user")
async def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    """Return the profile of the authenticated user."""
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead, summary="Update the current user")
async def update_current_user(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Apply a partial update to the authenticated user's profile."""
    try:
        user = await update_user(db, current_user, payload)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return UserRead.model_validate(user)
