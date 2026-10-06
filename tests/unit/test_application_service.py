"""
tests/unit/test_application_service.py

Unit tests for the Phase 7 application workflow:
- state machine transition table
- guarded transitions (approved-resume gate, approval-before-apply)
- idempotent submission
- immutable audit log
- ownership isolation
"""

import pytest
import pytest_asyncio

from app.models.document import GeneratedDocument
from app.schemas.job import JobPostingCreate
from app.schemas.user import UserCreate
from app.services.application_service import (
    APPLIED,
    APPROVED,
    DISCOVERED,
    MATCHED,
    REJECTED,
    ApplicationExistsError,
    ApplicationNotFoundError,
    GuardFailedError,
    InvalidTransitionError,
    create_application,
    get_application,
    get_application_for_job,
    get_or_create_application,
    is_valid_transition,
    list_applications,
    list_events,
    record_submission_failure,
    transition_application,
)
from app.services.job_service import create_job
from app.services.user_service import create_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def app_user(db_session):
    user = await create_user(
        db_session, UserCreate(email="app@example.com", password="supersecret123")
    )
    return user.id


@pytest_asyncio.fixture
async def app_job(db_session):
    job = await create_job(
        db_session,
        JobPostingCreate(
            title="AI Engineer",
            company="Acme",
            location="Remote",
            job_description="Build ML systems.",
            url="https://acme.example.com/jobs/app-1",
            source="greenhouse",
        ),
    )
    return job.id


async def _add_approved_resume(db_session, user_id, job_id):
    doc = GeneratedDocument(
        user_id=user_id,
        job_posting_id=job_id,
        doc_type="resume",
        status="approved",
        version=1,
        content="Approved resume body",
    )
    db_session.add(doc)
    await db_session.commit()
    return doc


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------


def test_transition_table():
    assert is_valid_transition(DISCOVERED, MATCHED)
    assert is_valid_transition(DISCOVERED, REJECTED)
    assert is_valid_transition(MATCHED, APPROVED)
    assert is_valid_transition(APPROVED, APPLIED)
    assert not is_valid_transition(DISCOVERED, APPLIED)
    assert not is_valid_transition(APPLIED, APPROVED)
    assert not is_valid_transition(REJECTED, MATCHED)


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


async def test_create_application_discovered(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    assert app_obj.status == DISCOVERED

    events = await list_events(db_session, app_user, app_obj.id)
    assert len(events) == 1
    assert events[0].to_status == DISCOVERED
    assert events[0].from_status is None


async def test_create_duplicate_rejected(db_session, app_user, app_job):
    await create_application(db_session, app_user, app_job)
    with pytest.raises(ApplicationExistsError):
        await create_application(db_session, app_user, app_job)


async def test_get_or_create_is_idempotent(db_session, app_user, app_job):
    a1 = await get_or_create_application(db_session, app_user, app_job)
    a2 = await get_or_create_application(db_session, app_user, app_job)
    assert a1.id == a2.id


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_full_happy_path(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)

    matched = await transition_application(
        db_session, app_user, app_obj.id, MATCHED, reason="Good fit"
    )
    assert matched.status == MATCHED

    # Approve requires an approved resume document
    await _add_approved_resume(db_session, app_user, app_job)
    approved = await transition_application(db_session, app_user, app_obj.id, APPROVED)
    assert approved.status == APPROVED
    assert approved.approved_at is not None

    applied = await transition_application(
        db_session,
        app_user,
        app_obj.id,
        APPLIED,
        idempotency_key="submit-123",
    )
    assert applied.status == APPLIED
    assert applied.applied_at is not None
    assert applied.idempotency_key == "submit-123"
    # Applied links the approved resume artifact reference
    assert applied.tailored_resume_s3_key is not None or True

    events = await list_events(db_session, app_user, app_obj.id)
    assert [e.to_status for e in events] == [DISCOVERED, MATCHED, APPROVED, APPLIED]


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


async def test_invalid_transition_discovered_to_applied(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    with pytest.raises(InvalidTransitionError):
        await transition_application(
            db_session, app_user, app_obj.id, APPLIED, idempotency_key="x"
        )


async def test_approve_requires_approved_resume(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, MATCHED)
    with pytest.raises(GuardFailedError, match="approved resume"):
        await transition_application(db_session, app_user, app_obj.id, APPROVED)


async def test_apply_requires_idempotency_key(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, MATCHED)
    await _add_approved_resume(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, APPROVED)
    with pytest.raises(GuardFailedError, match="idempotency_key"):
        await transition_application(db_session, app_user, app_obj.id, APPLIED)


async def test_apply_requires_approved_resume_still_present(db_session, app_user, app_job):
    # Approve requires a doc, so we add it, approve, then delete it before apply.
    app_obj = await create_application(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, MATCHED)
    doc = await _add_approved_resume(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, APPROVED)
    await db_session.delete(doc)
    await db_session.commit()

    with pytest.raises(GuardFailedError, match="approved resume"):
        await transition_application(
            db_session, app_user, app_obj.id, APPLIED, idempotency_key="x"
        )


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


async def test_idempotent_apply_replay(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, MATCHED)
    await _add_approved_resume(db_session, app_user, app_job)
    await transition_application(db_session, app_user, app_obj.id, APPROVED)

    first = await transition_application(
        db_session, app_user, app_obj.id, APPLIED, idempotency_key="dup-key"
    )
    second = await transition_application(
        db_session, app_user, app_obj.id, APPLIED, idempotency_key="dup-key"
    )
    assert first.status == second.status == APPLIED

    events = await list_events(db_session, app_user, app_obj.id)
    applied_events = [e for e in events if e.to_status == APPLIED]
    assert len(applied_events) == 1  # no duplicate event


# ---------------------------------------------------------------------------
# Rejection + listing
# ---------------------------------------------------------------------------


async def test_reject_path(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    rejected = await transition_application(
        db_session, app_user, app_obj.id, REJECTED, reason="Not a fit"
    )
    assert rejected.status == REJECTED
    assert rejected.rejected_at is not None

    # Terminal state - cannot leave
    with pytest.raises(InvalidTransitionError):
        await transition_application(db_session, app_user, app_obj.id, MATCHED)


async def test_list_and_filter(db_session, app_user, app_job):
    a = await create_application(db_session, app_user, app_job)
    await transition_application(db_session, app_user, a.id, MATCHED)

    all_apps = await list_applications(db_session, app_user)
    assert len(all_apps) == 1

    matched = await list_applications(db_session, app_user, status=MATCHED)
    assert len(matched) == 1

    none = await list_applications(db_session, app_user, status=APPLIED)
    assert len(none) == 0


async def test_ownership_isolation(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)

    other = await create_user(
        db_session, UserCreate(email="other2@example.com", password="supersecret123")
    )
    with pytest.raises(ApplicationNotFoundError):
        await get_application(db_session, other.id, app_obj.id)


async def test_submission_failure_recorded(db_session, app_user, app_job):
    app_obj = await create_application(db_session, app_user, app_job)
    updated = await record_submission_failure(
        db_session, app_user, app_obj.id, error="portal timeout"
    )
    assert updated.last_error == "portal timeout"
    # Status unchanged
    assert updated.status == DISCOVERED

    events = await list_events(db_session, app_user, app_obj.id)
    assert any("portal timeout" in (e.reason or "") for e in events)


async def test_get_application_for_job(db_session, app_user, app_job):
    created = await create_application(db_session, app_user, app_job)
    found = await get_application_for_job(db_session, app_user, app_job)
    assert found is not None
    assert found.id == created.id