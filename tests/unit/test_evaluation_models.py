"""
tests/unit/test_evaluation_models.py

Phase 3A schema tests.

All tests are offline — no network, no LLM, no database.
Tests cover: valid construction, optional fields, enum validation,
serialization round-trips, and the disclosure policy model.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.evaluation.models import (
    DisclosureLevel,
    EligibilityResult,
    EligibilityStatus,
    EvaluationResult,
    EvidenceReference,
    JobRequirements,
    PriorityLevel,
    RecommendationStatus,
    RoleMatch,
    RoleMatchStatus,
    SkillMatch,
    SkillMatchStatus,
)


# ============================================================
# Helpers
# ============================================================

def make_evidence_ref(ref_id: str = "CLAIM-001", disclosure: DisclosureLevel = DisclosureLevel.PUBLIC) -> EvidenceReference:
    return EvidenceReference(ref_id=ref_id, disclosure=disclosure)


def make_skill_match(skill: str = "Python", status: SkillMatchStatus = SkillMatchStatus.VERIFIED_MATCH) -> SkillMatch:
    return SkillMatch(skill=skill, status=status)


def make_eligibility(
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
    failed: list | None = None,
) -> EligibilityResult:
    return EligibilityResult(
        status=status,
        failed_requirements=failed or [],
    )


def make_job_requirements(job_id: str = "job-123") -> JobRequirements:
    return JobRequirements(
        job_id=job_id,
        role="Software Engineer",
        required_skills=["Python", "SQL"],
        preferred_skills=["Docker"],
    )


# ============================================================
# EvidenceReference tests
# ============================================================

class TestEvidenceReference:

    def test_valid_public_reference(self):
        ref = EvidenceReference(ref_id="CLAIM-001", disclosure=DisclosureLevel.PUBLIC)
        assert ref.ref_id == "CLAIM-001"
        assert ref.disclosure == DisclosureLevel.PUBLIC
        assert ref.is_public_safe is True
        assert ref.is_internal_only is False

    def test_valid_restricted_reference(self):
        ref = EvidenceReference(ref_id="CLAIM-002", disclosure=DisclosureLevel.RESTRICTED)
        assert ref.is_public_safe is False
        assert ref.is_internal_only is True

    def test_undetermined_defaults_to_internal_only(self):
        """Undetermined disclosure must be treated as restricted."""
        ref = EvidenceReference(ref_id="CLAIM-003")
        assert ref.disclosure == DisclosureLevel.UNDETERMINED
        assert ref.is_public_safe is False
        assert ref.is_internal_only is True

    def test_invalid_disclosure_level(self):
        with pytest.raises(ValidationError):
            EvidenceReference(ref_id="X", disclosure="classified")

    def test_ref_id_is_required(self):
        with pytest.raises(ValidationError):
            EvidenceReference(disclosure=DisclosureLevel.PUBLIC)

    def test_skill_reference(self):
        ref = EvidenceReference(ref_id="SKILL-1", disclosure=DisclosureLevel.PUBLIC)
        assert ref.ref_id == "SKILL-1"
        assert ref.is_public_safe is True

    def test_restricted_claim_002_policy(self):
        """CLAIM-002 is specifically noted as restricted. Verify the policy holds."""
        ref = EvidenceReference(ref_id="CLAIM-002", disclosure=DisclosureLevel.RESTRICTED)
        assert ref.is_internal_only is True
        assert ref.is_public_safe is False


# ============================================================
# JobRequirements tests
# ============================================================

class TestJobRequirements:

    def test_valid_minimal(self):
        req = JobRequirements(job_id="job-001")
        assert req.job_id == "job-001"
        assert req.role is None
        assert req.required_skills == []
        assert req.preferred_skills == []
        assert req.eligibility_requirements == []
        assert req.other_constraints == []

    def test_valid_full(self):
        req = JobRequirements(
            job_id="job-002",
            role="ML Engineer",
            seniority="Senior",
            domain_requirements=["NLP", "Computer Vision"],
            required_skills=["Python", "PyTorch"],
            preferred_skills=["Kubernetes"],
            education_requirements="Bachelor's in CS or related",
            experience_requirements="3+ years",
            eligibility_requirements=["Must be authorized to work in US"],
            location_requirements="San Francisco, CA",
            work_mode="hybrid",
            other_constraints=["Must pass background check"],
        )
        assert req.role == "ML Engineer"
        assert "Python" in req.required_skills
        assert req.work_mode == "hybrid"

    def test_optional_fields_remain_none(self):
        req = JobRequirements(job_id="j1")
        assert req.seniority is None
        assert req.education_requirements is None
        assert req.experience_requirements is None
        assert req.location_requirements is None
        assert req.work_mode is None

    def test_job_id_required(self):
        with pytest.raises(ValidationError):
            JobRequirements()

    def test_list_fields_default_to_empty(self):
        req = JobRequirements(job_id="j1")
        assert isinstance(req.required_skills, list)
        assert isinstance(req.preferred_skills, list)
        assert isinstance(req.domain_requirements, list)
        assert isinstance(req.eligibility_requirements, list)
        assert isinstance(req.other_constraints, list)

    def test_serialization_round_trip(self):
        req = make_job_requirements("job-serialize")
        data = req.model_dump()
        reconstructed = JobRequirements(**data)
        assert reconstructed.job_id == req.job_id
        assert reconstructed.required_skills == req.required_skills


# ============================================================
# SkillMatch tests
# ============================================================

class TestSkillMatch:

    def test_verified_match_no_evidence(self):
        sm = SkillMatch(skill="Python", status=SkillMatchStatus.VERIFIED_MATCH)
        assert sm.skill == "Python"
        assert sm.status == SkillMatchStatus.VERIFIED_MATCH
        assert sm.evidence_references == []
        assert sm.rationale is None

    def test_verified_match_with_evidence(self):
        sm = SkillMatch(
            skill="Python",
            status=SkillMatchStatus.VERIFIED_MATCH,
            evidence_references=[
                make_evidence_ref("SKILL-1"),
                make_evidence_ref("CLAIM-005"),
            ],
            rationale="Candidate has verified Python experience via SKILL-1.",
        )
        assert len(sm.evidence_references) == 2
        assert sm.rationale is not None

    def test_no_verified_evidence_status(self):
        sm = SkillMatch(skill="AWS", status=SkillMatchStatus.NO_VERIFIED_EVIDENCE)
        assert sm.status == SkillMatchStatus.NO_VERIFIED_EVIDENCE
        assert sm.evidence_references == []

    def test_partial_match(self):
        sm = SkillMatch(skill="Kubernetes", status=SkillMatchStatus.PARTIAL_MATCH)
        assert sm.status == SkillMatchStatus.PARTIAL_MATCH

    def test_uncertain_status(self):
        sm = SkillMatch(skill="Rust", status=SkillMatchStatus.UNCERTAIN)
        assert sm.status == SkillMatchStatus.UNCERTAIN

    def test_not_applicable_status(self):
        sm = SkillMatch(skill="COBOL", status=SkillMatchStatus.NOT_APPLICABLE)
        assert sm.status == SkillMatchStatus.NOT_APPLICABLE

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            SkillMatch(skill="Python", status="STRONG_MATCH")

    def test_skill_required(self):
        with pytest.raises(ValidationError):
            SkillMatch(status=SkillMatchStatus.VERIFIED_MATCH)

    def test_status_required(self):
        with pytest.raises(ValidationError):
            SkillMatch(skill="Python")


# ============================================================
# EligibilityResult tests
# ============================================================

class TestEligibilityResult:

    def test_eligible_minimal(self):
        result = EligibilityResult(status=EligibilityStatus.ELIGIBLE)
        assert result.status == EligibilityStatus.ELIGIBLE
        assert result.failed_requirements == []
        assert result.uncertain_requirements == []

    def test_eligible_with_matched(self):
        result = EligibilityResult(
            status=EligibilityStatus.ELIGIBLE,
            matched_requirements=["Bachelor's degree in CS"],
            rationale="All requirements met.",
        )
        assert len(result.matched_requirements) == 1

    def test_not_eligible_requires_failed_requirement(self):
        """NOT_ELIGIBLE with no failed requirements must raise."""
        with pytest.raises(ValidationError):
            EligibilityResult(status=EligibilityStatus.NOT_ELIGIBLE)

    def test_not_eligible_with_failed_requirement(self):
        result = EligibilityResult(
            status=EligibilityStatus.NOT_ELIGIBLE,
            failed_requirements=["Graduation year 2024 required; candidate graduated 2022"],
        )
        assert len(result.failed_requirements) == 1

    def test_uncertain_status(self):
        result = EligibilityResult(
            status=EligibilityStatus.UNCERTAIN,
            uncertain_requirements=["Work authorization status unknown"],
        )
        assert result.status == EligibilityStatus.UNCERTAIN

    def test_uncertain_does_not_require_failed(self):
        """UNCERTAIN must not require a failed requirement — uncertainty != ineligibility."""
        result = EligibilityResult(
            status=EligibilityStatus.UNCERTAIN,
        )
        assert result.failed_requirements == []

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            EligibilityResult(status="MAYBE")

    def test_status_required(self):
        with pytest.raises(ValidationError):
            EligibilityResult()

    def test_evidence_references_held(self):
        result = EligibilityResult(
            status=EligibilityStatus.ELIGIBLE,
            evidence_references=[make_evidence_ref("CLAIM-007")],
        )
        assert result.evidence_references[0].ref_id == "CLAIM-007"


# ============================================================
# RoleMatch tests
# ============================================================

class TestRoleMatch:

    def test_exact_match(self):
        rm = RoleMatch(
            requested_role="Software Engineer",
            matched_target_role="Software Engineer",
            status=RoleMatchStatus.EXACT_MATCH,
            rationale="Role matches target exactly.",
        )
        assert rm.status == RoleMatchStatus.EXACT_MATCH
        assert rm.matched_target_role == "Software Engineer"

    def test_related_match(self):
        rm = RoleMatch(
            requested_role="ML Engineer",
            matched_target_role="AI Engineer",
            status=RoleMatchStatus.RELATED_MATCH,
        )
        assert rm.status == RoleMatchStatus.RELATED_MATCH

    def test_no_match(self):
        rm = RoleMatch(
            requested_role="Accountant",
            matched_target_role=None,
            status=RoleMatchStatus.NO_MATCH,
        )
        assert rm.matched_target_role is None
        assert rm.status == RoleMatchStatus.NO_MATCH

    def test_uncertain_match(self):
        rm = RoleMatch(status=RoleMatchStatus.UNCERTAIN)
        assert rm.requested_role is None
        assert rm.matched_target_role is None

    def test_status_required(self):
        with pytest.raises(ValidationError):
            RoleMatch()

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            RoleMatch(status="MAYBE_MATCH")


# ============================================================
# EvaluationResult tests
# ============================================================

class TestEvaluationResult:

    def test_minimal_valid(self):
        """An EvaluationResult with only job_id is valid — all other fields are Optional."""
        result = EvaluationResult(job_id="job-001")
        assert result.job_id == "job-001"
        assert result.fit_score is None
        assert result.priority is None
        assert result.recommendation is None
        assert result.eligibility is None
        assert result.role_match is None
        assert result.matched_skills == []
        assert result.partial_skills == []
        assert result.missing_skills == []
        assert result.strengths == []
        assert result.gaps == []
        assert result.risks == []
        assert result.evidence_references == []

    def test_job_id_required(self):
        with pytest.raises(ValidationError):
            EvaluationResult()

    def test_fit_score_bounds(self):
        """fit_score must be 0–100."""
        EvaluationResult(job_id="j", fit_score=0.0)
        EvaluationResult(job_id="j", fit_score=100.0)
        EvaluationResult(job_id="j", fit_score=75.5)

    def test_fit_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationResult(job_id="j", fit_score=100.1)

    def test_fit_score_below_0_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationResult(job_id="j", fit_score=-1.0)

    def test_sub_scores_bounds(self):
        for field in ["technical_match", "project_match", "experience_match",
                      "preference_match", "evidence_quality"]:
            EvaluationResult(job_id="j", **{field: 50.0})

    def test_sub_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            EvaluationResult(job_id="j", technical_match=101.0)

    def test_priority_levels(self):
        for p in PriorityLevel:
            result = EvaluationResult(job_id="j", priority=p)
            assert result.priority == p

    def test_recommendation_values(self):
        for r in RecommendationStatus:
            result = EvaluationResult(job_id="j", recommendation=r)
            assert result.recommendation == r

    def test_full_result(self):
        """Construct a fully-populated EvaluationResult."""
        eligibility = EligibilityResult(
            status=EligibilityStatus.ELIGIBLE,
            matched_requirements=["Bachelor's degree"],
        )
        role_match = RoleMatch(
            requested_role="AI Engineer",
            matched_target_role="AI Engineer",
            status=RoleMatchStatus.EXACT_MATCH,
        )
        matched = [SkillMatch(skill="Python", status=SkillMatchStatus.VERIFIED_MATCH)]
        missing = [SkillMatch(skill="AWS", status=SkillMatchStatus.NO_VERIFIED_EVIDENCE)]

        result = EvaluationResult(
            job_id="job-999",
            eligibility=eligibility,
            fit_score=85.0,
            priority=PriorityLevel.STRONG,
            recommendation=RecommendationStatus.APPLY,
            role_match=role_match,
            technical_match=88.0,
            project_match=80.0,
            experience_match=75.0,
            preference_match=90.0,
            evidence_quality=70.0,
            matched_skills=matched,
            missing_skills=missing,
            strengths=["Strong Python background"],
            gaps=["No AWS experience"],
            risks=["Seniority may exceed expectations"],
            evidence_references=[
                make_evidence_ref("SKILL-1", DisclosureLevel.PUBLIC),
                make_evidence_ref("CLAIM-002", DisclosureLevel.RESTRICTED),
            ],
        )

        assert result.fit_score == 85.0
        assert result.priority == PriorityLevel.STRONG
        assert result.recommendation == RecommendationStatus.APPLY
        assert len(result.matched_skills) == 1
        assert len(result.missing_skills) == 1

    def test_restricted_evidence_in_result_is_internal_only(self):
        """Confirm CLAIM-002 (restricted) stored in evidence_references is flagged correctly."""
        result = EvaluationResult(
            job_id="job-002",
            evidence_references=[
                EvidenceReference(ref_id="CLAIM-002", disclosure=DisclosureLevel.RESTRICTED),
            ],
        )
        restricted = [r for r in result.evidence_references if r.is_internal_only]
        public_safe = [r for r in result.evidence_references if r.is_public_safe]
        assert len(restricted) == 1
        assert len(public_safe) == 0

    def test_serialization_round_trip(self):
        result = EvaluationResult(
            job_id="job-rt",
            fit_score=72.3,
            priority=PriorityLevel.REASONABLE,
            recommendation=RecommendationStatus.REVIEW,
        )
        data = result.model_dump()
        reconstructed = EvaluationResult(**data)
        assert reconstructed.job_id == result.job_id
        assert reconstructed.fit_score == result.fit_score
        assert reconstructed.priority == result.priority


# ============================================================
# Enum exhaustiveness
# ============================================================

class TestEnumExhaustiveness:

    def test_all_skill_match_statuses_are_valid(self):
        for status in SkillMatchStatus:
            sm = SkillMatch(skill="X", status=status)
            assert sm.status == status

    def test_all_eligibility_statuses_are_valid(self):
        for status in EligibilityStatus:
            if status == EligibilityStatus.NOT_ELIGIBLE:
                er = EligibilityResult(
                    status=status,
                    failed_requirements=["something failed"],
                )
            else:
                er = EligibilityResult(status=status)
            assert er.status == status

    def test_all_role_match_statuses_are_valid(self):
        for status in RoleMatchStatus:
            rm = RoleMatch(status=status)
            assert rm.status == status

    def test_all_priority_levels_are_valid(self):
        for p in PriorityLevel:
            result = EvaluationResult(job_id="j", priority=p)
            assert result.priority == p

    def test_all_recommendation_statuses_are_valid(self):
        for r in RecommendationStatus:
            result = EvaluationResult(job_id="j", recommendation=r)
            assert result.recommendation == r

    def test_all_disclosure_levels_are_valid(self):
        for d in DisclosureLevel:
            ref = EvidenceReference(ref_id="X", disclosure=d)
            assert ref.disclosure == d
