"""
backend/app/tasks/embeddings.py

Celery tasks for embedding generation and backfill.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

from app.core.celery_app import celery_app
from app.core.embeddings import get_embedding_provider, EmbeddingProvider
from app.core.metrics import embedding_generation_total, embedding_generation_duration_seconds, celery_tasks_total, celery_task_duration_seconds

logger = logging.getLogger(__name__)


# Lazy imports for database-dependent functions
def _get_db_session():
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal


def _get_job_model():
    from app.models.job import JobPosting
    return JobPosting


def _get_embedding_service():
    from app.services.embedding_service import (
        build_job_text,
        generate_job_embedding,
        update_job_embedding,
        get_jobs_without_embeddings,
        backfill_embeddings as service_backfill_embeddings,
    )
    return {
        'build_job_text': build_job_text,
        'generate_job_embedding': generate_job_embedding,
        'update_job_embedding': update_job_embedding,
        'get_jobs_without_embeddings': get_jobs_without_embeddings,
        'backfill_embeddings': service_backfill_embeddings,
    }


@celery_app.task(
    name="app.tasks.embeddings.generate_job_embedding_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def generate_job_embedding_task(self, job_id: int) -> dict:
    """
    Celery task to generate embedding for a single job.
    
    Called after job insertion to generate embedding asynchronously.
    """
    task_start = time.time()
    logger.info(f"Generating embedding for job {job_id}")
    
    try:
        result = asyncio.run(_generate_job_embedding_async(job_id))
        
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="generate_job_embedding_task",
            status="success"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="generate_job_embedding_task"
        ).observe(duration)
        
        logger.info(f"Generated embedding for job {job_id} in {duration:.2f}s")
        return {"job_id": job_id, "status": "success", "duration_seconds": round(duration, 2)}
        
    except Exception as exc:
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="generate_job_embedding_task",
            status="failure"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="generate_job_embedding_task"
        ).observe(duration)
        
        logger.exception(f"Failed to generate embedding for job {job_id}")
        raise


async def _generate_job_embedding_async(job_id: int) -> dict:
    """Async function to generate and store embedding."""
    provider = get_embedding_provider()
    JobPosting = _get_job_model()
    embedding_service = _get_embedding_service()
    AsyncSessionLocal = _get_db_session()
    
    async with AsyncSessionLocal() as db:
        # Get job
        from sqlalchemy import select
        result = await db.execute(
            select(JobPosting).where(JobPosting.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.embedding is not None:
            logger.info(f"Job {job_id} already has embedding, skipping")
            return {"job_id": job_id, "status": "already_exists"}
        
        # Generate embedding
        text = embedding_service['build_job_text'](job)
        
        embedding_result = await provider.embed([text])
        embedding = embedding_result.embeddings[0]
        
        # Store embedding
        await embedding_service['update_job_embedding'](db, job_id, embedding)
        
        # Record metrics
        embedding_generation_total.labels(
            provider=provider.model_name,
            status="success"
        ).inc()
        embedding_generation_duration_seconds.labels(
            provider=provider.model_name
        ).observe(embedding_result.latency_ms / 1000)
        
        return {
            "job_id": job_id,
            "status": "success",
            "model": embedding_result.model,
            "dimensions": embedding_result.dimensions,
            "tokens_used": embedding_result.tokens_used,
            "cost_usd": embedding_result.cost_usd,
        }


@celery_app.task(
    name="app.tasks.embeddings.backfill_embeddings_task",
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def backfill_embeddings_task(self, batch_size: int = 100) -> dict:
    """
    Celery task to backfill embeddings for all jobs without embeddings.
    
    Runs periodically or manually triggered.
    """
    task_start = time.time()
    logger.info(f"Starting embedding backfill with batch_size={batch_size}")
    
    try:
        result = asyncio.run(_backfill_embeddings_async(batch_size))
        
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="backfill_embeddings_task",
            status="success"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="backfill_embeddings_task"
        ).observe(duration)
        
        result["duration_seconds"] = round(duration, 2)
        logger.info(f"Embedding backfill completed in {duration:.2f}s: {result}")
        return result
        
    except Exception as exc:
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="backfill_embeddings_task",
            status="failure"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="backfill_embeddings_task"
        ).observe(duration)
        
        logger.exception("Embedding backfill task failed")
        raise


async def _backfill_embeddings_async(batch_size: int) -> dict:
    """Async function to backfill embeddings."""
    provider = get_embedding_provider()
    
    return await service_backfill_embeddings(
        batch_size=batch_size,
        provider=provider,
    )


@celery_app.task(name="app.tasks.embeddings.generate_search_embedding_task")
def generate_search_embedding_task(query: str) -> dict:
    """
    Celery task to generate embedding for a search query.
    
    Used for semantic search - generates query embedding on-demand.
    """
    logger.info(f"Generating search embedding for: {query[:50]}...")
    
    try:
        provider = get_embedding_provider()
        from app.services.embedding_service import build_search_text
        text = build_search_text(query)
        
        result = asyncio.run(provider.embed([text]))
        embedding = result.embeddings[0]
        
        return {
            "query": query,
            "embedding": embedding,
            "model": result.model,
            "dimensions": result.dimensions,
        }
        
    except Exception as e:
        logger.exception(f"Failed to generate search embedding for: {query}")
        raise


@celery_app.task(name="app.tasks.embeddings.regenerate_embeddings_task")
def regenerate_embeddings_task(job_ids: List[int], provider_name: Optional[str] = None) -> dict:
    """
    Celery task to regenerate embeddings for specific jobs.
    
    Useful when switching embedding models or after model updates.
    """
    task_start = time.time()
    logger.info(f"Regenerating embeddings for {len(job_ids)} jobs")
    
    try:
        result = asyncio.run(_regenerate_embeddings_async(job_ids, provider_name))
        
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="regenerate_embeddings_task",
            status="success"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="regenerate_embeddings_task"
        ).observe(duration)
        
        result["duration_seconds"] = round(duration, 2)
        return result
        
    except Exception as exc:
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="regenerate_embeddings_task",
            status="failure"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="regenerate_embeddings_task"
        ).observe(duration)
        
        logger.exception("Regenerate embeddings task failed")
        raise


async def _regenerate_embeddings_async(job_ids: List[int], provider_name: Optional[str]) -> dict:
    """Regenerate embeddings for specific jobs."""
    if provider_name:
        from app.core.embeddings import EmbeddingProviderFactory
        provider = EmbeddingProviderFactory.create(provider_name)
    else:
        provider = get_embedding_provider()
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(JobPosting).where(JobPosting.id.in_(job_ids))
        )
        jobs = list(result.scalars().all())
        
        if not jobs:
            return {"processed": 0, "succeeded": 0, "failed": 0, "errors": ["No jobs found"]}
        
        texts = [build_job_text(job) for job in jobs]
        
        try:
            embedding_result = await provider.embed(texts)
            
            # Update all jobs
            for job, embedding in zip(jobs, embedding_result.embeddings):
                await update_job_embedding(db, job.id, embedding)
            
            return {
                "processed": len(jobs),
                "succeeded": len(jobs),
                "failed": 0,
                "model": embedding_result.model,
                "dimensions": embedding_result.dimensions,
            }
            
        except Exception as e:
            logger.exception("Failed to regenerate embeddings")
            return {
                "processed": len(jobs),
                "succeeded": 0,
                "failed": len(jobs),
                "errors": [str(e)],
            }