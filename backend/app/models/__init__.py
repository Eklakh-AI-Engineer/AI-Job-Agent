from app.models.base import Base
from app.models.user import User
from app.models.job import JobPosting, ApplicationStatus

# Re-export models for Alembic to detect them easily
__all__ = ["Base", "User", "JobPosting", "ApplicationStatus"]
