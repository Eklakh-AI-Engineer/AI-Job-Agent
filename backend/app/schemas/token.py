"""
backend/app/schemas/token.py

Authentication token schemas.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Response returned by the login endpoint."""

    access_token: str = Field(..., description="Signed JWT access token.")
    token_type: str = Field("bearer", description="Token scheme, always 'bearer'.")
    expires_in: int = Field(..., ge=1, description="Lifetime of the token, in seconds.")


class TokenPayload(BaseModel):
    """Decoded access-token claims exposed to the service layer."""

    sub: str = Field(..., description="Subject of the token: the user id.")
    exp: Optional[int] = Field(None, description="Expiry timestamp (Unix seconds).")
    typ: Optional[str] = Field(None, description="Token type, expected to be 'access'.")
