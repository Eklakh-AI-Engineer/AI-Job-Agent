import time
from app.core.celery_app import celery_app


@celery_app.task(name="dummy_task")
def dummy_task(message: str) -> str:
    """
    A dummy task to verify celery works.
    """
    time.sleep(2)  # Simulate work
    return f"Task completed successfully. Message: {message}"
