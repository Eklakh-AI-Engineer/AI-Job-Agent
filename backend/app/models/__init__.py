from app.models.base import Base
from app.models.user import User
from app.models.job import JobPosting, ApplicationStatus
from app.models.candidate_kb import CandidateKBRecord

# Re-export models for Alembic to detect them easily
__all__ = ["Base", "User", "JobPosting", "ApplicationStatus", "CandidateKBRecord"]
