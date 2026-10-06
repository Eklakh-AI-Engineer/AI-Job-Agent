"""
backend/app/schemas/application.py

Request/response schemas for the application workflow.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    """Create an application for a job."""

    job_id: int = Field(..., description="Job posting id.")
    match_score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Optional precomputed fit score."
    )


class ApplicationRead(BaseModel):
    """An application record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_posting_id: int
    status: str
    match_score: Optional[float] = None
    tailored_resume_s3_key: Optional[str] = None
    cover_letter_s3_key: Optional[str] = None
    approved_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    last_error: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApplicationList(BaseModel):
    """List of applications."""

    items: List[ApplicationRead] = Field(default_factory=list)
    total: int = 0


class ApplicationTransitionRequest(BaseModel):
    """Request a guarded status transition."""

    to_status: str = Field(
        ...,
        description="Target status: Matched, Approved, Applied, or Rejected.",
    )
    reason: Optional[str] = Field(None, max_length=1024)
    idempotency_key: Optional[str] = Field(
        None,
        max_length=255,
        description=(
            "Required for Applied transitions. Replaying the same key is a no-op."
        ),
    )


class ApplicationEventRead(BaseModel):
    """An immutable audit-log event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    from_status: Optional[str] = None
    to_status: str
    actor: str
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    event_meta: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class ApplicationEventList(BaseModel):
    """Audit-log history for an application."""

    items: List[ApplicationEventRead] = Field(default_factory=list)
    total: int = 0


class ApplicationSubmitRequest(BaseModel):
    """Request to prepare/submit an application via browser automation."""

    dry_run: bool = Field(
        True,
        description=(
            "If true (default), pre-fill the form and capture evidence without "
            "clicking submit. Set false to actually submit (requires Approved)."
        ),
    )


class ApplicationSubmitResponse(BaseModel):
    """Result of a submission attempt."""

    success: bool
    dry_run: bool
    ats: str
    apply_url: str
    fields_filled: Dict[str, str] = Field(default_factory=dict)
    evidence_paths: List[str] = Field(default_factory=list)
    message: str = ""
    error: Optional[str] = None
    application_id: int
    application_status: str