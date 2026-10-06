"""
backend/app/schemas/job.py

Job posting and application-status schemas.

``JobPosting`` carries a 1536-dimension pgvector embedding. That column is
deliberately absent from these schemas: embeddings are an internal
implementation detail and must not leak through the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobPostingCreate(BaseModel):
    """Payload used to ingest a discovered job posting."""

    title: str = Field(..., max_length=255)
    company: str = Field(..., max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    job_description: str = Field(..., description="Full job description text.")
    url: str = Field(
        ..., max_length=1024, description="Canonical posting URL; must be unique."
    )
    source: str = Field(
        ..., max_length=100, description="Origin board, e.g. 'greenhouse'."
    )

    # Optional structured fields (surfaced from discovery / manual ingestion)
    source_job_id: Optional[str] = Field(None, max_length=255)
    application_url: Optional[str] = Field(None, max_length=1024)
    work_mode: Optional[str] = Field(None, max_length=50)
    posted_date: Optional[str] = Field(None, max_length=100)
    closing_date: Optional[str] = Field(None, max_length=100)
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    eligibility: Optional[str] = None
    compensation: Optional[str] = Field(None, max_length=512)

    @field_validator("title", "company", "location", "url", "source")
    @classmethod
    def _strip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class JobPostingRead(BaseModel):
    """Job posting representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: Optional[str] = None
    job_description: str
    url: str
    source: str

    # Extended fields surfaced for the agent UI (embedding remains internal)
    source_job_id: Optional[str] = None
    application_url: Optional[str] = None
    work_mode: Optional[str] = None
    posted_date: Optional[str] = None
    closing_date: Optional[str] = None
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    eligibility: Optional[str] = None
    compensation: Optional[str] = None

    created_at: Optional[datetime] = None


class JobPostingList(BaseModel):
    """Paginated collection of job postings."""

    items: List[JobPostingRead] = Field(default_factory=list)
    total: int = Field(0, ge=0, description="Total postings matching the filter.")
    limit: int = Field(0, ge=0)
    offset: int = Field(0, ge=0)


class ApplicationStatusRead(BaseModel):
    """Application tracking record for a user and job pairing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_posting_id: int
    status: str
    match_score: Optional[float] = None
