"""
backend/app/api/v1/applications.py

Application workflow API endpoints.

The workflow enforces a guarded state machine (see ``application_service``).
An application can only be marked Applied after an approved resume document
exists, and submission requires an idempotency key.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
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
from app.services.application_service import (
    ApplicationExistsError,
    ApplicationNotFoundError,
    GuardFailedError,
    InvalidTransitionError,
    create_application,
    get_application,
    list_applications,
    list_events,
    transition_application,
)
from app.services.browser_automation_service import (
    SubmissionBlockedError,
    submit_application,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an application for a job",
)
async def create_my_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """Create an application in the Discovered state."""
    try:
        app_obj = await create_application(
            db, current_user.id, payload.job_id, match_score=payload.match_score
        )
    except ApplicationExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return ApplicationRead.model_validate(app_obj)


@router.get(
    "",
    response_model=ApplicationList,
    summary="List the current user's applications",
)
async def list_my_applications(
    app_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationList:
    """List applications owned by the authenticated user."""
    apps = await list_applications(db, current_user.id, status=app_status)
    return ApplicationList(
        items=[ApplicationRead.model_validate(a) for a in apps],
        total=len(apps),
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationRead,
    summary="Get one application",
)
async def get_my_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """Return a single application owned by the authenticated user."""
    try:
        app_obj = await get_application(db, current_user.id, application_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return ApplicationRead.model_validate(app_obj)


@router.get(
    "/{application_id}/events",
    response_model=ApplicationEventList,
    summary="Get the audit log for an application",
)
async def get_my_application_events(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEventList:
    """Return the immutable audit-log history for an application."""
    try:
        events = await list_events(db, current_user.id, application_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return ApplicationEventList(
        items=[ApplicationEventRead.model_validate(e) for e in events],
        total=len(events),
    )


@router.post(
    "/{application_id}/transition",
    response_model=ApplicationRead,
    summary="Transition an application's status",
)
async def transition_my_application(
    application_id: int,
    payload: ApplicationTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """
    Apply a guarded status transition.

    - ``Matched`` / ``Rejected``: allowed from Discovered/Matched/Approved.
    - ``Approved``: requires an approved resume document.
    - ``Applied``: requires Approved + approved resume + idempotency key.
    """
    try:
        app_obj = await transition_application(
            db,
            current_user.id,
            application_id,
            to_status=payload.to_status,
            actor=f"user:{current_user.id}",
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except GuardFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return ApplicationRead.model_validate(app_obj)


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationSubmitResponse,
    summary="Prepare or submit an application via browser automation",
)
async def submit_my_application(
    application_id: int,
    payload: ApplicationSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationSubmitResponse:
    """
    Pre-fill the ATS application form (dry-run by default).

    A real submission (``dry_run=false``) requires the application to be
    ``Approved`` with an approved resume document. The application advances to
    ``Applied`` on success.
    """
    try:
        outcome = await submit_application(
            db,
            current_user.id,
            application_id,
            dry_run=payload.dry_run,
            actor=f"user:{current_user.id}",
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SubmissionBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except GuardFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    r = outcome.result
    return ApplicationSubmitResponse(
        success=r.success,
        dry_run=r.dry_run,
        ats=r.ats,
        apply_url=r.apply_url,
        fields_filled=r.fields_filled,
        evidence_paths=r.evidence_paths,
        message=r.message,
        error=r.error,
        application_id=outcome.application_id,
        application_status=outcome.application_status,
    )