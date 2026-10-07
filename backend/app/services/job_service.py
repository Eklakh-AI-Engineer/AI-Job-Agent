"""
backend/app/services/job_service.py

Job posting business logic: ingestion, listing, and lookup.

The pgvector ``embedding`` column is intentionally never read or written here.
Embeddings are produced by the matching pipeline (Phase 4) and stay internal.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting
from app.schemas.job import JobPostingCreate
from app.services.errors import JobAlreadyExistsError, JobNotFoundError
from app.services.jd_normalization import normalize_job_requirements

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def _clamp_limit(limit: int) -> int:
    """Keep pagination within sane bounds without raising on caller input."""
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


async def list_jobs(
    db: AsyncSession,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    company: Optional[str] = None,
    source: Optional[str] = None,
) -> List[JobPosting]:
    """
    List job postings, newest first.

    ``company`` and ``source`` are optional exact-match filters.
    """
    stmt = select(JobPosting)
    if company:
        stmt = stmt.where(JobPosting.company == company.strip())
    if source:
        stmt = stmt.where(JobPosting.source == source.strip())

    stmt = (
        stmt.order_by(JobPosting.id.desc())
        .limit(_clamp_limit(limit))
        .offset(max(offset, 0))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_jobs(db: AsyncSession) -> int:
    """Total number of stored job postings."""
    result = await db.execute(select(func.count()).select_from(JobPosting))
    return int(result.scalar() or 0)


async def get_job_by_id(db: AsyncSession, job_id: int) -> Optional[JobPosting]:
    """Return the posting with ``job_id``, or None."""
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    return result.scalar_one_or_none()


async def get_job_by_url(db: AsyncSession, url: str) -> Optional[JobPosting]:
    """Return the posting with ``url``, or None."""
    result = await db.execute(select(JobPosting).where(JobPosting.url == url))
    return result.scalar_one_or_none()


async def create_job(db: AsyncSession, payload: JobPostingCreate) -> JobPosting:
    """
    Ingest a job posting.

    Raises:
        JobAlreadyExistsError: if a posting with the same URL already exists.
    """
    existing = await get_job_by_url(db, payload.url)
    if existing is not None:
        raise JobAlreadyExistsError("A job posting with this URL already exists")

    normalized = normalize_job_requirements(payload.model_dump())
    job = JobPosting(
        title=payload.title,
        company=payload.company,
        location=payload.location,
        job_description=payload.job_description,
        url=payload.url,
        source=payload.source,
        source_job_id=payload.source_job_id,
        application_url=payload.application_url,
        work_mode=payload.work_mode,
        posted_date=payload.posted_date,
        closing_date=payload.closing_date,
        experience_requirement=payload.experience_requirement,
        education_requirement=payload.education_requirement,
        required_skills=payload.required_skills or None,
        preferred_skills=payload.preferred_skills or None,
        eligibility=payload.eligibility,
        compensation=payload.compensation,
        internship_information=payload.internship_information,
        raw_source_reference=payload.raw_source_reference,
        normalized_required_skills=normalized["required_skills"],
        normalized_preferred_skills=normalized["preferred_skills"],
        experience_min_years=normalized["normalization"]["fields"]["experience"]["min_years"],
        experience_max_years=normalized["normalization"]["fields"]["experience"]["max_years"],
        education_level=normalized["normalization"]["fields"]["education"]["level"],
        education_fields=normalized["normalization"]["fields"]["education"]["fields"],
        jd_normalization_version=normalized["normalization"]["version"],
        jd_normalization_status=normalized["normalization"]["status"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_or_raise(db: AsyncSession, job_id: int) -> JobPosting:
    """Return the posting with ``job_id`` or raise :class:`JobNotFoundError`."""
    job = await get_job_by_id(db, job_id)
    if job is None:
        raise JobNotFoundError(f"Job posting {job_id} not found")
    return job
