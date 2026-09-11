"""
backend/evaluation/__init__.py

Evaluation engine — Phase 3.
This package provides the deterministic Candidate–Job Evaluation Engine.

Phase 3A: canonical Pydantic schemas only.
Phase 3B: requirement extraction (parsing Job → JobRequirements).
Phase 3C: eligibility, skill matching, role matching.
Phase 3D: scoring and priority classification.
Phase 3E: full evaluator pipeline + explainable output.
"""

from backend.evaluation.requirements import extract_requirements
from backend.evaluation.candidate_models import (
    CandidateKB,
    CandidateProfile,
    CandidateSkills,
    SkillRecord,
    CandidateClaims,
    ClaimRecord,
    CandidateExperience,
    WorkExperienceRecord,
    ProjectRecord,
    CandidatePreferences,
    APPROVED_TARGET_ROLES,
)
from backend.evaluation.candidate_loader import (
    load_candidate_kb_from_dir,
    load_candidate_kb_from_dict,
    validate_candidate_kb,
)

__all__ = [
    "extract_requirements",
    "CandidateKB",
    "CandidateProfile",
    "CandidateSkills",
    "SkillRecord",
    "CandidateClaims",
    "ClaimRecord",
    "CandidateExperience",
    "WorkExperienceRecord",
    "ProjectRecord",
    "CandidatePreferences",
    "APPROVED_TARGET_ROLES",
    "load_candidate_kb_from_dir",
    "load_candidate_kb_from_dict",
    "validate_candidate_kb",
]
