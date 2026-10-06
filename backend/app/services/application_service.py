"""
backend/app/services/application_service.py

Application workflow: a guarded state machine over ``ApplicationStatus``
with an immutable ``ApplicationEvent`` audit log.

State machine
-------------
    Discovered ──▶ Matched ──▶ Approved ──▶ Applied
         │            │           │            │
         └────────────┴───────────┴────────────┴──▶ Rejected

Guards
------
- ``Approved`` requires at least one **approved** resume document for the
  (user, job) pair — the human-review gate from Phase 6.
- ``Applied`` requires the application to currently be ``Approved`` and an
  approved resume document to still exist. It also requires an idempotency
  key so external submissions cannot be duplicated on retry.

Every transition appends an ``ApplicationEvent``. Transitions are idempotent
when an ``idempotency_key`` is supplied: replaying the same key targeting the
same status is a no-op and returns the application unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import GeneratedDocument
from app.models.job import ApplicationEvent, ApplicationStatus, JobPosting

logger = logging.getLogger(__name__)


# --- States ---
DISCOVERED = "Discovered"
MATCHED = "Matched"
APPROVED = "Approved"
APPLIED = "Applied"
REJECTED = "Rejected"

ALL_STATUSES: Set[str] = {DISCOVERED, MATCHED, APPROVED, APPLIED, REJECTED}

# --- Transition table (from -> allowed targets) ---
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    DISCOVERED: {MATCHED, REJECTED},
    MATCHED: {APPROVED, REJECTED},
    APPROVED: {APPLIED, REJECTED},
    APPLIED: {REJECTED},
    REJECTED: set(),  # terminal
}

DOC_TYPE_RESUME = "resume"
DOC_STATUS_APPROVED = "approved"


class ApplicationNotFoundError(Exception):
    """Raised when an application id does not resolve for the user."""


class ApplicationExistsError(Exception):
    """Raised when an application already exists for a (user, job) pair."""


class InvalidTransitionError(Exception):
    """Raised when a state transition is not permitted."""


class GuardFailedError(Exception):
    """Raised when a transition's precondition is not met."""


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """Return True if ``from_status -> to_status`` is an allowed transition."""
    return to_status in VALID_TRANSITIONS.get(from_status, set())


async def _has_approved_resume(
    db: AsyncSession, user_id: int, job_id: int
) -> bool:
    result = await db.execute(
        select(GeneratedDocument.id)
        .where(
            GeneratedDocument.user_id == user_id,
            GeneratedDocument.job_posting_id == job_id,
            GeneratedDocument.doc_type == DOC_TYPE_RESUME,
            GeneratedDocument.status == DOC_STATUS_APPROVED,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


def _check_guards(
    db_has_approved_resume: bool,
    from_status: str,
    to_status: str,
) -> None:
    """Validate transition preconditions (pure, given resolved evidence)."""
    if to_status == APPROVED:
        if not db_has_approved_resume:
            raise GuardFailedError(
                "Cannot approve an application without an approved resume document."
            )
    if to_status == APPLIED:
        if from_status != APPROVED:
            raise GuardFailedError("Application must be Approved before it can be Applied.")
        if not db_has_approved_resume:
            raise GuardFailedError(
                "Cannot submit an application without an approved resume document."
            )


async def record_event(
    db: AsyncSession,
    application: ApplicationStatus,
    from_status: Optional[str],
    to_status: str,
    actor: str = "system",
    reason: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    event_meta: Optional[dict] = None,
) -> ApplicationEvent:
    """Append an immutable audit event for a transition."""
    event = ApplicationEvent(
        application_id=application.id,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        reason=reason,
        idempotency_key=idempotency_key,
        event_meta=event_meta,
    )
    db.add(event)
    return event


async def create_application(
    db: AsyncSession,
    user_id: int,
    job_id: int,
    actor: Optional[str] = None,
    match_score: Optional[float] = None,
) -> ApplicationStatus:
    """
    Create a new application in the ``Discovered`` state.

    Raises:
        ApplicationExistsError: if one already exists for (user, job).
    """
    existing = await get_application_for_job(db, user_id, job_id)
    if existing is not None:
        raise ApplicationExistsError(
            f"Application already exists for user {user_id} and job {job_id}"
        )

    application = ApplicationStatus(
        user_id=user_id,
        job_posting_id=job_id,
        status=DISCOVERED,
        match_score=match_score,
    )
    db.add(application)
    await db.flush()  # assign id

    await record_event(
        db,
        application,
        from_status=None,
        to_status=DISCOVERED,
        actor=actor or f"user:{user_id}",
        reason="Application created",
    )
    await db.commit()
    await db.refresh(application)
    logger.info(f"Created application {application.id} (user={user_id}, job={job_id})")
    return application


async def get_application(
    db: AsyncSession, user_id: int, application_id: int
) -> ApplicationStatus:
    """Fetch an application owned by the user."""
    result = await db.execute(
        select(ApplicationStatus).where(
            ApplicationStatus.id == application_id,
            ApplicationStatus.user_id == user_id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise ApplicationNotFoundError(f"Application {application_id} not found")
    return application


async def get_application_for_job(
    db: AsyncSession, user_id: int, job_id: int
) -> Optional[ApplicationStatus]:
    result = await db.execute(
        select(ApplicationStatus).where(
            ApplicationStatus.user_id == user_id,
            ApplicationStatus.job_posting_id == job_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_application(
    db: AsyncSession, user_id: int, job_id: int, match_score: Optional[float] = None
) -> ApplicationStatus:
    existing = await get_application_for_job(db, user_id, job_id)
    if existing is not None:
        return existing
    return await create_application(db, user_id, job_id, match_score=match_score)


async def list_applications(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
) -> List[ApplicationStatus]:
    stmt = select(ApplicationStatus).where(ApplicationStatus.user_id == user_id)
    if status:
        stmt = stmt.where(ApplicationStatus.status == status)
    stmt = stmt.order_by(ApplicationStatus.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_events(
    db: AsyncSession, user_id: int, application_id: int
) -> List[ApplicationEvent]:
    """Return the audit log for an application owned by the user."""
    application = await get_application(db, user_id, application_id)
    result = await db.execute(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application.id)
        .order_by(ApplicationEvent.id.asc())
    )
    return list(result.scalars().all())


def _find_idempotent_event(
    events: List[ApplicationEvent], idempotency_key: str, to_status: str
) -> Optional[ApplicationEvent]:
    for event in events:
        if event.idempotency_key == idempotency_key and event.to_status == to_status:
            return event
    return None


async def transition_application(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    to_status: str,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    event_meta: Optional[dict] = None,
) -> ApplicationStatus:
    """
    Transition an application to ``to_status``, enforcing the state machine
    and guards, and appending an audit event.

    Raises:
        ApplicationNotFoundError, InvalidTransitionError, GuardFailedError.
    """
    if to_status not in ALL_STATUSES:
        raise InvalidTransitionError(
            f"Unknown status '{to_status}'. Valid: {sorted(ALL_STATUSES)}"
        )

    if to_status == APPLIED and not idempotency_key:
        raise GuardFailedError(
            "An idempotency_key is required to submit an application."
        )

    application = await get_application(db, user_id, application_id)
    from_status = application.status

    # Idempotent replay: same key + same target already recorded -> no-op.
    if idempotency_key:
        events_result = await db.execute(
            select(ApplicationEvent).where(
                ApplicationEvent.application_id == application.id,
                ApplicationEvent.idempotency_key == idempotency_key,
            )
        )
        existing_event = _find_idempotent_event(
            list(events_result.scalars().all()), idempotency_key, to_status
        )
        if existing_event is not None:
            logger.info(
                f"Idempotent replay for application {application.id} -> {to_status}"
            )
            return application

    if not is_valid_transition(from_status, to_status):
        raise InvalidTransitionError(
            f"Cannot transition from '{from_status}' to '{to_status}'"
        )

    has_resume = await _has_approved_resume(db, user_id, application.job_posting_id)
    _check_guards(has_resume, from_status, to_status)

    now = datetime.now(timezone.utc)
    application.status = to_status
    if to_status == APPROVED:
        application.approved_at = now
    elif to_status == APPLIED:
        application.applied_at = now
        if idempotency_key:
            application.idempotency_key = idempotency_key
        # Link the approved resume artifact if not already set.
        if not application.tailored_resume_s3_key:
            resume_result = await db.execute(
                select(GeneratedDocument)
                .where(
                    GeneratedDocument.user_id == user_id,
                    GeneratedDocument.job_posting_id == application.job_posting_id,
                    GeneratedDocument.doc_type == DOC_TYPE_RESUME,
                    GeneratedDocument.status == DOC_STATUS_APPROVED,
                )
                .order_by(GeneratedDocument.version.desc())
                .limit(1)
            )
            resume = resume_result.scalar_one_or_none()
            if resume is not None:
                application.tailored_resume_s3_key = resume.storage_key
    elif to_status == REJECTED:
        application.rejected_at = now

    await record_event(
        db,
        application,
        from_status=from_status,
        to_status=to_status,
        actor=actor or f"user:{user_id}",
        reason=reason,
        idempotency_key=idempotency_key,
        event_meta=event_meta,
    )

    await db.commit()
    await db.refresh(application)
    logger.info(
        f"Application {application.id}: {from_status} -> {to_status} (actor={actor})"
    )

    # Fire notifications (best-effort; never block the workflow).
    if to_status in (MATCHED, APPLIED, REJECTED):
        try:
            job_result = await db.execute(
                select(JobPosting).where(JobPosting.id == application.job_posting_id)
            )
            job = job_result.scalar_one_or_none()
            title = job.title if job else ""
            company = job.company if job else ""
            from app.services import notification_service

            if to_status == MATCHED:
                await notification_service.notify_pending_approval(
                    user_id, application.id, title, company
                )
            elif to_status == APPLIED:
                await notification_service.notify_submitted(
                    user_id, application.id, title, company
                )
            elif to_status == REJECTED:
                await notification_service.notify_rejected(
                    user_id, application.id, reason
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Notification dispatch failed: {exc}")

    return application


async def record_submission_failure(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    error: str,
    actor: str = "worker",
) -> ApplicationStatus:
    """Record a failed submission attempt without changing the state."""
    application = await get_application(db, user_id, application_id)
    application.last_error = error
    await record_event(
        db,
        application,
        from_status=application.status,
        to_status=application.status,
        actor=actor,
        reason=f"Submission failed: {error}",
    )
    await db.commit()
    await db.refresh(application)
    return application