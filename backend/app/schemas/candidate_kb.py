"""
backend/app/schemas/candidate_kb.py

Request/response schemas for the Candidate Knowledge Base API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CandidateKBSaveRequest(BaseModel):
    """Payload for creating/updating a user's Candidate KB."""

    data: Dict[str, Any] = Field(
        ...,
        description=(
            "Full CandidateKB document with keys: profile, skills, claims, "
            "experience, preferences. Validated against the CandidateKB schema."
        ),
    )
    change_note: Optional[str] = Field(
        None,
        max_length=512,
        description="Optional note explaining the change (stored in version history).",
    )


class CandidateKBValidateRequest(BaseModel):
    """Payload for validating a Candidate KB without saving it."""

    data: Dict[str, Any] = Field(..., description="CandidateKB document to validate.")


class CandidateKBValidateResponse(BaseModel):
    """Result of a KB validation request."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CandidateKBResponse(BaseModel):
    """
    A user's Candidate KB.

    By default restricted/undetermined evidence references are stripped.
    Set ``include_restricted=true`` (owner-only) to receive the full document.
    """

    model_config = ConfigDict(extra="allow")

    version: int
    is_active: bool
    change_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    #: The KB document itself (disclosure-filtered unless include_restricted).
    data: Dict[str, Any]


class CandidateKBVersionSummary(BaseModel):
    """Metadata for one KB version (without the full document)."""

    model_config = ConfigDict(from_attributes=True)

    version: int
    is_active: bool
    change_note: Optional[str] = None
    created_at: Optional[datetime] = None


class CandidateKBVersionList(BaseModel):
    """List of KB versions for the authenticated user."""

    items: List[CandidateKBVersionSummary] = Field(default_factory=list)
    total: int = 0


class CandidateKBDeleteResponse(BaseModel):
    """Result of deleting a user's KB."""

    deleted: int
    message: str = "Candidate KB deleted"