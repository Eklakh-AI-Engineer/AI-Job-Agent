"""
backend/app/services/job_discovery_service.py

Service layer for job discovery ingestion.
Replaces the sync SQLite-based JobRepository with async SQLAlchemy.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting
from app.schemas.job_discovery import JobDiscoveryCreate
from app.services.errors import JobAlreadyExistsError


async def create_job_from_discovery(db: AsyncSession, payload: JobDiscoveryCreate) -> JobPosting:
    """
    Ingest a job from discovery pipeline.
    
    Uses PostgreSQL upsert (ON CONFLICT) to handle duplicates by URL.
    
    Raises:
        JobAlreadyExistsError: If a posting with the same URL already exists.
    """
    # Check for existing by URL first (unique constraint)
    existing = await get_job_by_url(db, payload.url)
    if existing is not None:
        raise JobAlreadyExistsError("A job posting with this URL already exists")

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
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
        eligibility=payload.eligibility,
        compensation=payload.compensation,
        internship_information=payload.internship_information,
        raw_source_reference=payload.raw_source_reference,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def bulk_upsert_jobs(db: AsyncSession, payloads: List[JobDiscoveryCreate]) -> dict:
    """
    Bulk upsert jobs from discovery pipeline.
    
    Uses PostgreSQL ON CONFLICT DO NOTHING for URL uniqueness.
    Returns counts of inserted, duplicates, and errors.
    """
    if not payloads:
        return {"inserted": 0, "duplicates": 0, "errors": []}

    values = []
    for p in payloads:
        values.append({
            "title": p.title,
            "company": p.company,
            "location": p.location,
            "job_description": p.job_description,
            "url": p.url,
            "source": p.source,
            "source_job_id": p.source_job_id,
            "application_url": p.application_url,
            "work_mode": p.work_mode,
            "posted_date": p.posted_date,
            "closing_date": p.closing_date,
            "experience_requirement": p.experience_requirement,
            "education_requirement": p.education_requirement,
            "required_skills": p.required_skills,
            "preferred_skills": p.preferred_skills,
            "eligibility": p.eligibility,
            "compensation": p.compensation,
            "internship_information": p.internship_information,
            "raw_source_reference": p.raw_source_reference,
        })

    # Use PostgreSQL upsert with ON CONFLICT DO NOTHING on URL
    stmt = pg_insert(JobPosting).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
    
    result = await db.execute(stmt)
    await db.commit()
    
    # Rowcount gives us the number of inserted rows
    inserted = result.rowcount
    duplicates = len(values) - inserted
    
    return {"inserted": inserted, "duplicates": duplicates, "errors": []}


async def list_jobs(
    db: AsyncSession,
    limit: int = 100,
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
        .limit(limit)
        .offset(max(offset, 0))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_jobs(db: AsyncSession) -> int:
    """Total number of stored job postings."""
    from sqlalchemy import func
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


async def get_job_by_source_id(db: AsyncSession, source: str, source_job_id: str) -> Optional[JobPosting]:
    """Return the posting with ``source`` and ``source_job_id``, or None."""
    result = await db.execute(
        select(JobPosting).where(
            JobPosting.source == source,
            JobPosting.source_job_id == source_job_id,
        )
    )
    return result.scalar_one_or_none()


async def get_job_or_raise(db: AsyncSession, job_id: int) -> JobPosting:
    """Return the posting with ``job_id`` or raise :class:`JobNotFoundError`."""
    from app.services.errors import JobNotFoundError
    job = await get_job_by_id(db, job_id)
    if job is None:
        raise JobNotFoundError(f"Job posting {job_id} not found")
    return job