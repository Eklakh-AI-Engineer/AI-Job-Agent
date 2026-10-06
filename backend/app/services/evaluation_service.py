"""
backend/app/services/evaluation_service.py

Service layer for candidate-job evaluation.
Connects the API layer to the deterministic evaluation engine.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting
from app.services.candidate_kb_service import (
    CandidateKBNotFoundError,
    load_candidate_kb,
)
from app.services.job_discovery_service import get_job_by_id as get_job_by_id_service
from backend.evaluation.candidate_models import CandidateKB
from backend.evaluation.evaluator import evaluate_candidate_against_job
from backend.evaluation.models import EvaluationResult
from backend.evaluation.requirements import extract_requirements

__all__ = [
    "CandidateKBNotFoundError",
    "evaluate_job_for_user",
    "evaluate_job_with_kb",
    "get_candidate_kb",
]


async def get_candidate_kb(db: AsyncSession, user_id: int) -> CandidateKB:
    """
    Load the active Candidate KB for a user from the database.

    Raises:
        CandidateKBNotFoundError: if the user has no persisted KB.
    """
    return await load_candidate_kb(db, user_id)


async def evaluate_job_for_user(
    db: AsyncSession,
    job_id: int,
    user_id: int,
) -> EvaluationResult:
    """
    Evaluate a job posting against a user's candidate KB.

    This is the main entry point for the evaluation API.
    """
    # 1. Get job from database
    job = await get_job_by_id_service(db, job_id)
    if job is None:
        from app.services.errors import JobNotFoundError

        raise JobNotFoundError(f"Job posting {job_id} not found")

    # JobPosting is the canonical application-domain representation.
    job_requirements = extract_requirements(job)

    # 4. Load candidate KB from database
    candidate_kb = await load_candidate_kb(db, user_id)

    # 5. Run evaluation (Phase 3C)
    result = evaluate_candidate_against_job(job_requirements, candidate_kb)

    return result


async def evaluate_job_with_kb(
    job: JobPosting,
    candidate_kb: CandidateKB,
) -> EvaluationResult:
    """
    Evaluate a job posting against a provided candidate KB.

    Useful for batch evaluation or when KB is already loaded.
    """
    job_requirements = extract_requirements(job)
    return evaluate_candidate_against_job(job_requirements, candidate_kb)