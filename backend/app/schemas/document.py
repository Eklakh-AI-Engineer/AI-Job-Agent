"""
backend/app/schemas/document.py

Request/response schemas for generated documents.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentGenerateRequest(BaseModel):
    """Payload for generating a document for a job."""

    job_id: int = Field(..., description="Job posting id to tailor the document to.")
    doc_type: str = Field(
        ...,
        description="Type of document: 'resume' or 'cover_letter'.",
    )
    store_artifact: bool = Field(
        True, description="Persist the rendered artifact to storage."
    )


class DocumentRead(BaseModel):
    """A generated document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_posting_id: int
    doc_type: str
    status: str
    version: int
    content: str
    meta: Optional[Dict[str, Any]] = None
    used_claim_ids: Optional[List[str]] = None
    storage_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentList(BaseModel):
    """List of generated documents."""

    items: List[DocumentRead] = Field(default_factory=list)
    total: int = 0


class DocumentStatusUpdate(BaseModel):
    """Update a document's review status."""

    status: str = Field(..., description="New status: 'approved' or 'rejected'.")


class DocumentContentUpdate(BaseModel):
    """Apply a manual edit to a document."""

    content: str = Field(..., min_length=1, description="New document body.")


class ATSAnalysisResponse(BaseModel):
    """ATS analysis for a document against its job."""

    score: float
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    coverage_ratio: float
    recommendations: List[str] = Field(default_factory=list)