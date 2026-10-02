"""
backend/app/api/v1/jobs.py

Read and ingest endpoints for job postings.

Ingestion is currently open to any authenticated user; it is exercised by the
discovery pipeline. A dedicated ingestion scope will be introduced with the
Discovery agent in Phase 4.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.job import JobPostingCreate, JobPostingList, JobPostingRead
from app.services.errors import JobAlreadyExistsError, JobNotFoundError
from app.services.job_service import (
    count_jobs,
    create_job,
    get_job_or_raise,
    list_jobs,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobPostingList, summary="List job postings")
async def get_jobs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results."),
    offset: int = Query(0, ge=0, description="Number of results to skip."),
    company: Optional[str] = Query(None, description="Filter by exact company name."),
    source: Optional[str] = Query(None, description="Filter by source board."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostingList:
    """Return job postings, newest first."""
    jobs = await list_jobs(
        db, limit=limit, offset=offset, company=company, source=source
    )
    total = await count_jobs(db)
    return JobPostingList(
        items=[JobPostingRead.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=JobPostingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a job posting",
)
async def post_job(
    payload: JobPostingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostingRead:
    """Store a newly discovered job posting. Duplicate URLs are rejected."""
    try:
        job = await create_job(db, payload)
    except JobAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return JobPostingRead.model_validate(job)


@router.get("/{job_id}", response_model=JobPostingRead, summary="Get one job posting")
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobPostingRead:
    """Return a single job posting by id."""
    try:
        job = await get_job_or_raise(db, job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return JobPostingRead.model_validate(job)
