"""
backend/app/tasks/applications.py

Celery tasks for browser-automation application submission.

These tasks perform *real* submissions (dry_run=False) and are therefore only
ever dispatched for applications that are already Approved. They retry with
exponential backoff and record failures against the application.
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


def _get_submit_fn():
    from app.services.browser_automation_service import submit_application

    return submit_application


@celery_app.task(
    name="app.tasks.applications.submit_application_task",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # max 30 min
    retry_jitter=True,
)
def submit_application_task(self, user_id: int, application_id: int) -> dict:
    """
    Submit an approved application via browser automation.
    """
    task_start = time.time()
    logger.info(f"Submitting application {application_id} for user {user_id}")

    try:
        result = asyncio.run(_submit_async(user_id, application_id))

        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="submit_application_task", status="success"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="submit_application_task"
        ).observe(duration)

        result["duration_seconds"] = round(duration, 2)
        return result

    except Exception:
        duration = time.time() - task_start
        celery_tasks_total.labels(
            task_name="submit_application_task", status="failure"
        ).inc()
        celery_task_duration_seconds.labels(
            task_name="submit_application_task"
        ).observe(duration)
        logger.exception(f"Application submission task failed for {application_id}")
        raise


async def _submit_async(user_id: int, application_id: int) -> dict:
    submit_application = _get_submit_fn()
    session_factory = _get_db_session()

    async with session_factory() as db:
        outcome = await submit_application(
            db,
            user_id,
            application_id,
            dry_run=False,
            check_robots=True,
            actor="worker:submission",
        )
        r = outcome.result
        return {
            "application_id": outcome.application_id,
            "application_status": outcome.application_status,
            "success": r.success,
            "ats": r.ats,
            "error": r.error,
            "evidence_paths": r.evidence_paths,
        }


@celery_app.task(name="app.tasks.applications.dry_run_submission_task")
def dry_run_submission_task(user_id: int, application_id: int) -> dict:
    """
    Pre-fill an application form without submitting (safe inspection).
    """
    submit_application = _get_submit_fn()
    session_factory = _get_db_session()

    async def _run():
        async with session_factory() as db:
            outcome = await submit_application(
                db, user_id, application_id, dry_run=True, actor="worker:dry-run"
            )
            return outcome.result.to_dict()

    return asyncio.run(_run())