"""
backend/evaluation/models.py

Canonical Pydantic schemas for the Candidate–Job Evaluation Engine.

Phase 3A: schema definitions only.
No evaluation logic, no scoring, no LLM calls, no network access.

Disclosure policy
-----------------
Candidate claims carry a 'disclosure' level:
  public        – safe for public-facing outputs (resumes, LinkedIn)
  restricted    – usable as internal evidence ONLY; must NOT appear in any
                  generated document, resume section, or external output
  undetermined  – treat as restricted until explicitly reviewed

EvidenceReference holds only the claim/skill ID (a string like "CLAIM-002"
or "SKILL-1"). It does NOT embed claim content, so restricted details are
never inadvertently surfaced through the evaluation schema.

The evaluator (Phase 3C+) is responsible for NOT copying restricted claim
content into any field of EvaluationResult that may be exposed externally.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SkillMatchStatus(str, Enum):
    """Classification of how well a candidate's evidence matches a job skill."""

    VERIFIED_MATCH = "VERIFIED_MATCH"
    """Candidate has a verified, relevant claim or skill backing this requirement."""
    PARTIAL_MATCH = "PARTIAL_MATCH"
    """Candidate has transferable or partial evidence, not a direct match."""
    NO_VERIFIED_EVIDENCE = "NO_VERIFIED_EVIDENCE"
    """The skill appears in the candidate KB but has no supporting verified claim."""
    UNCERTAIN = "UNCERTAIN"
    """Whether the candidate meets this requirement cannot be determined from available data."""
    NOT_APPLICABLE = "NOT_APPLICABLE"
    """The skill/requirement is not applicable to this candidate's target role or context."""


class EligibilityStatus(str, Enum):
    """Overall eligibility verdict for a job."""

    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNCERTAIN = "UNCERTAIN"


class RoleMatchStatus(str, Enum):
    """Whether the job role aligns with the candidate's confirmed target roles."""

    EXACT_MATCH = "EXACT_MATCH"
    """Job role matches one of the candidate's target roles exactly."""
    RELATED_MATCH = "RELATED_MATCH"
    """Job role is closely related to a target role (e.g., 'AI Engineer' and 'ML Engineer')."""
    NO_MATCH = "NO_MATCH"
    """Job role is not aligned with any of the candidate's target roles."""
    UNCERTAIN = "UNCERTAIN"
    """Cannot determine alignment from available data."""


class RecommendationStatus(str, Enum):
    """Final recommendation produced by the evaluation engine."""

    APPLY = "APPLY"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class PriorityLevel(str, Enum):
    """Priority tier, derived from the overall fit score."""

    HIGH_PRIORITY = "HIGH_PRIORITY"  # 90–100
    STRONG = "STRONG"  # 80–89
    REASONABLE = "REASONABLE"  # 70–79
    REVIEW = "REVIEW"  # 60–69
    REJECT = "REJECT"  # < 60


class DisclosureLevel(str, Enum):
    """
    Disclosure level of a candidate claim or skill.

    IMPORTANT: 'restricted' claims must NEVER appear in public-facing text.
    'undetermined' must be treated as restricted until explicitly reviewed.
    """

    PUBLIC = "public"
    RESTRICTED = "restricted"
    UNDETERMINED = "undetermined"


# ---------------------------------------------------------------------------
# Evidence Reference
# ---------------------------------------------------------------------------


class EvidenceReference(BaseModel):
    """
    A reference to a specific piece of candidate evidence by ID.

    Holds only the reference ID, NOT the content of the claim/skill.
    This ensures restricted claims (e.g., CLAIM-002) are never embedded
    in evaluation output that could be exposed publicly.
    """

    ref_id: str = Field(
        ...,
        description=(
            "ID of the referenced claim or skill, e.g. 'CLAIM-002' or 'SKILL-1'. "
            "The evaluator must look up disclosure level before surfacing this reference."
        ),
        examples=["CLAIM-001", "SKILL-3"],
    )
    disclosure: DisclosureLevel = Field(
        DisclosureLevel.UNDETERMINED,
        description=(
            "Disclosure level inherited from the source claim/skill. "
            "Defaults to UNDETERMINED (treated as restricted). "
            "Must be set explicitly by the evaluator when loading from the candidate KB."
        ),
    )

    @property
    def is_public_safe(self) -> bool:
        """Returns True only if this reference is explicitly marked public."""
        return self.disclosure == DisclosureLevel.PUBLIC

    @property
    def is_internal_only(self) -> bool:
        """Returns True for references that must not appear in public-facing outputs."""
        return self.disclosure in (
            DisclosureLevel.RESTRICTED,
            DisclosureLevel.UNDETERMINED,
        )


# ---------------------------------------------------------------------------
# Job Requirements
# ---------------------------------------------------------------------------


class JobRequirements(BaseModel):
    """
    Structured representation of requirements extracted from a canonical Job.

    Phase 3A: this is a data container only.
    Phase 3B will implement the extraction logic (Job → JobRequirements).

    Fields that cannot be reliably extracted from the job description should
    be left as None or empty lists — never guessed or inferred.
    """

    job_id: str = Field(
        ...,
        description="ID of the source Job record this was extracted from.",
    )

    # Core role
    role: Optional[str] = Field(
        None,
        description="Job role/title as stated in the posting.",
    )
    seniority: Optional[str] = Field(
        None,
        description="Seniority level (e.g., 'Junior', 'Mid', 'Senior', 'Lead', 'Staff').",
    )
    domain_requirements: List[str] = Field(
        default_factory=list,
        description="Domain areas the role operates in (e.g., 'NLP', 'Computer Vision').",
    )

    # Skills
    required_skills: List[str] = Field(
        default_factory=list,
        description="Skills explicitly stated as required. Sourced from job posting.",
    )
    preferred_skills: List[str] = Field(
        default_factory=list,
        description="Skills stated as preferred or nice-to-have.",
    )

    # Education and experience
    education_requirements: Optional[str] = Field(
        None,
        description=(
            "Education requirement as stated in the posting. "
            "Represents uncertainty as None, not a guess."
        ),
    )
    experience_requirements: Optional[str] = Field(
        None,
        description="Years or type of experience required, as stated.",
    )

    # Eligibility constraints
    eligibility_requirements: List[str] = Field(
        default_factory=list,
        description=(
            "Explicit eligibility constraints from the posting "
            "(e.g., graduation year, visa, citizenship)."
        ),
    )

    # Location and working arrangement
    location_requirements: Optional[str] = Field(
        None,
        description="Location constraint as stated (e.g., 'San Francisco, CA', 'Remote-US').",
    )
    work_mode: Optional[str] = Field(
        None,
        description="Working arrangement: 'remote', 'hybrid', 'onsite', or None if unknown.",
    )

    # Other
    other_constraints: List[str] = Field(
        default_factory=list,
        description="Any other constraints not captured above.",
    )


# ---------------------------------------------------------------------------
# Skill Match
# ---------------------------------------------------------------------------


class SkillMatch(BaseModel):
    """
    Evaluation of one job skill against the candidate knowledge base.

    Phase 3C will populate these; Phase 3A defines the container.
    """

    skill: str = Field(
        ...,
        description="The skill being evaluated (as taken from JobRequirements).",
    )
    status: SkillMatchStatus = Field(
        ...,
        description="Match classification for this skill.",
    )
    evidence_references: List[EvidenceReference] = Field(
        default_factory=list,
        description=(
            "References to candidate claims/skills that support this classification. "
            "Empty for NO_VERIFIED_EVIDENCE, NOT_APPLICABLE, or UNCERTAIN."
        ),
    )
    rationale: Optional[str] = Field(
        None,
        description=(
            "Short human-readable explanation of why this status was assigned. "
            "Must NOT include content from restricted claims."
        ),
    )


# ---------------------------------------------------------------------------
# Eligibility Result
# ---------------------------------------------------------------------------


class EligibilityResult(BaseModel):
    """
    Verdict on whether the candidate meets the job's eligibility requirements.

    Uncertainty is explicit: UNCERTAIN is returned when a requirement
    cannot be evaluated, not when it is assumed to pass.
    """

    status: EligibilityStatus = Field(
        ...,
        description="Overall eligibility verdict.",
    )
    matched_requirements: List[str] = Field(
        default_factory=list,
        description="Eligibility requirements the candidate demonstrably meets.",
    )
    failed_requirements: List[str] = Field(
        default_factory=list,
        description="Eligibility requirements the candidate demonstrably does NOT meet.",
    )
    uncertain_requirements: List[str] = Field(
        default_factory=list,
        description="Requirements that could not be evaluated from available data.",
    )
    evidence_references: List[EvidenceReference] = Field(
        default_factory=list,
        description="References to candidate data used in this evaluation.",
    )
    rationale: Optional[str] = Field(
        None,
        description="Explanation of the overall eligibility verdict.",
    )

    @model_validator(mode="after")
    def not_eligible_requires_failed(self) -> "EligibilityResult":
        """
        If the overall status is NOT_ELIGIBLE, at least one failed requirement
        must be listed. This prevents silent rejections with no stated reason.
        """
        if (
            self.status == EligibilityStatus.NOT_ELIGIBLE
            and not self.failed_requirements
        ):
            raise ValueError(
                "EligibilityResult with status NOT_ELIGIBLE must list at least one "
                "failed_requirement."
            )
        return self


# ---------------------------------------------------------------------------
# Role Match
# ---------------------------------------------------------------------------


class RoleMatch(BaseModel):
    """
    Evaluation of whether the job role aligns with the candidate's target roles.

    Target roles (Phase 3, approved list):
      - AI Engineer
      - ML Engineer
      - Generative AI Engineer
      - Software Engineer
      - Data Scientist

    Do not expand this list. Do not infer role alignment.
    """

    requested_role: Optional[str] = Field(
        None,
        description="Role title as stated in the job posting.",
    )
    matched_target_role: Optional[str] = Field(
        None,
        description=(
            "The candidate target role that was matched, or None if no match. "
            "Must be one of the approved target roles."
        ),
    )
    status: RoleMatchStatus = Field(
        ...,
        description="Alignment classification.",
    )
    rationale: Optional[str] = Field(
        None,
        description="Short explanation of why this status was assigned.",
    )
    evidence_references: List[EvidenceReference] = Field(
        default_factory=list,
        description="References supporting the role alignment assessment.",
    )


# ---------------------------------------------------------------------------
# Evaluation Result
# ---------------------------------------------------------------------------


class EvaluationResult(BaseModel):
    """
    Complete, explainable result of evaluating a candidate against a job.

    Phase 3A: schema definition only. All score/match fields accept None
    until the evaluator (Phase 3C–3E) populates them.

    Disclosure policy:
    - 'strengths', 'gaps', 'risks', 'evidence_references' may be surfaced
      in internal dashboards but must be filtered before any public export.
    - The evaluator must check EvidenceReference.is_internal_only before
      including any reference in public-facing output.
    """

    # Identity
    job_id: str = Field(
        ...,
        description="ID of the Job record this evaluation was produced for.",
    )

    # Top-level verdict
    eligibility: Optional[EligibilityResult] = Field(
        None,
        description="Structured eligibility assessment.",
    )
    fit_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Overall fit score 0–100. None until scoring is run.",
    )
    priority: Optional[PriorityLevel] = Field(
        None,
        description="Priority tier derived from fit_score.",
    )
    recommendation: Optional[RecommendationStatus] = Field(
        None,
        description="Final recommendation: APPLY, REVIEW, or REJECT.",
    )

    # Sub-scores (populated by Phase 3D scorer)
    role_match: Optional[RoleMatch] = Field(
        None,
        description="Role alignment assessment.",
    )
    technical_match: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Technical skill match sub-score 0–100.",
    )
    project_match: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Project evidence sub-score 0–100.",
    )
    experience_match: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Experience alignment sub-score 0–100.",
    )
    preference_match: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Candidate preference alignment sub-score 0–100.",
    )
    evidence_quality: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Overall quality/depth of supporting evidence 0–100.",
    )

    # Skill breakdown
    matched_skills: List[SkillMatch] = Field(
        default_factory=list,
        description="Skills with VERIFIED_MATCH status.",
    )
    partial_skills: List[SkillMatch] = Field(
        default_factory=list,
        description="Skills with PARTIAL_MATCH status.",
    )
    missing_skills: List[SkillMatch] = Field(
        default_factory=list,
        description="Skills with NO_VERIFIED_EVIDENCE status.",
    )

    # Eligibility breakdown
    eligibility_issues: List[str] = Field(
        default_factory=list,
        description="Plain-text descriptions of failed eligibility requirements.",
    )

    # Narrative
    strengths: List[str] = Field(
        default_factory=list,
        description=(
            "Key strengths of the candidate relative to this job. "
            "Must NOT include content from restricted claims."
        ),
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="Notable gaps between job requirements and candidate evidence.",
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Risk factors (e.g., missing eligibility info, seniority mismatch).",
    )

    # Audit trail
    evidence_references: List[EvidenceReference] = Field(
        default_factory=list,
        description=(
            "All evidence references used in this evaluation. "
            "May include restricted references for internal use. "
            "Must be filtered by disclosure level before any external export."
        ),
    )
    ranking_version: Optional[str] = Field(None, description="Versioned candidate-job ranking configuration.")
    semantic_similarity: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Cosine similarity between candidate and job embeddings.")
    ranking_components: dict[str, float] = Field(default_factory=dict, description="Auditable component scores used by the hybrid ranker.")
