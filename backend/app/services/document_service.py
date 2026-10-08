"""
backend/app/services/document_service.py

Orchestration for document generation and the human-review workflow.

Responsibilities:
- load the job + candidate KB,
- extract requirements,
- generate a tailored resume and/or cover letter (public evidence only),
- persist a ``GeneratedDocument`` row,
- store the rendered artifact,
- manage draft → approved/rejected review state.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import GeneratedDocument
from app.models.job import JobPosting
from app.services.candidate_kb_service import load_candidate_kb
from app.services.cover_letter_service import build_cover_letter
from app.services.document_artifacts import build_artifacts
from app.services.document_storage import build_document_key, get_document_storage
from app.services.resume_service import build_tailored_resume
from evaluation.requirements import extract_requirements

logger = logging.getLogger(__name__)

DOC_TYPE_RESUME = "resume"
DOC_TYPE_COVER_LETTER = "cover_letter"
VALID_DOC_TYPES = {DOC_TYPE_RESUME, DOC_TYPE_COVER_LETTER}

STATUS_DRAFT = "draft"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
VALID_STATUSES = {STATUS_DRAFT, STATUS_APPROVED, STATUS_REJECTED}


class DocumentNotFoundError(Exception):
    """Raised when a document id does not resolve for the user."""


class DocumentGenerationError(Exception):
    """Raised when document generation cannot proceed."""


async def _load_job(db: AsyncSession, job_id: int) -> JobPosting:
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise DocumentGenerationError(f"Job posting {job_id} not found")
    return job


async def _next_version(
    db: AsyncSession, user_id: int, job_id: int, doc_type: str
) -> int:
    from sqlalchemy import func

    result = await db.execute(
        select(func.max(GeneratedDocument.version)).where(
            GeneratedDocument.user_id == user_id,
            GeneratedDocument.job_posting_id == job_id,
            GeneratedDocument.doc_type == doc_type,
        )
    )
    return (result.scalar() or 0) + 1


async def generate_resume(
    db: AsyncSession,
    user_id: int,
    job_id: int,
    store_artifact: bool = True,
) -> GeneratedDocument:
    """
    Generate a tailored resume for (user, job) and persist it as a draft.
    """
    job = await _load_job(db, job_id)
    kb = await load_candidate_kb(db, user_id)

    requirements = extract_requirements(job)

    resume = build_tailored_resume(kb, requirements)
    content = resume.render_text()

    version = await _next_version(db, user_id, job_id, DOC_TYPE_RESUME)

    meta = {
        "ats": resume.ats,
        "header": resume.header,
        "sections": ["summary", "skills", "experience", "projects", "education"],
        "artifact_version": 1,
    }

    doc = GeneratedDocument(
        user_id=user_id,
        job_posting_id=job_id,
        doc_type=DOC_TYPE_RESUME,
        status=STATUS_DRAFT,
        version=version,
        content=content,
        meta=meta,
        used_claim_ids=resume.used_claim_ids,
    )
    db.add(doc)
    await db.flush()  # assign id

    if store_artifact:
        try:
            storage = get_document_storage()
            text_key = build_document_key(user_id, job_id, DOC_TYPE_RESUME, version, "txt")
            await storage.put(text_key, content)
            artifacts = build_artifacts(
                content, doc_type=DOC_TYPE_RESUME, user_id=user_id, job_id=job_id, version=version
            )
            artifact_meta = {}
            for fmt, artifact in artifacts.items():
                key = build_document_key(user_id, job_id, DOC_TYPE_RESUME, version, fmt)
                await storage.put_bytes(key, artifact["bytes"], artifact["content_type"])
                artifact_meta[fmt] = {k: v for k, v in artifact.items() if k != "bytes"}
                artifact_meta[fmt]["storage_key"] = key
            meta["artifacts"] = artifact_meta
            doc.meta = meta
            doc.storage_key = artifact_meta["pdf"]["storage_key"]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to store resume artifacts")
            raise DocumentGenerationError(f"Failed to persist resume artifacts: {exc}") from exc

    await db.commit()
    await db.refresh(doc)
    logger.info(f"Generated resume doc {doc.id} (user={user_id}, job={job_id}, v{version})")
    return doc


async def generate_cover_letter(
    db: AsyncSession,
    user_id: int,
    job_id: int,
    store_artifact: bool = True,
) -> GeneratedDocument:
    """
    Generate a cover letter for (user, job) and persist it as a draft.
    """
    job = await _load_job(db, job_id)
    kb = await load_candidate_kb(db, user_id)

    requirements = extract_requirements(job)

    letter = build_cover_letter(
        kb,
        requirements,
        company=job.company,
        role=job.title,
    )
    content = letter.render_text()

    version = await _next_version(db, user_id, job_id, DOC_TYPE_COVER_LETTER)

    doc = GeneratedDocument(
        user_id=user_id,
        job_posting_id=job_id,
        doc_type=DOC_TYPE_COVER_LETTER,
        status=STATUS_DRAFT,
        version=version,
        content=content,
        meta={"company": job.company, "role": job.title, "artifact_version": 1},
        used_claim_ids=letter.used_claim_ids,
    )
    db.add(doc)
    await db.flush()

    if store_artifact:
        try:
            storage = get_document_storage()
            text_key = build_document_key(user_id, job_id, DOC_TYPE_COVER_LETTER, version, "txt")
            await storage.put(text_key, content)
            artifacts = build_artifacts(
                content, doc_type=DOC_TYPE_COVER_LETTER, user_id=user_id, job_id=job_id, version=version
            )
            artifact_meta = {}
            for fmt, artifact in artifacts.items():
                key = build_document_key(user_id, job_id, DOC_TYPE_COVER_LETTER, version, fmt)
                await storage.put_bytes(key, artifact["bytes"], artifact["content_type"])
                artifact_meta[fmt] = {k: v for k, v in artifact.items() if k != "bytes"}
                artifact_meta[fmt]["storage_key"] = key
            meta = dict(doc.meta or {})
            meta["artifacts"] = artifact_meta
            doc.meta = meta
            doc.storage_key = artifact_meta["pdf"]["storage_key"]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to store cover-letter artifacts")
            raise DocumentGenerationError(f"Failed to persist cover-letter artifacts: {exc}") from exc

    await db.commit()
    await db.refresh(doc)
    logger.info(
        f"Generated cover letter doc {doc.id} (user={user_id}, job={job_id}, v{version})"
    )
    return doc


async def get_document(
    db: AsyncSession, user_id: int, document_id: int
) -> GeneratedDocument:
    result = await db.execute(
        select(GeneratedDocument).where(
            GeneratedDocument.id == document_id,
            GeneratedDocument.user_id == user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise DocumentNotFoundError(f"Document {document_id} not found")
    return doc


async def list_documents(
    db: AsyncSession,
    user_id: int,
    job_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[GeneratedDocument]:
    stmt = select(GeneratedDocument).where(GeneratedDocument.user_id == user_id)
    if job_id is not None:
        stmt = stmt.where(GeneratedDocument.job_posting_id == job_id)
    if doc_type:
        stmt = stmt.where(GeneratedDocument.doc_type == doc_type)
    if status:
        stmt = stmt.where(GeneratedDocument.status == status)
    stmt = stmt.order_by(GeneratedDocument.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_document_status(
    db: AsyncSession,
    user_id: int,
    document_id: int,
    status: str,
) -> GeneratedDocument:
    """Approve or reject a document (human-review gate)."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {sorted(VALID_STATUSES)}")

    doc = await get_document(db, user_id, document_id)
    doc.status = status
    await db.commit()
    await db.refresh(doc)
    logger.info(f"Document {document_id} status -> {status}")
    return doc


async def update_document_content(
    db: AsyncSession,
    user_id: int,
    document_id: int,
    content: str,
) -> GeneratedDocument:
    """Apply a manual edit to a document's content."""
    doc = await get_document(db, user_id, document_id)
    doc.content = content
    # Edits invalidate prior approval
    doc.status = STATUS_DRAFT
    await db.commit()
    await db.refresh(doc)
    return doc


async def regenerate_document(
    db: AsyncSession,
    user_id: int,
    document_id: int,
) -> GeneratedDocument:
    """Regenerate a document (creates a new version)."""
    doc = await get_document(db, user_id, document_id)
    if doc.doc_type == DOC_TYPE_RESUME:
        return await generate_resume(db, user_id, doc.job_posting_id)
    elif doc.doc_type == DOC_TYPE_COVER_LETTER:
        return await generate_cover_letter(db, user_id, doc.job_posting_id)
    else:
        raise DocumentGenerationError(f"Unknown doc_type: {doc.doc_type}")