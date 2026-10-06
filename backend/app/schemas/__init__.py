"""Pydantic request/response schemas for the API layer."""

from app.schemas.token import TokenPayload, TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserRead, UserUpdate
from app.schemas.job import (
    ApplicationStatusRead,
    JobPostingCreate,
    JobPostingList,
    JobPostingRead,
)
from app.schemas.job_discovery import (
    JobDiscoveryCreate,
    JobDiscoveryList,
    JobDiscoveryRead,
)
from app.schemas.candidate_kb import (
    CandidateKBDeleteResponse,
    CandidateKBResponse,
    CandidateKBSaveRequest,
    CandidateKBValidateRequest,
    CandidateKBValidateResponse,
    CandidateKBVersionList,
    CandidateKBVersionSummary,
)

__all__ = [
    "ApplicationStatusRead",
    "CandidateKBDeleteResponse",
    "CandidateKBResponse",
    "CandidateKBSaveRequest",
    "CandidateKBValidateRequest",
    "CandidateKBValidateResponse",
    "CandidateKBVersionList",
    "CandidateKBVersionSummary",
    "JobDiscoveryCreate",
    "JobDiscoveryList",
    "JobDiscoveryRead",
    "JobPostingCreate",
    "JobPostingList",
    "JobPostingRead",
    "TokenPayload",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserRead",
    "UserUpdate",
]
