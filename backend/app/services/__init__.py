"""Service layer: business logic shared by the API and the Celery workers."""

from app.services.errors import (
    AuthenticationError,
    InactiveUserError,
    JobAlreadyExistsError,
    JobNotFoundError,
    ServiceError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.services.job_service import (
    count_jobs,
    create_job,
    get_job_by_id,
    get_job_by_url,
    get_job_or_raise,
    list_jobs,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
)

__all__ = [
    "AuthenticationError",
    "InactiveUserError",
    "JobAlreadyExistsError",
    "JobNotFoundError",
    "ServiceError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "authenticate_user",
    "count_jobs",
    "create_job",
    "create_user",
    "get_job_by_id",
    "get_job_by_url",
    "get_job_or_raise",
    "get_user_by_email",
    "get_user_by_id",
    "list_jobs",
    "update_user",
]
