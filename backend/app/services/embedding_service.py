"""
backend/app/services/embedding_service.py

Service layer for embedding generation and management.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import (
    EmbeddingProvider,
    EmbeddingResult,
    get_embedding_provider,
    compute_text_hash,
)
from app.core.metrics import embedding_generation_total, embedding_generation_duration_seconds
from app.models.job import JobPosting

logger = logging.getLogger(__name__)


def _get_session_factory():
    """Lazily import the DB session factory to avoid connecting at import time."""
    from app.core.database import AsyncSessionLocal

    return AsyncSessionLocal


# Text templates for embedding generation
JOB_EMBEDDING_TEMPLATE = """Job Title: {title}
Company: {company}
Location: {location}
Work Mode: {work_mode}
Description: {description}
Requirements: {requirements}
Skills: {skills}
Eligibility: {eligibility}
"""

JOB_SEARCH_TEMPLATE = """Search Query: {query}
"""


def build_job_text(job: JobPosting) -> str:
    """Build text representation of a job for embedding."""
    skills = []
    if job.required_skills:
        skills.extend(job.required_skills)
    if job.preferred_skills:
        skills.extend(job.preferred_skills)
    
    requirements = []
    if job.experience_requirement:
        requirements.append(f"Experience: {job.experience_requirement}")
    if job.education_requirement:
        requirements.append(f"Education: {job.education_requirement}")
    if job.eligibility:
        requirements.append(f"Eligibility: {job.eligibility}")
    
    return JOB_EMBEDDING_TEMPLATE.format(
        title=job.title or "",
        company=job.company or "",
        location=job.location or "",
        work_mode=job.work_mode or "",
        description=job.job_description or "",
        requirements="; ".join(requirements),
        skills=", ".join(skills),
        eligibility=job.eligibility or "",
    )


def build_search_text(query: str) -> str:
    """Build text representation of a search query for embedding."""
    return JOB_SEARCH_TEMPLATE.format(query=query)


async def generate_job_embedding(
    job: JobPosting,
    provider: Optional[EmbeddingProvider] = None,
) -> EmbeddingResult:
    """
    Generate embedding for a single job posting.
    
    Args:
        job: JobPosting to embed
        provider: Optional provider override
        
    Returns:
        EmbeddingResult with embeddings and metadata
    """
    provider = provider or get_embedding_provider()
    text = build_job_text(job)
    
    start_time = asyncio.get_event_loop().time()
    try:
        result = await provider.embed([text])
        latency = (asyncio.get_event_loop().time() - start_time) * 1000
        
        embedding_generation_total.labels(
            provider=provider.model_name,
            status="success"
        ).inc()
        embedding_generation_duration_seconds.labels(
            provider=provider.model_name
        ).observe(latency / 1000)
        
        logger.debug(f"Generated embedding for job {job.id} ({latency:.0f}ms)")
        return result
        
    except Exception as e:
        embedding_generation_total.labels(
            provider=provider.model_name,
            status="failure"
        ).inc()
        logger.exception(f"Failed to generate embedding for job {job.id}")
        raise


async def generate_embeddings_batch(
    jobs: List[JobPosting],
    provider: Optional[EmbeddingProvider] = None,
    batch_size: int = 100,
) -> List[EmbeddingResult]:
    """
    Generate embeddings for multiple jobs in batches.
    
    Args:
        jobs: List of JobPostings to embed
        provider: Optional provider override
        batch_size: Number of jobs per batch
        
    Returns:
        List of EmbeddingResults (one per batch)
    """
    provider = provider or get_embedding_provider()
    results = []
    
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        texts = [build_job_text(job) for job in batch]
        
        start_time = asyncio.get_event_loop().time()
        try:
            result = await provider.embed(texts)
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            embedding_generation_total.labels(
                provider=provider.model_name,
                status="success"
            ).inc(len(batch))
            embedding_generation_duration_seconds.labels(
                provider=provider.model_name
            ).observe(latency / 1000)
            
            results.append(result)
            logger.info(f"Generated embeddings for batch {i//batch_size + 1} ({len(batch)} jobs, {latency:.0f}ms)")
            
        except Exception as e:
            embedding_generation_total.labels(
                provider=provider.model_name,
                status="failure"
            ).inc(len(batch))
            logger.exception(f"Failed to generate embeddings for batch {i//batch_size + 1}")
            raise
    
    return results


async def update_job_embedding(
    db: AsyncSession,
    job_id: int,
    embedding: List[float],
) -> bool:
    """
    Update a job's embedding in the database.
    
    Args:
        db: Database session
        job_id: Job ID
        embedding: Embedding vector
        
    Returns:
        True if updated, False if job not found
    """
    result = await db.execute(
        update(JobPosting)
        .where(JobPosting.id == job_id)
        .values(embedding=embedding)
    )
    await db.commit()
    return result.rowcount > 0


async def get_jobs_without_embeddings(
    db: AsyncSession,
    limit: int = 1000,
) -> List[JobPosting]:
    """Get jobs that don't have embeddings yet."""
    result = await db.execute(
        select(JobPosting)
        .where(JobPosting.embedding.is_(None))
        .limit(limit)
    )
    return list(result.scalars().all())


async def backfill_embeddings(
    batch_size: int = 100,
    provider: Optional[EmbeddingProvider] = None,
) -> dict:
    """
    Backfill embeddings for all jobs without embeddings.
    
    Args:
        batch_size: Number of jobs per batch
        provider: Optional provider override
        
    Returns:
        Dict with stats: processed, succeeded, failed
    """
    provider = provider or get_embedding_provider()
    session_factory = _get_session_factory()
    
    async with session_factory() as db:
        jobs = await get_jobs_without_embeddings(db, limit=10000)
        logger.info(f"Found {len(jobs)} jobs without embeddings")
        
        if not jobs:
            return {"processed": 0, "succeeded": 0, "failed": 0}
        
        stats = {"processed": 0, "succeeded": 0, "failed": 0}
        
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            texts = [build_job_text(job) for job in batch]
            
            try:
                result = await provider.embed(texts)
                
                # Update each job
                for job, embedding in zip(batch, result.embeddings):
                    await update_job_embedding(db, job.id, embedding)
                
                stats["processed"] += len(batch)
                stats["succeeded"] += len(batch)
                logger.info(f"Backfilled batch {i//batch_size + 1} ({len(batch)} jobs)")
                
            except Exception as e:
                stats["processed"] += len(batch)
                stats["failed"] += len(batch)
                logger.exception(f"Failed to backfill batch {i//batch_size + 1}")
        
        return stats


async def generate_search_embedding(
    query: str,
    provider: Optional[EmbeddingProvider] = None,
) -> List[float]:
    """Generate embedding for a search query."""
    provider = provider or get_embedding_provider()
    text = build_search_text(query)
    result = await provider.embed([text])
    return result.embeddings[0]