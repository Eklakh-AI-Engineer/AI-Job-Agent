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
from app.schemas.document import (
    ATSAnalysisResponse,
    DocumentContentUpdate,
    DocumentGenerateRequest,
    DocumentList,
    DocumentRead,
    DocumentStatusUpdate,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationEventList,
    ApplicationEventRead,
    ApplicationList,
    ApplicationRead,
    ApplicationSubmitRequest,
    ApplicationSubmitResponse,
    ApplicationTransitionRequest,
)

__all__ = [
    "ATSAnalysisResponse",
    "ApplicationCreate",
    "ApplicationEventList",
    "ApplicationEventRead",
    "ApplicationList",
    "ApplicationRead",
    "ApplicationStatusRead",
    "ApplicationSubmitRequest",
    "ApplicationSubmitResponse",
    "ApplicationTransitionRequest",
    "CandidateKBDeleteResponse",
    "CandidateKBResponse",
    "CandidateKBSaveRequest",
    "CandidateKBValidateRequest",
    "CandidateKBValidateResponse",
    "CandidateKBVersionList",
    "CandidateKBVersionSummary",
    "DocumentContentUpdate",
    "DocumentGenerateRequest",
    "DocumentList",
    "DocumentRead",
    "DocumentStatusUpdate",
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
