"""End-to-end application pipeline over the real services.

Uses SQLite, deterministic embeddings and a local fake ATS so the test proves
service composition without external credentials or real submissions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.job import JobPostingCreate
from app.services.application_service import APPROVED, MATCHED, create_application, transition_application
from app.services.candidate_kb_service import save_candidate_kb_from_dict
from app.services.document_service import generate_cover_letter, generate_resume, update_document_status
from app.services.job_service import create_job
from app.services.browser_automation_service import submit_application
from app.agents.application_bot import SubmissionResult
from backend.evaluation.candidate_loader import load_candidate_kb_from_dir
from backend.evaluation.hybrid_ranker import rank_candidate_job


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_true_application_pipeline(db_session, tmp_storage, tmp_path):
    kb = load_candidate_kb_from_dir("tests/fixtures/candidate")
    user = type("UserRef", (), {"id": 1})()

    # Persist the same canonical candidate data consumed by document generation.
    await save_candidate_kb_from_dict(
        db_session, user.id, kb.model_dump(mode="json")
    )

    job = await create_job(
        db_session,
        JobPostingCreate(
            title="AI Engineer",
            company="Pipeline Test",
            location="Remote",
            job_description=(
                "Build AI systems with Python, PyTorch and Docker. "
                "Work on machine learning services and production APIs."
            ),
            url="https://pipeline.example/jobs/1",
            source="greenhouse",
            application_url="http://mock-ats.invalid/apply",
            required_skills=["Python", "PyTorch"],
            preferred_skills=["Docker"],
        ),
    )

    # The ranking algorithm is real; only the external embedding provider is
    # replaced with a deterministic vector for a credential-free test.
    fake_embedding = AsyncMock(return_value=[1.0] + [0.0] * 1535)
    with patch(
        "app.services.embedding_service.generate_search_embedding",
        fake_embedding,
    ):
        result, components = await rank_candidate_job(job, kb)

    assert 0.0 <= result.fit_score <= 100.0
    assert result.ranking_version == "hybrid-v1"
    assert "semantic" in components

    resume = await generate_resume(db_session, user.id, job.id)
    letter = await generate_cover_letter(db_session, user.id, job.id)
    assert resume.meta["artifacts"]["pdf"]["storage_key"].endswith(".pdf")
    assert resume.meta["artifacts"]["docx"]["storage_key"].endswith(".docx")
    assert letter.meta["artifacts"]["pdf"]["storage_key"].endswith(".pdf")
    assert letter.meta["artifacts"]["docx"]["storage_key"].endswith(".docx")

    await update_document_status(db_session, user.id, resume.id, "approved")
    application = await create_application(
        db_session, user.id, job.id, match_score=result.fit_score
    )
    await transition_application(
        db_session, user.id, application.id, MATCHED, actor="e2e"
    )
    await transition_application(
        db_session, user.id, application.id, APPROVED, actor="e2e"
    )

    captured = {}

    class FakeFiller:
        async def run(self, request):
            captured["request"] = request
            return SubmissionResult(
                success=True,
                dry_run=False,
                ats="mock",
                apply_url=request.apply_url,
                fields_filled={"resume": "input[type=file]"},
                evidence_paths=[str(tmp_path / "mock-ats.png")],
                message="Mock ATS accepted submission.",
            )

    outcome = await submit_application(
        db_session,
        user.id,
        application.id,
        dry_run=False,
        form_filler=FakeFiller(),
        check_robots=False,
        evidence_dir=str(tmp_path),
    )

    assert outcome.result.success is True
    assert outcome.application_status == "Applied"
    assert captured["request"].applicant.resume_path.endswith(".pdf")
