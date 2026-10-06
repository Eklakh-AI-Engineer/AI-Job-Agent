"""
backend/app/tasks/maintenance.py

Celery tasks for maintenance operations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from sqlalchemy import delete, select
from app.models.job import ApplicationStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.maintenance.cleanup_old_results")
def cleanup_old_results() -> dict:
    """
    Clean up old task results and stale application statuses.
    
    Runs daily at 2 AM via Celery Beat.
    """
    logger.info("Starting cleanup task")
    
    try:
        result = asyncio.run(_cleanup_stale_applications())
        logger.info(f"Cleanup completed: {result}")
        return result
    except Exception as exc:
        logger.exception("Cleanup task failed")
        raise


async def _cleanup_stale_applications() -> dict:
    """Clean up stale application statuses older than 90 days in 'Discovered' state."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    
    async with AsyncSessionLocal() as db:
        # Find stale applications in "Discovered" state
        stmt = select(ApplicationStatus).where(
            ApplicationStatus.status == "Discovered",
            ApplicationStatus.created_at < cutoff,
        )
        result = await db.execute(stmt)
        stale_apps = result.scalars().all()
        
        count = len(stale_apps)
        
        if count > 0:
            # Delete them
            for app in stale_apps:
                await db.delete(app)
            await db.commit()
        
        return {
            "stale_applications_removed": count,
            "cutoff_date": cutoff.isoformat(),
        }


# Import asyncio at module level for the task
import asyncio