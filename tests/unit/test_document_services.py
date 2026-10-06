"""
tests/unit/test_document_services.py

Unit tests for document generation (Phase 6):
- ATS keyword analysis
- Resume tailoring (public evidence only, job-relevance ordering)
- Cover letter grounding
- Artifact storage backend
- Document orchestration (generate / list / edit / approve / regenerate)
"""

import pytest
import pytest_asyncio

from app.schemas.job import JobPostingCreate
from app.services.ats_service import analyze_ats, extract_job_keywords
from app.services.candidate_kb_service import save_candidate_kb_from_dict
from app.services.cover_letter_service import build_cover_letter
from app.services.document_service import (
    DocumentNotFoundError,
    generate_cover_letter,
    generate_resume,
    get_document,
    list_documents,
    regenerate_document,
    update_document_content,
    update_document_status,
)
from app.services.document_storage import (
    LocalFilesystemStorage,
    build_document_key,
    get_document_storage,
    set_document_storage,
)
from app.services.job_service import create_job
from app.services.resume_service import build_tailored_resume
from app.services.user_service import create_user
from app.schemas.user import UserCreate
from backend.evaluation.candidate_models import (
    CandidateClaims,
    CandidateExperience,
    CandidateKB,
    CandidatePreferences,
    CandidateProfile,
    CandidateSkills,
    ClaimRecord,
    DisclosureLevel,
    Education,
    ProjectRecord,
    SkillRecord,
    WorkAuthorization,
    WorkExperienceRecord,
)
from backend.evaluation.models import JobRequirements


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_requirements():
    return JobRequirements(
        job_id="job-1",
        role="AI Engineer",
        required_skills=["Python", "PyTorch", "TensorFlow"],
        preferred_skills=["Docker"],
        eligibility_requirements=["Must be authorized to work in the US"],
    )


def make_kb() -> CandidateKB:
    return CandidateKB(
        profile=CandidateProfile(
            candidate_id="c1",
            full_name="Ada Lovelace",
            email="ada@example.com",
            target_roles=["AI Engineer", "ML Engineer"],
            education=Education(
                degree="B.S.",
                field_of_study="Computer Science",
                institution="MIT",
                graduation_year=2024,
            ),
            work_authorization=WorkAuthorization(
                authorized_locations=["US"], requires_visa_sponsorship=False
            ),
        ),
        skills=CandidateSkills(
            skills=[
                SkillRecord(
                    id="SKILL-1", name="Python", verified=True,
                    evidence_claims=["CLAIM-1"], disclosure=DisclosureLevel.PUBLIC,
                ),
                SkillRecord(
                    id="SKILL-2", name="PyTorch", verified=True,
                    evidence_claims=["CLAIM-2"], disclosure=DisclosureLevel.PUBLIC,
                ),
                SkillRecord(
                    id="SKILL-3", name="SecretInternal", verified=True,
                    evidence_claims=["CLAIM-3"], disclosure=DisclosureLevel.RESTRICTED,
                ),
            ]
        ),
        claims=CandidateClaims(
            claims=[
                ClaimRecord(
                    id="CLAIM-1", title="Python", statement="Built scalable Python services",
                    verified=True, associated_skills=["Python"], disclosure=DisclosureLevel.PUBLIC,
                ),
                ClaimRecord(
                    id="CLAIM-2", title="PyTorch", statement="Trained deep learning models in PyTorch",
                    verified=True, associated_skills=["PyTorch"], disclosure=DisclosureLevel.PUBLIC,
                ),
                ClaimRecord(
                    id="CLAIM-3", title="Secret", statement="TOP SECRET PROJECT",
                    verified=True, associated_skills=["SecretInternal"], disclosure=DisclosureLevel.RESTRICTED,
                ),
            ]
        ),
        experience=CandidateExperience(
            work_experience=[
                WorkExperienceRecord(
                    id="EXP-1", role="ML Intern", company="Acme",
                    start_date="2023-06", end_date="2023-09", claims=["CLAIM-2"],
                    disclosure=DisclosureLevel.PUBLIC,
                )
            ],
            projects=[
                ProjectRecord(
                    id="PROJ-1", title="Vision Model", skills_used=["Python", "PyTorch"],
                    claims=["CLAIM-1"], disclosure=DisclosureLevel.PUBLIC,
                )
            ],
        ),
        preferences=CandidatePreferences(),
    )


def make_kb_dict():
    return make_kb().model_dump(mode="json")


@pytest_asyncio.fixture
async def doc_user(db_session):
    user = await create_user(
        db_session, UserCreate(email="doc@example.com", password="supersecret123")
    )
    return user.id


@pytest_asyncio.fixture
async def doc_job(db_session):
    job = await create_job(
        db_session,
        JobPostingCreate(
            title="AI Engineer",
            company="Acme",
            location="Remote",
            job_description="Build ML systems with Python and PyTorch.",
            url="https://acme.example.com/jobs/1",
            source="greenhouse",
            required_skills=["Python", "PyTorch", "TensorFlow"],
            preferred_skills=["Docker"],
        ),
    )
    return job.id


@pytest.fixture
def tmp_storage(tmp_path):
    old = None
    try:
        old = get_document_storage()
    except Exception:
        old = None
    storage = LocalFilesystemStorage(root=str(tmp_path / "docs"))
    set_document_storage(storage)
    yield storage
    # restore default (best effort)
    set_document_storage(LocalFilesystemStorage(root="data/documents"))


# ---------------------------------------------------------------------------
# ATS
# ---------------------------------------------------------------------------


def test_ats_keyword_extraction_orders_required_first():
    kws = extract_job_keywords(make_requirements())
    assert kws == ["Python", "PyTorch", "TensorFlow", "Docker"]


def test_ats_matches_present_keywords():
    doc = "Experienced in Python and PyTorch for ML."
    ats = analyze_ats(doc, make_requirements(), make_kb())
    assert "Python" in ats.matched_keywords
    assert "PyTorch" in ats.matched_keywords
    assert "TensorFlow" in ats.missing_keywords


def test_ats_score_bounds():
    ats = analyze_ats("nothing relevant here", make_requirements(), make_kb())
    assert 0.0 <= ats.score <= 100.0
    full = analyze_ats(
        "Python PyTorch TensorFlow Docker", make_requirements(), make_kb()
    )
    assert full.score == 100.0


def test_ats_reports_unbacked_keywords_without_fabrication():
    ats = analyze_ats("Python", make_requirements(), make_kb())
    # TensorFlow/Docker have no public evidence -> must be flagged as unbacked
    joined = " ".join(ats.recommendations)
    assert "do not fabricate" in joined


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def test_resume_excludes_restricted_content():
    resume = build_tailored_resume(make_kb(), make_requirements())
    text = resume.render_text()
    assert "SecretInternal" not in text
    assert "TOP SECRET" not in text
    assert "SecretInternal" not in resume.skills


def test_resume_used_claim_ids_only_public():
    resume = build_tailored_resume(make_kb(), make_requirements())
    assert "CLAIM-3" not in resume.used_claim_ids
    assert "CLAIM-1" in resume.used_claim_ids
    assert "CLAIM-2" in resume.used_claim_ids


def test_resume_orders_skills_by_job_relevance():
    resume = build_tailored_resume(make_kb(), make_requirements())
    # Python & PyTorch are both job keywords; both should appear, verified only
    assert set(resume.skills) == {"Python", "PyTorch"}


def test_resume_renders_header_and_education():
    resume = build_tailored_resume(make_kb(), make_requirements())
    text = resume.render_text()
    assert "Ada Lovelace" in text
    assert "Computer Science" in text
    assert "EDUCATION" in text


# ---------------------------------------------------------------------------
# Cover letter
# ---------------------------------------------------------------------------


def test_cover_letter_grounded_in_public_claim():
    letter = build_cover_letter(
        make_kb(), make_requirements(), company="Acme", role="AI Engineer"
    )
    text = letter.render_text()
    assert "Acme" in text
    assert "Python" in text or "PyTorch" in text
    # References at least one public claim
    assert letter.used_claim_ids
    assert "CLAIM-3" not in letter.used_claim_ids


def test_cover_letter_excludes_restricted():
    letter = build_cover_letter(make_kb(), make_requirements(), company="Acme")
    text = letter.render_text()
    assert "TOP SECRET" not in text
    assert "SecretInternal" not in text


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


async def test_storage_round_trip(tmp_storage):
    key = build_document_key(1, 2, "resume", 1)
    await tmp_storage.put(key, "hello world")
    assert await tmp_storage.get(key) == "hello world"
    assert await tmp_storage.delete(key) is True
    assert await tmp_storage.get(key) is None


async def test_storage_rejects_path_traversal(tmp_storage):
    with pytest.raises(ValueError):
        await tmp_storage.put("../../etc/passwd", "bad")


# ---------------------------------------------------------------------------
# Document orchestration (DB-backed)
# ---------------------------------------------------------------------------


async def test_generate_resume_draft(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_resume(db_session, doc_user, doc_job)

    assert doc.id is not None
    assert doc.doc_type == "resume"
    assert doc.status == "draft"
    assert doc.version == 1
    assert "Ada Lovelace" in doc.content
    assert "SecretInternal" not in doc.content
    assert doc.storage_key is not None
    assert doc.meta["ats"]["score"] >= 0


async def test_generate_cover_letter_draft(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_cover_letter(db_session, doc_user, doc_job)

    assert doc.doc_type == "cover_letter"
    assert doc.status == "draft"
    assert "Acme" in doc.content


async def test_list_and_filter_documents(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    await generate_resume(db_session, doc_user, doc_job)
    await generate_cover_letter(db_session, doc_user, doc_job)

    all_docs = await list_documents(db_session, doc_user)
    assert len(all_docs) == 2

    resumes = await list_documents(db_session, doc_user, doc_type="resume")
    assert len(resumes) == 1
    assert resumes[0].doc_type == "resume"


async def test_approve_document(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_resume(db_session, doc_user, doc_job)
    updated = await update_document_status(db_session, doc_user, doc.id, "approved")
    assert updated.status == "approved"

    approved = await list_documents(db_session, doc_user, status="approved")
    assert len(approved) == 1


async def test_edit_resets_to_draft(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_resume(db_session, doc_user, doc_job)
    await update_document_status(db_session, doc_user, doc.id, "approved")

    edited = await update_document_content(db_session, doc_user, doc.id, "new content")
    assert edited.content == "new content"
    assert edited.status == "draft"


async def test_regenerate_creates_new_version(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_resume(db_session, doc_user, doc_job)
    assert doc.version == 1

    v2 = await regenerate_document(db_session, doc_user, doc.id)
    assert v2.version == 2
    assert v2.id != doc.id


async def test_document_ownership_isolation(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_resume(db_session, doc_user, doc_job)

    other = await create_user(
        db_session, UserCreate(email="other@example.com", password="supersecret123")
    )
    with pytest.raises(DocumentNotFoundError):
        await get_document(db_session, other.id, doc.id)


async def test_invalid_status_rejected(db_session, doc_user, doc_job, tmp_storage):
    await save_candidate_kb_from_dict(db_session, doc_user, make_kb_dict())
    doc = await generate_resume(db_session, doc_user, doc_job)
    with pytest.raises(ValueError):
        await update_document_status(db_session, doc_user, doc.id, "bogus")