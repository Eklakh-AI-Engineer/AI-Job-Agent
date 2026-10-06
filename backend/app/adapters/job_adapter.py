"""
backend/app/adapters/job_adapter.py

Adapter to convert unified JobPosting SQLAlchemy model to the format
expected by the evaluation pipeline (backend.jobs.models.Job).
"""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timezone
from backend.jobs.models import Job as LegacyJob
from app.models.job import JobPosting


def job_posting_to_legacy_job(job_posting: JobPosting) -> LegacyJob:
    """
    Convert SQLAlchemy JobPosting to legacy Pydantic Job model for evaluation pipeline.
    
    This allows the existing evaluation code to work with the unified model.
    """
    if job_posting is None:
        raise ValueError("JobPosting cannot be None")
    
    return LegacyJob(
        id=str(job_posting.id),  # Convert integer PK to string for compatibility
        source=job_posting.source,
        source_job_id=job_posting.source_job_id or "",
        company=job_posting.company,
        title=job_posting.title,
        location=job_posting.location,
        work_mode=job_posting.work_mode,
        job_url=job_posting.url,
        application_url=job_posting.application_url,
        description=job_posting.job_description,
        posted_date=_parse_date(job_posting.posted_date),
        closing_date=_parse_date(job_posting.closing_date),
        experience_requirement=job_posting.experience_requirement,
        education_requirement=job_posting.education_requirement,
        required_skills=job_posting.required_skills or [],
        preferred_skills=job_posting.preferred_skills or [],
        eligibility=job_posting.eligibility,
        compensation=job_posting.compensation,
        internship_information=job_posting.internship_information,
        discovered_at=job_posting.created_at or datetime.now(timezone.utc),
        updated_at=job_posting.updated_at,
        raw_source_reference=job_posting.raw_source_reference,
    )


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime, supporting multiple formats."""
    if not date_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, return None
    return None


def legacy_job_to_job_posting_create(legacy_job: LegacyJob) -> dict:
    """
    Convert legacy Pydantic Job to dict suitable for JobPosting creation.
    """
    return {
        "title": legacy_job.title,
        "company": legacy_job.company,
        "location": legacy_job.location,
        "job_description": legacy_job.description or "",
        "url": legacy_job.job_url,
        "source": legacy_job.source,
        "source_job_id": legacy_job.source_job_id,
        "application_url": legacy_job.application_url,
        "work_mode": legacy_job.work_mode,
        "posted_date": legacy_job.posted_date.isoformat() if legacy_job.posted_date else None,
        "closing_date": legacy_job.closing_date.isoformat() if legacy_job.closing_date else None,
        "experience_requirement": legacy_job.experience_requirement,
        "education_requirement": legacy_job.education_requirement,
        "required_skills": legacy_job.required_skills,
        "preferred_skills": legacy_job.preferred_skills,
        "eligibility": legacy_job.eligibility,
        "compensation": legacy_job.compensation,
        "internship_information": legacy_job.internship_information,
        "raw_source_reference": legacy_job.raw_source_reference,
    }