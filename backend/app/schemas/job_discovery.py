"""
backend/app/schemas/job_discovery.py

Pydantic schemas for job discovery pipeline.
Maps to the unified JobPosting SQLAlchemy model.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobDiscoveryCreate(BaseModel):
    """Schema for creating a job from discovery pipeline."""

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

    # Extended fields from discovery
    source_job_id: Optional[str] = Field(None, max_length=255)
    application_url: Optional[str] = Field(None, max_length=1024)
    work_mode: Optional[str] = Field(None, max_length=50, description="remote/hybrid/onsite")
    posted_date: Optional[str] = Field(None, max_length=100)
    closing_date: Optional[str] = Field(None, max_length=100)
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    eligibility: Optional[str] = None
    compensation: Optional[str] = Field(None, max_length=512)
    internship_information: Optional[str] = None
    raw_source_reference: Optional[dict] = None
    # Computed normalization fields are optional on ingestion; the service
    # derives them from the source fields to keep all ingestion paths consistent.
    normalized_required_skills: List[str] = Field(default_factory=list)
    normalized_preferred_skills: List[str] = Field(default_factory=list)
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    education_level: Optional[str] = None
    education_fields: List[str] = Field(default_factory=list)
    jd_normalization_version: Optional[str] = None
    jd_normalization_status: Optional[str] = None

    @field_validator("title", "company", "location", "url", "source", mode="before")
    @classmethod
    def _strip_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("required_skills", "preferred_skills", mode="before")
    @classmethod
    def _clean_skill_list(cls, value: Optional[List[str]]) -> List[str]:
        if not value:
            return []
        cleaned = []
        for item in value:
            if item is not None:
                c = str(item).strip()
                if c:
                    cleaned.append(c)
        return cleaned


class JobDiscoveryRead(BaseModel):
    """Job representation returned by discovery pipeline."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: Optional[str] = None
    job_description: str
    url: str
    source: str
    source_job_id: Optional[str] = None
    application_url: Optional[str] = None
    work_mode: Optional[str] = None
    posted_date: Optional[str] = None
    closing_date: Optional[str] = None
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    eligibility: Optional[str] = None
    compensation: Optional[str] = None
    internship_information: Optional[str] = None
    raw_source_reference: Optional[dict] = None
    created_at: Optional[datetime] = None


class JobDiscoveryList(BaseModel):
    """Paginated collection of discovered jobs."""

    items: List[JobDiscoveryRead] = Field(default_factory=list)
    total: int = Field(0, ge=0, description="Total postings matching the filter.")
    limit: int = Field(0, ge=0)
    offset: int = Field(0, ge=0)