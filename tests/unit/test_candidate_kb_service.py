"""
tests/unit/test_candidate_kb_service.py

Unit tests for the persisted Candidate KB service.

Covers:
- Validation of KB dicts before save
- Disclosure filtering (restricted / undetermined redaction)
- Versioned save/load round trip
- Active-version semantics
- Delete
"""

import pytest
import pytest_asyncio

from app.schemas.user import UserCreate
from app.services.candidate_kb_service import (
    CandidateKBNotFoundError,
    CandidateKBValidationError,
    delete_candidate_kb,
    filter_restricted_references,
    get_active_kb_record,
    kb_to_public_dict,
    list_candidate_kb_versions,
    load_candidate_kb,
    load_candidate_kb_optional,
    save_candidate_kb_from_dict,
    validate_kb_dict,
)
from app.services.user_service import create_user


@pytest_asyncio.fixture
async def kb_user(db_session):
    """Create a persisted user and return its id."""
    user = await create_user(
        db_session,
        UserCreate(email="kb@example.com", password="supersecret123"),
    )
    return user.id


def make_kb_dict(target_role="AI Engineer"):
    return {
        "profile": {
            "candidate_id": "CAND-1",
            "full_name": "Test Candidate",
            "target_roles": [target_role],
            "education": {
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "graduation_year": 2024,
            },
            "work_authorization": {
                "authorized_locations": ["US"],
                "requires_visa_sponsorship": False,
            },
        },
        "skills": {
            "skills": [
                {
                    "id": "SKILL-1",
                    "name": "Python",
                    "verified": True,
                    "evidence_claims": ["CLAIM-1"],
                    "disclosure": "public",
                },
                {
                    "id": "SKILL-2",
                    "name": "Internal Only",
                    "verified": True,
                    "evidence_claims": ["CLAIM-2"],
                    "disclosure": "restricted",
                },
            ]
        },
        "claims": {
            "claims": [
                {
                    "id": "CLAIM-1",
                    "title": "Python",
                    "statement": "5 years of Python",
                    "verified": True,
                    "disclosure": "public",
                },
                {
                    "id": "CLAIM-2",
                    "title": "Internal",
                    "statement": "sensitive detail",
                    "verified": True,
                    "disclosure": "restricted",
                    "verification_source": "private-artifact",
                },
            ]
        },
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_kb_dict_accepts_valid_document():
    kb = validate_kb_dict(make_kb_dict())
    assert kb.profile.candidate_id == "CAND-1"
    assert len(kb.skills.skills) == 2


def test_validate_kb_dict_rejects_invalid_target_role():
    data = make_kb_dict(target_role="Product Manager")
    with pytest.raises(CandidateKBValidationError):
        validate_kb_dict(data)


def test_validate_kb_dict_rejects_non_dict():
    with pytest.raises(CandidateKBValidationError):
        validate_kb_dict(["not", "a", "dict"])


def test_validate_kb_dict_rejects_broken_reference():
    data = make_kb_dict()
    data["skills"]["skills"][0]["evidence_claims"] = ["CLAIM-999"]
    with pytest.raises(CandidateKBValidationError):
        validate_kb_dict(data)


# ---------------------------------------------------------------------------
# Disclosure filtering
# ---------------------------------------------------------------------------


def test_filter_restricted_redacts_restricted_claim_statement():
    kb = validate_kb_dict(make_kb_dict())
    public = kb_to_public_dict(kb)
    claims = {c["id"]: c for c in public["claims"]["claims"]}
    assert claims["CLAIM-1"]["statement"] == "5 years of Python"
    assert claims["CLAIM-2"]["statement"] == "[restricted]"
    assert claims["CLAIM-2"]["verification_source"] is None


def test_filter_restricted_strips_restricted_skill_evidence():
    kb = validate_kb_dict(make_kb_dict())
    public = kb_to_public_dict(kb)
    skills = {s["id"]: s for s in public["skills"]["skills"]}
    assert skills["SKILL-1"]["evidence_claims"] == ["CLAIM-1"]
    assert skills["SKILL-2"]["evidence_claims"] == []


def test_filter_restricted_does_not_mutate_original():
    kb = validate_kb_dict(make_kb_dict())
    _ = filter_restricted_references(kb)
    # Original still holds restricted content
    claim = kb.get_claim("CLAIM-2")
    assert claim.statement == "sensitive detail"


def test_undetermined_disclosure_is_treated_as_restricted():
    data = make_kb_dict()
    data["claims"]["claims"][0]["disclosure"] = "undetermined"
    kb = validate_kb_dict(data)
    public = kb_to_public_dict(kb)
    claims = {c["id"]: c for c in public["claims"]["claims"]}
    assert claims["CLAIM-1"]["statement"] == "[restricted]"


# ---------------------------------------------------------------------------
# DB-backed: save / load / versioning / delete
# ---------------------------------------------------------------------------


async def test_save_and_load_round_trip(db_session, kb_user):
    record = await save_candidate_kb_from_dict(db_session, kb_user, make_kb_dict())
    assert record.version == 1
    assert record.is_active is True

    kb = await load_candidate_kb(db_session, kb_user)
    assert kb.profile.candidate_id == "CAND-1"


async def test_load_raises_when_absent(db_session, kb_user):
    with pytest.raises(CandidateKBNotFoundError):
        await load_candidate_kb(db_session, kb_user)


async def test_load_optional_returns_none_when_absent(db_session, kb_user):
    assert await load_candidate_kb_optional(db_session, kb_user) is None


async def test_save_creates_incrementing_versions(db_session, kb_user):
    r1 = await save_candidate_kb_from_dict(db_session, kb_user, make_kb_dict())
    r2 = await save_candidate_kb_from_dict(
        db_session, kb_user, make_kb_dict(), change_note="update"
    )
    assert r1.version == 1
    assert r2.version == 2

    # Only one active version
    active = await get_active_kb_record(db_session, kb_user)
    assert active.version == 2
    assert active.change_note == "update"


async def test_version_history(db_session, kb_user):
    await save_candidate_kb_from_dict(db_session, kb_user, make_kb_dict())
    await save_candidate_kb_from_dict(db_session, kb_user, make_kb_dict())
    versions = await list_candidate_kb_versions(db_session, kb_user)
    assert [v.version for v in versions] == [2, 1]


async def test_delete_kb(db_session, kb_user):
    await save_candidate_kb_from_dict(db_session, kb_user, make_kb_dict())
    deleted = await delete_candidate_kb(db_session, kb_user)
    assert deleted == 1
    assert await load_candidate_kb_optional(db_session, kb_user) is None


async def test_save_rejects_invalid_document(db_session, kb_user):
    with pytest.raises(CandidateKBValidationError):
        await save_candidate_kb_from_dict(
            db_session, kb_user, make_kb_dict(target_role="Product Manager")
        )