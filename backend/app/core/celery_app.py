from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_job_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.dummy"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
