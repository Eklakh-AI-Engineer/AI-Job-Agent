"""
backend/app/api/v1/auth.py

Registration and login endpoints.

Both endpoints are intentionally vague on failure: registration returns 409 for
a duplicate email (unavoidable, the client is choosing an identity) while login
returns a single generic 401 for unknown email, wrong password, or disabled
account, so the API cannot be used to enumerate registered users.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_authentication_error
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import limiter
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.errors import (
    AuthenticationError,
    InactiveUserError,
    UserAlreadyExistsError,
)
from app.services.user_service import authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("5/minute")
async def register(
    request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserRead:
    """Create an account. Returns the created user without any credentials."""
    try:
        user = await create_user(db, payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return UserRead.model_validate(user)


@router.post(
    "/login", response_model=TokenResponse, summary="Exchange credentials for a token"
)
@limiter.limit("10/minute")
async def login(
    request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Authenticate and return a bearer token."""
    try:
        user = await authenticate_user(db, payload.email, payload.password)
    except (AuthenticationError, InactiveUserError) as exc:
        raise require_authentication_error(exc) from exc

    settings = get_settings()
    token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )
