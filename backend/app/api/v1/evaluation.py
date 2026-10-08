"""
backend/app/api/v1/evaluation.py

Evaluation API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.evaluation_service import (
    CandidateKBNotFoundError,
    evaluate_job_for_user,
)
from app.services.errors import JobNotFoundError
from evaluation.models import EvaluationResult

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


@router.post(
    "/{job_id}",
    response_model=EvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a job posting against the current user's profile",
)
async def evaluate_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationResult:
    """
    Evaluate a job posting against the authenticated user's candidate knowledge base.
    
    Returns a complete EvaluationResult with:
    - Skill-by-skill match analysis
    - Eligibility assessment
    - Role alignment
    - Overall fit score and recommendation
    - Evidence references for audit trail
    """
    try:
        result = await evaluate_job_for_user(db, job_id, current_user.id)
        return result
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CandidateKBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate knowledge base not found. Please complete your profile first.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc