"""
backend/app/api/deps.py

Shared FastAPI dependencies for the v1 API.

Authentication is bearer-token based: clients obtain a token from
``POST /api/v1/auth/login`` and send it as ``Authorization: Bearer <token>``.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import TokenError, decode_access_token
from app.models.user import User
from app.services.errors import AuthenticationError, InactiveUserError
from app.services.user_service import get_user_by_id

settings = get_settings()

# auto_error=True would return 403 instead of 401 for a missing header; we want
# a proper 401 with the WWW-Authenticate challenge, so credentials are optional
# here and validated below.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_token_payload(
    token: str | None = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    Decode the bearer token from the request.

    Raises:
        HTTPException: 401 if the token is absent, expired, or invalid.
    """
    if not token:
        raise CREDENTIALS_EXCEPTION
    try:
        return decode_access_token(token)
    except TokenError as exc:
        # Surface the reason without exposing the secret or the payload.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    payload: Dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from the token subject.

    Raises:
        HTTPException: 401 if the token is valid but the user no longer exists
            or the account is disabled.
    """
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CREDENTIALS_EXCEPTION from exc

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


def require_authentication_error(
    exc: AuthenticationError | InactiveUserError,
) -> HTTPException:
    """Map a service-layer auth failure onto the correct HTTP response."""
    if isinstance(exc, InactiveUserError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=str(exc),
        headers={"WWW-Authenticate": "Bearer"},
    )
