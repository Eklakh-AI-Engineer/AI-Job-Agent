"""
tests/unit/test_browser_automation.py

Unit tests for Phase 8 browser automation.

No real browser or network is used: the form filler is faked and robots.txt
checks are bypassed or patched per test.
"""

import time

import pytest
import pytest_asyncio

from app.agents.ats_config import host_of, resolve_ats
from app.agents.politeness import DomainRateLimiter
from app.agents.application_bot import ApplicantData, SubmissionResult
from app.models.document import GeneratedDocument
from app.models.user import User
from app.schemas.job import JobPostingCreate
from app.schemas.user import UserCreate
from app.services.application_service import (
    APPLIED,
    APPROVED,
    MATCHED,
    REJECTED,
    create_application,
    get_application,
    list_events,
    transition_application,
)
from app.services.browser_automation_service import (
    SubmissionBlockedError,
    build_applicant_data,
    submit_application,
)
from app.services.candidate_kb_service import save_candidate_kb_from_dict
from app.services.document_artifacts import build_artifacts
from app.services.document_storage import LocalFilesystemStorage, build_document_key, get_document_storage, set_document_storage
from app.services.job_service import create_job
from app.services.user_service import create_user


# ---------------------------------------------------------------------------
# Fakes / helpers
# ---------------------------------------------------------------------------


class FakeFormFiller:
    def __init__(self, success: bool = True, error=None, evidence=None):
        self.success = success
        self.error = error
        self.evidence = evidence if evidence is not None else ["/tmp/evidence.png"]
        self.calls = []

    async def run(self, request):
        self.calls.append(request)
        return SubmissionResult(
            success=self.success,
            dry_run=request.dry_run,
            ats=request.ats.name,
            apply_url=request.apply_url,
            fields_filled={"email": "#email", "resume": "input[type=file]"},
            evidence_paths=list(self.evidence) if request.capture_evidence else [],
            message="fake",
            error=self.error,
        )


class NoWaitLimiter(DomainRateLimiter):
    def __init__(self):
        super().__init__(min_interval_seconds=0.0)


def make_kb_dict():
    return {
        "profile": {
            "candidate_id": "c1",
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS", "graduation_year": 2024},
            "work_authorization": {
                "authorized_locations": ["US"],
                "requires_visa_sponsorship": False,
            },
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }


@pytest_asyncio.fixture
async def ba_user(db_session):
    user = await create_user(
        db_session, UserCreate(email="ba@example.com", password="supersecret123")
    )
    return user.id


@pytest_asyncio.fixture
async def ba_job(db_session):
    job = await create_job(
        db_session,
        JobPostingCreate(
            title="AI Engineer",
            company="Acme",
            location="Remote",
            job_description="Build ML systems.",
            url="https://boards.greenhouse.io/acme/jobs/99",
            application_url="https://boards.greenhouse.io/acme/jobs/99",
            source="greenhouse",
        ),
    )
    return job.id


async def _add_approved_resume(db_session, user_id, job_id, storage_root="data/documents"):
    set_document_storage(LocalFilesystemStorage(storage_root))
    artifacts = build_artifacts(
        "APPROVED RESUME BODY",
        doc_type="resume",
        user_id=user_id,
        job_id=job_id,
        version=1,
    )
    pdf_key = build_document_key(user_id, job_id, "resume", 1, "pdf")
    await get_document_storage().put_bytes(pdf_key, artifacts["pdf"]["bytes"], artifacts["pdf"]["content_type"])
    artifacts["pdf"]["storage_key"] = pdf_key
    artifact_meta = {
        fmt: {key: value for key, value in artifact.items() if key != "bytes"}
        for fmt, artifact in artifacts.items()
    }
    doc = GeneratedDocument(
        user_id=user_id,
        job_posting_id=job_id,
        doc_type="resume",
        status="approved",
        version=1,
        content="APPROVED RESUME BODY",
        meta={"artifacts": artifact_meta},
    )
    db_session.add(doc)
    await db_session.commit()
    return doc


# ---------------------------------------------------------------------------
# ATS config
# ---------------------------------------------------------------------------


def test_ats_resolution():
    assert resolve_ats("https://boards.greenhouse.io/acme/jobs/1").name == "greenhouse"
    assert resolve_ats("https://jobs.lever.co/acme/abc").name == "lever"
    assert resolve_ats("https://acme.wd1.myworkdayjobs.com/careers").name == "workday"
    assert resolve_ats("https://example.com/apply").name == "generic"


def test_host_of():
    assert host_of("https://boards.greenhouse.io/acme/jobs/1") == "boards.greenhouse.io"
    assert host_of("") == ""


# ---------------------------------------------------------------------------
# Politeness
# ---------------------------------------------------------------------------


async def test_rate_limiter_enforces_interval():
    limiter = DomainRateLimiter(min_interval_seconds=0.05)
    start = time.monotonic()
    await limiter.acquire("example.com")
    limiter.release("example.com")
    await limiter.acquire("example.com")
    limiter.release("example.com")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05


async def test_robots_disallow_blocks_submission(db_session, ba_user, ba_job, monkeypatch):
    # Set up an Approved application with an approved resume
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)
    await _add_approved_resume(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, APPROVED)

    import app.services.browser_automation_service as svc

    async def _deny(url, user_agent="*"):
        return False

    monkeypatch.setattr(svc, "is_allowed_by_robots", _deny)

    with pytest.raises(SubmissionBlockedError, match="robots.txt"):
        await submit_application(
            db_session, ba_user, app.id, dry_run=False, form_filler=FakeFormFiller()
        )


# ---------------------------------------------------------------------------
# build_applicant_data
# ---------------------------------------------------------------------------


async def test_build_applicant_data_materializes_docs(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    await _add_approved_resume(db_session, ba_user, ba_job)

    # Fetch job
    from sqlalchemy import select

    from app.models.job import JobPosting

    job = (
        await db_session.execute(select(JobPosting).where(JobPosting.id == ba_job))
    ).scalar_one()

    data = await build_applicant_data(db_session, ba_user, job, str(tmp_path))
    assert data.first_name == "Ada"
    assert data.last_name == "Lovelace"
    assert data.email == "ada@example.com"
    assert data.location == "US"
    assert data.resume_path is not None
    import os

    assert os.path.isfile(data.resume_path)
    assert open(data.resume_path, "rb").read(4) == b"%PDF"


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


async def test_dry_run_allowed_from_matched(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)

    filler = FakeFormFiller()
    outcome = await submit_application(
        db_session,
        ba_user,
        app.id,
        dry_run=True,
        form_filler=filler,
        rate_limiter=NoWaitLimiter(),
        check_robots=False,
        evidence_dir=str(tmp_path),
    )
    assert outcome.result.success is True
    assert outcome.result.dry_run is True
    # Status unchanged
    refreshed = await get_application(db_session, ba_user, app.id)
    assert refreshed.status == MATCHED
    # Filler was actually invoked
    assert len(filler.calls) == 1


async def test_real_submit_requires_approved(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)

    with pytest.raises(SubmissionBlockedError, match="must be Approved"):
        await submit_application(
            db_session,
            ba_user,
            app.id,
            dry_run=False,
            form_filler=FakeFormFiller(),
            rate_limiter=NoWaitLimiter(),
            check_robots=False,
            evidence_dir=str(tmp_path),
        )


async def test_real_submit_rejected_application_blocked(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, REJECTED)

    with pytest.raises(SubmissionBlockedError, match="rejected"):
        await submit_application(
            db_session,
            ba_user,
            app.id,
            dry_run=False,
            form_filler=FakeFormFiller(),
            rate_limiter=NoWaitLimiter(),
            check_robots=False,
            evidence_dir=str(tmp_path),
        )


# ---------------------------------------------------------------------------
# Happy path + failure
# ---------------------------------------------------------------------------


async def test_real_submit_success_advances_to_applied(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)
    await _add_approved_resume(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, APPROVED)

    filler = FakeFormFiller(success=True)
    outcome = await submit_application(
        db_session,
        ba_user,
        app.id,
        dry_run=False,
        form_filler=filler,
        rate_limiter=NoWaitLimiter(),
        check_robots=False,
        evidence_dir=str(tmp_path),
    )
    assert outcome.result.success is True
    assert outcome.application_status == APPLIED

    refreshed = await get_application(db_session, ba_user, app.id)
    assert refreshed.status == APPLIED
    assert refreshed.applied_at is not None
    assert refreshed.idempotency_key is not None

    events = await list_events(db_session, ba_user, app.id)
    applied_events = [e for e in events if e.to_status == APPLIED]
    assert len(applied_events) == 1
    assert applied_events[0].event_meta["ats"] == "greenhouse"


async def test_real_submit_failure_records_error(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)
    await _add_approved_resume(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, APPROVED)

    filler = FakeFormFiller(success=False, error="portal timeout")
    outcome = await submit_application(
        db_session,
        ba_user,
        app.id,
        dry_run=False,
        form_filler=filler,
        rate_limiter=NoWaitLimiter(),
        check_robots=False,
        evidence_dir=str(tmp_path),
    )
    assert outcome.result.success is False

    refreshed = await get_application(db_session, ba_user, app.id)
    assert refreshed.status == APPROVED  # unchanged
    assert refreshed.last_error == "portal timeout"


async def test_idempotent_resubmit_is_noop(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)
    await _add_approved_resume(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, APPROVED)

    kwargs = dict(
        dry_run=False,
        form_filler=FakeFormFiller(),
        rate_limiter=NoWaitLimiter(),
        check_robots=False,
        evidence_dir=str(tmp_path),
    )
    o1 = await submit_application(db_session, ba_user, app.id, **kwargs)
    assert o1.application_status == APPLIED

    # Second submission uses the same idempotency key -> no duplicate event.
    o2 = await submit_application(db_session, ba_user, app.id, **kwargs)
    assert o2.application_status == APPLIED

    events = await list_events(db_session, ba_user, app.id)
    assert len([e for e in events if e.to_status == APPLIED]) == 1


async def test_ats_metadata_flows_to_request(db_session, ba_user, ba_job, tmp_path):
    await save_candidate_kb_from_dict(db_session, ba_user, make_kb_dict())
    app = await create_application(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, MATCHED)
    await _add_approved_resume(db_session, ba_user, ba_job)
    await transition_application(db_session, ba_user, app.id, APPROVED)

    filler = FakeFormFiller()
    await submit_application(
        db_session,
        ba_user,
        app.id,
        dry_run=True,
        form_filler=filler,
        rate_limiter=NoWaitLimiter(),
        check_robots=False,
        evidence_dir=str(tmp_path),
    )
    assert filler.calls[0].ats.name == "greenhouse"
    assert filler.calls[0].applicant.email == "ada@example.com"