from app.models.base import Base
from app.models.user import User
from app.models.job import JobPosting, ApplicationStatus, ApplicationEvent
from app.models.candidate_kb import CandidateKBRecord
from app.models.document import GeneratedDocument

# Re-export models for Alembic to detect them easily
__all__ = [
    "Base",
    "User",
    "JobPosting",
    "ApplicationStatus",
    "ApplicationEvent",
    "CandidateKBRecord",
    "GeneratedDocument",
]
