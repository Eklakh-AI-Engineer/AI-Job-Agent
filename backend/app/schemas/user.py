"""
backend/app/schemas/user.py

User request/response schemas.

The password field only ever appears on :class:`UserCreate` / :class:`UserLogin`
(input). No response schema exposes it, and :class:`UserRead` is built from ORM
objects via ``from_attributes`` so the hashed password is never serialised.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def _validate_password_strength(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"password must be at most {PASSWORD_MAX_LENGTH} characters")
    if value.strip() != value:
        raise ValueError("password must not start or end with whitespace")
    return value


class UserCreate(BaseModel):
    """Registration payload."""

    email: EmailStr = Field(
        ..., description="Unique email address used as the login identity."
    )
    password: str = Field(
        ..., description="Plain-text password; hashed before storage."
    )
    full_name: Optional[str] = Field(
        None, max_length=255, description="Optional display name."
    )

    _normalize_password = field_validator("password")(_validate_password_strength)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def _normalize_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class UserLogin(BaseModel):
    """Login payload."""

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Plain-text password.")

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserUpdate(BaseModel):
    """Partial update of the caller's own profile."""

    full_name: Optional[str] = Field(None, max_length=255, description="Display name.")
    profile_data: Optional[str] = Field(
        None,
        description="JSON-encoded candidate profile consumed by downstream agents.",
    )

    @field_validator("full_name")
    @classmethod
    def _normalize_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class UserRead(BaseModel):
    """User representation returned by the API. Never includes secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    #: JSON-encoded candidate profile. Only ever returned to the owning user.
    profile_data: Optional[str] = None
    created_at: Optional[datetime] = None
