"""
backend/app/services/browser_automation_service.py

Orchestrates human-gated application submission.

Responsibilities:
- enforce that only an **Approved** application may be submitted,
- gather public applicant data + approved document artifacts,
- respect robots.txt and per-domain rate limits,
- drive the form filler (dry-run by default),
- capture evidence,
- advance the application to Applied (idempotently) on success, or record a
  submission failure without changing state.

The form filler and rate limiter are injectable so the whole flow can be
tested without a browser or network.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.application_bot import (
    ApplicantData,
    ApplicationFormFiller,
    SubmissionRequest,
    SubmissionResult,
    get_default_form_filler,
)
from app.agents.ats_config import host_of, resolve_ats
from app.agents.politeness import DomainRateLimiter, get_rate_limiter, is_allowed_by_robots
from app.models.document import GeneratedDocument
from app.models.job import ApplicationStatus, JobPosting
from app.services.application_service import (
    APPLIED,
    APPROVED,
    REJECTED,
    GuardFailedError,
    get_application,
    record_submission_failure,
    transition_application,
)
from app.services.candidate_kb_service import load_candidate_kb
from app.services.document_storage import get_document_storage

logger = logging.getLogger(__name__)

DOC_TYPE_RESUME = "resume"
DOC_TYPE_COVER_LETTER = "cover_letter"
DOC_STATUS_APPROVED = "approved"


class SubmissionBlockedError(Exception):
    """Raised when submission preconditions are not met."""


@dataclass
class SubmitOutcome:
    """Result of a submission attempt plus resulting application state."""

    result: SubmissionResult
    application_status: str
    application_id: int


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


async def build_applicant_data(
    db: AsyncSession, user_id: int, job: JobPosting, evidence_dir: str
) -> ApplicantData:
    """Build public applicant data from the user's KB (public evidence only)."""
    kb = await load_candidate_kb(db, user_id)
    profile = kb.profile
    first, last = _split_name(profile.full_name)
    location = (
        profile.work_authorization.authorized_locations[0]
        if profile.work_authorization.authorized_locations
        else ""
    )

    # Materialise approved documents to local files for upload.
    resume_path = await _materialize_approved_doc(
        db, user_id, job.id, DOC_TYPE_RESUME, evidence_dir
    )
    cover_path = await _materialize_approved_doc(
        db, user_id, job.id, DOC_TYPE_COVER_LETTER, evidence_dir
    )

    return ApplicantData(
        first_name=first,
        last_name=last,
        full_name=profile.full_name or "",
        email=profile.email or "",
        phone="",
        location=location,
        resume_path=resume_path,
        cover_letter_path=cover_path,
    )


async def _materialize_approved_doc(
    db: AsyncSession, user_id: int, job_id: int, doc_type: str, out_dir: str
) -> Optional[str]:
    """Materialise the approved PDF artifact for browser upload."""
    result = await db.execute(
        select(GeneratedDocument)
        .where(
            GeneratedDocument.user_id == user_id,
            GeneratedDocument.job_posting_id == job_id,
            GeneratedDocument.doc_type == doc_type,
            GeneratedDocument.status == DOC_STATUS_APPROVED,
        )
        .order_by(GeneratedDocument.version.desc())
        .limit(1)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        return None

    artifacts = (doc.meta or {}).get("artifacts", {})
    artifact = artifacts.get("pdf")
    if not artifact and doc.storage_key:
        # Backward-compatible fallback for documents whose canonical PDF key
        # was persisted before nested artifact metadata was refreshed.
        artifact = {"storage_key": doc.storage_key}
    if not artifact or not artifact.get("storage_key"):
        logger.warning("Approved %s document has no PDF artifact", doc_type)
        return None

    storage = get_document_storage()
    payload = await storage.get_bytes(artifact["storage_key"])
    if payload is None:
        logger.warning("Stored PDF artifact is missing for document %s", doc.id)
        return None

    expected_sha = artifact.get("sha256")
    if expected_sha and hashlib.sha256(payload).hexdigest() != expected_sha:
        logger.error("Artifact integrity check failed for document %s", doc.id)
        return None

    os.makedirs(out_dir, exist_ok=True)
    filename = artifact.get(
        "filename", f"user{user_id}_job{job_id}_{doc_type}_v{doc.version}.pdf"
    )
    path = os.path.join(out_dir, filename)
    try:
        with open(path, "wb") as fh:
            fh.write(payload)
        return path
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not materialise {doc_type} PDF artifact: {exc}")
        return None

async def submit_application(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    dry_run: bool = True,
    form_filler: Optional[ApplicationFormFiller] = None,
    rate_limiter: Optional[DomainRateLimiter] = None,
    check_robots: bool = True,
    evidence_dir: str = "data/evidence",
    actor: Optional[str] = None,
) -> SubmitOutcome:
    """
    Prepare (and optionally submit) an application.

    Guards:
        - The application must exist and belong to the user.
        - A *real* submission requires the application to be ``Approved`` and an
          approved resume document to exist.
        - robots.txt must permit the apply URL and the domain rate limit must
          be respected.

    On a successful real submission the application transitions to ``Applied``
    with a stable idempotency key. On failure the error is recorded without
    changing state.
    """
    application = await get_application(db, user_id, application_id)

    job_result = await db.execute(
        select(JobPosting).where(JobPosting.id == application.job_posting_id)
    )
    job = job_result.scalar_one_or_none()
    if job is None:
        raise SubmissionBlockedError("Job posting not found")

    apply_url = job.application_url or job.url
    if not apply_url:
        raise SubmissionBlockedError("Job has no application URL")

    idempotency_key = f"submission:{application.id}:{job.id}"

    # Idempotent replay: a retried task may find the application already
    # Applied under the same key. Return success without re-driving the browser.
    if not dry_run and application.status == APPLIED:
        if application.idempotency_key == idempotency_key:
            logger.info(
                f"Application {application.id} already submitted (idempotent replay)"
            )
            return SubmitOutcome(
                result=SubmissionResult(
                    success=True,
                    dry_run=False,
                    ats=resolve_ats(apply_url).name,
                    apply_url=apply_url,
                    message="Already submitted (idempotent replay).",
                ),
                application_status=APPLIED,
                application_id=application.id,
            )

    # --- Guards ---
    if application.status == REJECTED:
        raise SubmissionBlockedError("Cannot submit a rejected application")

    if not dry_run:
        if application.status != APPROVED:
            raise SubmissionBlockedError(
                f"Application must be Approved to submit (currently {application.status})"
            )
        resume_exists = await _materialize_check(db, user_id, job.id)
        if not resume_exists:
            raise GuardFailedError(
                "Cannot submit without an approved resume document."
            )

    # --- Politeness ---
    if check_robots:
        allowed = await is_allowed_by_robots(apply_url)
        if not allowed:
            raise SubmissionBlockedError(
                "robots.txt disallows automated access to this apply URL"
            )

    limiter = rate_limiter or get_rate_limiter()
    host = host_of(apply_url) or "unknown"
    await limiter.acquire(host)
    try:
        applicant = await build_applicant_data(db, user_id, job, evidence_dir)
        request = SubmissionRequest(
            apply_url=apply_url,
            applicant=applicant,
            dry_run=dry_run,
            capture_evidence=True,
            evidence_dir=evidence_dir,
            ats=resolve_ats(apply_url),
        )
        filler = form_filler or get_default_form_filler()
        result = await filler.run(request)
    finally:
        limiter.release(host)

    # --- Post-processing ---
    if result.success and not result.dry_run:
        updated = await transition_application(
            db,
            user_id,
            application.id,
            APPLIED,
            actor=actor or f"worker:automation",
            reason=f"Auto-submitted via {result.ats}",
            idempotency_key=idempotency_key,
            event_meta={
                "ats": result.ats,
                "evidence": result.evidence_paths,
                "fields_filled": list(result.fields_filled.keys()),
            },
        )
        logger.info(f"Application {application.id} submitted via {result.ats}")
        return SubmitOutcome(
            result=result, application_status=updated.status, application_id=updated.id
        )

    if not result.success:
        await record_submission_failure(
            db,
            user_id,
            application.id,
            error=result.error or "Unknown submission error",
            actor=actor or "worker:automation",
        )
        logger.warning(f"Application {application.id} submission failed: {result.error}")

    return SubmitOutcome(
        result=result,
        application_status=application.status,
        application_id=application.id,
    )


async def _materialize_check(db: AsyncSession, user_id: int, job_id: int) -> bool:
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