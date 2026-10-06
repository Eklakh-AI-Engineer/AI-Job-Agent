"""
backend/app/tasks/documents.py

Celery tasks for asynchronous document generation.
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.celery_app import celery_app
from app.core.metrics import celery_tasks_total, celery_task_duration_seconds

logger = logging.getLogger(__name__)


def _get_db_session():
    from app.core.database import AsyncSessionLocal

    return AsyncSessionLocal


def _get_document_service():
    from app.services import document_service

    return document_service


@celery_app.task(
    name="app.tasks.documents.generate_document_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def generate_document_task(self, user_id: int, job_id: int, doc_type: str) -> dict:
    """
    Celery task to generate a resume or cover letter in the background.
    """
    task_start = time.time()
    logger.info(f"Generating {doc_type} for user={user_id}, job={job_id}")

    try:
        result = asyncio.run(_generate_document_async(user_id, job_id, doc_type))

        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="generate_document_task", status="success"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="generate_document_task"
        ).observe(duration)

        result["duration_seconds"] = round(duration, 2)
        return result

    except Exception:
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="generate_document_task", status="failure"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="generate_document_task"
        ).observe(duration)
        logger.exception(f"Document generation failed for user={user_id}, job={job_id}")
        raise


async def _generate_document_async(user_id: int, job_id: int, doc_type: str) -> dict:
    service = _get_document_service()
    session_factory = _get_db_session()

    async with session_factory() as db:
        if doc_type == "resume":
            doc = await service.generate_resume(db, user_id, job_id)
        elif doc_type == "cover_letter":
            doc = await service.generate_cover_letter(db, user_id, job_id)
        else:
            raise ValueError(f"Unknown doc_type: {doc_type}")

        return {
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "version": doc.version,
            "status": doc.status,
        }


@celery_app.task(name="app.tasks.documents.generate_all_documents_task")
def generate_all_documents_task(user_id: int, job_id: int) -> dict:
    """
    Generate both a resume and a cover letter for a (user, job) pair.
    """
    logger.info(f"Generating all documents for user={user_id}, job={job_id}")
    results = {}

    for doc_type in ("resume", "cover_letter"):
        try:
            results[doc_type] = asyncio.run(
                _generate_document_async(user_id, job_id, doc_type)
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Failed to generate {doc_type}")
            results[doc_type] = {"error": str(exc)}

    return results