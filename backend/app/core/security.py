"""
backend/app/core/security.py

Password hashing and JSON Web Token handling for the API layer (Phase 3).

Design rules
------------
- Passwords are hashed with bcrypt. Plain-text passwords are never stored,
  logged, or returned by any API response.
- Access tokens are signed with the configured ``jwt_secret`` and carry an
  explicit ``typ`` claim so a token issued for another purpose can never be
  replayed as an access token.
- Token decoding is strict: expiry, signature, algorithm, type and subject are
  all validated. Any failure raises :class:`TokenError`, never returns ``None``,
  so callers cannot accidentally treat a bad token as anonymous-but-valid.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt only; ``deprecated="auto"`` lets us migrate schemes later without
# invalidating existing hashes.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_TYPE = "access"


class TokenError(ValueError):
    """Raised when a token is missing, malformed, expired, or of the wrong type."""


def hash_password(password: str) -> str:
    """Hash a plain-text password for storage."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored hash.

    Returns False (never raises) for malformed input, so login endpoints can
    fail closed with a generic 401 instead of leaking internal errors.
    """
    if not isinstance(plain_password, str) or not plain_password:
        return False
    if not isinstance(hashed_password, str) or not hashed_password:
        return False
    try:
        return bool(pwd_context.verify(plain_password, hashed_password))
    except ValueError:
        # Raised by passlib when the stored hash is not a recognised bcrypt hash.
        return False


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a signed access token for ``subject`` (the user id).

    ``extra_claims`` is merged last but may never override the reserved
    ``sub``, ``exp``, ``iat`` or ``typ`` claims.
    """
    if not subject:
        raise ValueError("token subject is required")

    settings = get_settings()
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_expire_minutes)
    )

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": issued_at,
        "exp": expires_at,
        "typ": ACCESS_TOKEN_TYPE,
    }
    if extra_claims:
        for reserved in ("sub", "exp", "iat", "typ"):
            extra_claims.pop(reserved, None)
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate an access token.

    Raises:
        TokenError: if the token is expired, badly signed, of the wrong type,
            or missing a subject.
    """
    if not isinstance(token, str) or not token.strip():
        raise TokenError("Token is missing")

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        # Covers InvalidSignatureError, DecodeError, InvalidTokenError, etc.
        raise TokenError("Invalid token") from exc

    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise TokenError("Invalid token type")
    if not payload.get("sub"):
        raise TokenError("Token is missing a subject")

    return payload
