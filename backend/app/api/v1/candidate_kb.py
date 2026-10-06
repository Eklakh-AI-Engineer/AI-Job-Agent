"""
backend/app/api/v1/candidate_kb.py

Candidate Knowledge Base endpoints.

The KB is private to its owner. Read endpoints strip restricted/undetermined
evidence references unless the caller is the owner and explicitly requests
``include_restricted=true``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.candidate_kb import (
    CandidateKBDeleteResponse,
    CandidateKBResponse,
    CandidateKBSaveRequest,
    CandidateKBValidateRequest,
    CandidateKBValidateResponse,
    CandidateKBVersionList,
    CandidateKBVersionSummary,
)
from app.services.candidate_kb_service import (
    CandidateKBNotFoundError,
    CandidateKBValidationError,
    delete_candidate_kb,
    kb_to_public_dict,
    list_candidate_kb_versions,
    load_candidate_kb,
    save_candidate_kb_from_dict,
    validate_kb_dict,
)

router = APIRouter(prefix="/profile/kb", tags=["Candidate KB"])


@router.get(
    "",
    response_model=CandidateKBResponse,
    summary="Get the current user's Candidate KB",
)
async def get_my_kb(
    include_restricted: bool = Query(
        False,
        description="Include restricted/undetermined evidence (owner-only).",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CandidateKBResponse:
    """
    Return the authenticated user's active Candidate KB.

    By default restricted content is stripped. The owner may set
    ``include_restricted=true`` to receive the full document for editing.
    """
    try:
        kb = await load_candidate_kb(db, current_user.id)
    except CandidateKBNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Candidate KB found. Create one with PUT /api/v1/profile/kb.",
        ) from exc
    except CandidateKBValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    record = None
    from app.services.candidate_kb_service import get_active_kb_record

    record = await get_active_kb_record(db, current_user.id)

    if include_restricted:
        data = kb.model_dump(mode="json")
    else:
        data = kb_to_public_dict(kb)

    return CandidateKBResponse(
        version=record.version if record else 1,
        is_active=record.is_active if record else True,
        change_note=record.change_note if record else None,
        created_at=record.created_at if record else None,
        updated_at=record.updated_at if record else None,
        data=data,
    )


@router.put(
    "",
    response_model=CandidateKBResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or replace the current user's Candidate KB",
)
async def put_my_kb(
    payload: CandidateKBSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CandidateKBResponse:
    """
    Validate and persist a new version of the authenticated user's KB.

    The KB is validated against the full CandidateKB schema (including
    cross-file referential integrity) before it is stored.
    """
    try:
        record = await save_candidate_kb_from_dict(
            db,
            current_user.id,
            payload.data,
            change_note=payload.change_note,
        )
    except CandidateKBValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Return the owner's full document (they just provided it).
    kb = await load_candidate_kb(db, current_user.id)
    return CandidateKBResponse(
        version=record.version,
        is_active=record.is_active,
        change_note=record.change_note,
        created_at=record.created_at,
        updated_at=record.updated_at,
        data=kb.model_dump(mode="json"),
    )


@router.post(
    "/validate",
    response_model=CandidateKBValidateResponse,
    summary="Validate a Candidate KB without saving",
)
async def validate_my_kb(
    payload: CandidateKBValidateRequest,
    current_user: User = Depends(get_current_user),
) -> CandidateKBValidateResponse:
    """
    Validate a KB document without persisting it.

    Useful for a client-side editor to surface errors before saving.
    """
    try:
        validate_kb_dict(payload.data)
        return CandidateKBValidateResponse(valid=True)
    except CandidateKBValidationError as exc:
        return CandidateKBValidateResponse(valid=False, errors=[str(exc)])


@router.delete(
    "",
    response_model=CandidateKBDeleteResponse,
    summary="Delete the current user's Candidate KB",
)
async def delete_my_kb(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CandidateKBDeleteResponse:
    """Delete all versions of the authenticated user's KB."""
    deleted = await delete_candidate_kb(db, current_user.id)
    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Candidate KB found to delete.",
        )
    return CandidateKBDeleteResponse(deleted=deleted)


@router.get(
    "/versions",
    response_model=CandidateKBVersionList,
    summary="List Candidate KB version history",
)
async def list_my_kb_versions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CandidateKBVersionList:
    """Return the version history for the authenticated user's KB."""
    records = await list_candidate_kb_versions(db, current_user.id)
    items = [
        CandidateKBVersionSummary(
            version=r.version,
            is_active=r.is_active,
            change_note=r.change_note,
            created_at=r.created_at,
        )
        for r in records
    ]
    return CandidateKBVersionList(items=items, total=len(items))