"""
backend/app/services/candidate_kb_service.py

Service layer for persisting and retrieving a user's Candidate Knowledge Base.

The KB document is validated against the ``CandidateKB`` Pydantic schema on
every write, so an invalid KB can never be persisted. Each save creates a new
versioned row; the previous active version is deactivated atomically.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_kb import CandidateKBRecord
from evaluation.candidate_loader import load_candidate_kb_from_dict
from evaluation.candidate_models import CandidateKB
from evaluation.models import DisclosureLevel

logger = logging.getLogger(__name__)


class CandidateKBNotFoundError(Exception):
    """Raised when a user has no persisted Candidate KB."""


class CandidateKBValidationError(Exception):
    """Raised when a KB document fails schema/cross-reference validation."""


async def get_active_kb_record(
    db: AsyncSession, user_id: int
) -> Optional[CandidateKBRecord]:
    """Return the active CandidateKBRecord for a user, or None."""
    result = await db.execute(
        select(CandidateKBRecord)
        .where(
            CandidateKBRecord.user_id == user_id,
            CandidateKBRecord.is_active.is_(True),
        )
        .order_by(CandidateKBRecord.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def load_candidate_kb(db: AsyncSession, user_id: int) -> CandidateKB:
    """
    Load and validate the active Candidate KB for a user.

    Raises:
        CandidateKBNotFoundError: if the user has no KB.
        CandidateKBValidationError: if the stored document is corrupt/invalid.
    """
    record = await get_active_kb_record(db, user_id)
    if record is None:
        raise CandidateKBNotFoundError(f"No Candidate KB found for user {user_id}")

    try:
        return load_candidate_kb_from_dict(record.data)
    except (ValueError, TypeError, KeyError) as exc:
        logger.error(f"Stored KB for user {user_id} is invalid: {exc}")
        raise CandidateKBValidationError(
            f"Stored Candidate KB is invalid: {exc}"
        ) from exc


async def load_candidate_kb_optional(
    db: AsyncSession, user_id: int
) -> Optional[CandidateKB]:
    """Load the active KB, returning None instead of raising when absent."""
    try:
        return await load_candidate_kb(db, user_id)
    except CandidateKBNotFoundError:
        return None


def validate_kb_dict(raw_data: dict) -> CandidateKB:
    """
    Validate a raw KB dictionary without persisting it.

    Raises:
        CandidateKBValidationError: if validation fails.
    """
    if not isinstance(raw_data, dict):
        raise CandidateKBValidationError("Candidate KB payload must be a JSON object")
    try:
        return load_candidate_kb_from_dict(raw_data)
    except (ValueError, TypeError, KeyError) as exc:
        raise CandidateKBValidationError(str(exc)) from exc


async def save_candidate_kb(
    db: AsyncSession,
    user_id: int,
    kb: CandidateKB,
    change_note: Optional[str] = None,
) -> CandidateKBRecord:
    """
    Persist a validated Candidate KB as a new active version.

    The previously active version (if any) is deactivated in the same
    transaction so exactly one active row exists per user.

    Returns:
        The newly created CandidateKBRecord.
    """
    # Determine next version number
    max_version_result = await db.execute(
        select(func.max(CandidateKBRecord.version)).where(
            CandidateKBRecord.user_id == user_id
        )
    )
    max_version = max_version_result.scalar() or 0
    next_version = max_version + 1

    # Deactivate all existing versions for this user
    await db.execute(
        update(CandidateKBRecord)
        .where(CandidateKBRecord.user_id == user_id)
        .values(is_active=False)
    )

    # Serialise the validated KB. Use mode="json" so enums become strings.
    data = kb.model_dump(mode="json")

    record = CandidateKBRecord(
        user_id=user_id,
        version=next_version,
        is_active=True,
        data=data,
        change_note=change_note,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info(f"Saved Candidate KB v{next_version} for user {user_id}")
    return record


async def save_candidate_kb_from_dict(
    db: AsyncSession,
    user_id: int,
    raw_data: dict,
    change_note: Optional[str] = None,
) -> CandidateKBRecord:
    """Validate and persist a raw KB dictionary."""
    kb = validate_kb_dict(raw_data)
    return await save_candidate_kb(db, user_id, kb, change_note=change_note)


async def delete_candidate_kb(db: AsyncSession, user_id: int) -> int:
    """Delete all KB versions for a user. Returns rows deleted."""
    result = await db.execute(
        select(CandidateKBRecord).where(CandidateKBRecord.user_id == user_id)
    )
    records = list(result.scalars().all())
    for record in records:
        await db.delete(record)
    await db.commit()
    logger.info(f"Deleted {len(records)} Candidate KB record(s) for user {user_id}")
    return len(records)


async def list_candidate_kb_versions(
    db: AsyncSession, user_id: int
) -> List[CandidateKBRecord]:
    """Return all KB versions for a user, newest first."""
    result = await db.execute(
        select(CandidateKBRecord)
        .where(CandidateKBRecord.user_id == user_id)
        .order_by(CandidateKBRecord.version.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Disclosure filtering
# ---------------------------------------------------------------------------

def filter_restricted_references(kb: CandidateKB) -> CandidateKB:
    """
    Return a copy of the KB with restricted/undetermined evidence references
    stripped from public-facing fields.

    The disclosure policy requires that restricted claim content never appears
    in externally visible output. This helper removes restricted claim/skill
    IDs from the serialised public representation while preserving the
    internal-only data in the database.
    """
    kb_copy = kb.model_copy(deep=True)

    for skill in kb_copy.skills.skills:
        if skill.disclosure != DisclosureLevel.PUBLIC:
            skill.evidence_claims = []

    for claim in kb_copy.claims.claims:
        if claim.disclosure != DisclosureLevel.PUBLIC:
            claim.statement = "[restricted]"
            claim.verification_source = None

    for exp in kb_copy.experience.work_experience:
        if exp.disclosure != DisclosureLevel.PUBLIC:
            exp.claims = []

    for proj in kb_copy.experience.projects:
        if proj.disclosure != DisclosureLevel.PUBLIC:
            proj.claims = []
            proj.verification_source = None

    return kb_copy


def kb_to_public_dict(kb: CandidateKB) -> dict:
    """Serialise a KB for public API output with restricted content removed."""
    filtered = filter_restricted_references(kb)
    return filtered.model_dump(mode="json")