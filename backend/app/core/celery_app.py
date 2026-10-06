from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_job_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.dummy",
        "app.tasks.discovery",
        "app.tasks.embeddings",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        # Run job discovery every 6 hours
        "discover-jobs-every-6-hours": {
            "task": "app.tasks.discovery.discover_jobs_task",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        # Generate embeddings for new jobs every hour
        "generate-embeddings-hourly": {
            "task": "app.tasks.embeddings.backfill_embeddings_task",
            "schedule": crontab(minute=15, hour="*"),  # 15 min past every hour
            "kwargs": {"batch_size": 50},
        },
        # Clean up old task results daily
        "cleanup-old-results-daily": {
            "task": "app.tasks.maintenance.cleanup_old_results",
            "schedule": crontab(minute=0, hour=2),
        },
    },
)
