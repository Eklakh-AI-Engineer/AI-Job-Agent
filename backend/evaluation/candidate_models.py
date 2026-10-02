"""
backend/evaluation/candidate_models.py

Pydantic models for Candidate Knowledge Base (Phase 3C).
Represents:
- Profile (identity, education, work authorization, target roles)
- Skills (canonical skills, verified evidence links, disclosure)
- Claims (verifiable factual statements, verification sources, disclosure)
- Experience (work history and project evidence)
- Preferences (work modes, locations, relocation, compensation, exclusions)
"""

from __future__ import annotations

from typing import List, Optional, Set
from pydantic import BaseModel, Field, model_validator
from .models import DisclosureLevel, EvidenceReference

APPROVED_TARGET_ROLES: Set[str] = {
    "AI Engineer",
    "ML Engineer",
    "Generative AI Engineer",
    "Software Engineer",
    "Data Scientist",
}


class Education(BaseModel):
    degree: str = Field(
        ..., description="Degree level/name, e.g. Bachelor of Technology"
    )
    field_of_study: str = Field(
        ..., description="Field of study/major, e.g. Computer Science"
    )
    institution: Optional[str] = Field(None, description="Educational institution")
    graduation_year: Optional[int] = Field(None, description="Graduation year")
    status: Optional[str] = Field(
        None, description="Status, e.g. completed, in_progress"
    )


class WorkAuthorization(BaseModel):
    authorized_locations: List[str] = Field(
        default_factory=list,
        description="Locations/countries where candidate has legal work authorization",
    )
    requires_visa_sponsorship: bool = Field(
        False,
        description="Whether candidate requires visa sponsorship in target locations",
    )


class CandidateProfile(BaseModel):
    candidate_id: str = Field(..., description="Unique identifier for candidate")
    full_name: str = Field(..., description="Candidate full name")
    email: Optional[str] = Field(None, description="Contact email")
    target_roles: List[str] = Field(
        ...,
        description="Confirmed target roles. Single source of truth. Must be in APPROVED_TARGET_ROLES.",
    )
    education: Education = Field(..., description="Educational background")
    work_authorization: WorkAuthorization = Field(
        default_factory=WorkAuthorization,
        description="Work authorization status",
    )

    @model_validator(mode="after")
    def validate_target_roles(self) -> "CandidateProfile":
        if not self.target_roles:
            raise ValueError("target_roles cannot be empty")
        for role in self.target_roles:
            if role not in APPROVED_TARGET_ROLES:
                raise ValueError(
                    f"Invalid target role '{role}'. Must be one of: {sorted(APPROVED_TARGET_ROLES)}"
                )
        return self


class SkillRecord(BaseModel):
    id: str = Field(..., description="Unique skill ID, e.g. SKILL-1")
    name: str = Field(..., description="Canonical skill name")
    category: Optional[str] = Field(None, description="Taxonomy grouping")
    verified: bool = Field(False, description="True if backed by verified claim")
    evidence_claims: List[str] = Field(
        default_factory=list,
        description="Claim IDs (CLAIM-n) providing evidence for this skill",
    )
    disclosure: DisclosureLevel = Field(
        DisclosureLevel.UNDETERMINED,
        description="Disclosure level. Defaults to undetermined.",
    )
    transferable_to: List[str] = Field(
        default_factory=list,
        description="Related skills/concepts for partial matching",
    )


class CandidateSkills(BaseModel):
    skills: List[SkillRecord] = Field(default_factory=list)


class ClaimRecord(BaseModel):
    id: str = Field(..., description="Unique claim ID, e.g. CLAIM-001")
    title: str = Field(..., description="Short title of the claim")
    statement: str = Field(
        ..., description="Factual statement of experience or achievement"
    )
    verified: bool = Field(False, description="True if backed by verifiable artifact")
    verification_source: Optional[str] = Field(
        None,
        description="Source of verification, e.g. GitHub repo, certificate",
    )
    disclosure: DisclosureLevel = Field(
        DisclosureLevel.UNDETERMINED,
        description="Disclosure level. Defaults to undetermined.",
    )
    associated_skills: List[str] = Field(
        default_factory=list,
        description="Skill IDs or names associated with this claim",
    )


class CandidateClaims(BaseModel):
    claims: List[ClaimRecord] = Field(default_factory=list)


class WorkExperienceRecord(BaseModel):
    id: str = Field(..., description="Unique work experience ID, e.g. EXP-001")
    role: str = Field(..., description="Role/job title")
    company: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Location of employment")
    work_mode: Optional[str] = Field(None, description="remote/hybrid/onsite")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM)")
    end_date: Optional[str] = Field(
        None, description="End date (YYYY-MM) or null if current"
    )
    duration_months: Optional[int] = Field(None, description="Duration in months")
    verified: bool = Field(False, description="True if employment is verified")
    disclosure: DisclosureLevel = Field(
        DisclosureLevel.UNDETERMINED,
        description="Disclosure level. Defaults to undetermined.",
    )
    claims: List[str] = Field(
        default_factory=list,
        description="Associated claim IDs (CLAIM-n)",
    )


class ProjectRecord(BaseModel):
    id: str = Field(..., description="Unique project ID, e.g. PROJ-001")
    title: str = Field(..., description="Project title")
    domain: List[str] = Field(default_factory=list, description="Domains covered")
    skills_used: List[str] = Field(
        default_factory=list, description="Skills demonstrated"
    )
    description: Optional[str] = Field(None, description="Project summary")
    verified: bool = Field(
        False, description="True if project is verified by code/demo"
    )
    verification_source: Optional[str] = Field(
        None, description="Link or reference to code"
    )
    disclosure: DisclosureLevel = Field(
        DisclosureLevel.UNDETERMINED,
        description="Disclosure level. Defaults to undetermined.",
    )
    claims: List[str] = Field(
        default_factory=list,
        description="Associated claim IDs (CLAIM-n)",
    )


class CandidateExperience(BaseModel):
    work_experience: List[WorkExperienceRecord] = Field(default_factory=list)
    projects: List[ProjectRecord] = Field(default_factory=list)


class CompensationPreference(BaseModel):
    minimum_annual: Optional[float] = Field(
        None, description="Minimum expected annual compensation"
    )
    currency: Optional[str] = Field(None, description="Currency code, e.g. USD, INR")


class CandidatePreferences(BaseModel):
    # Note: target_roles is NOT here - single source of truth is CandidateProfile.
    preferred_work_modes: List[str] = Field(
        default_factory=list,
        description="Preferred working modes: remote/hybrid/onsite",
    )
    preferred_locations: List[str] = Field(
        default_factory=list,
        description="Preferred geographic locations",
    )
    willing_to_relocate: Optional[bool] = Field(
        None,
        description="Willingness to relocate",
    )
    compensation: Optional[CompensationPreference] = Field(
        None,
        description="Compensation preferences",
    )
    excluded_companies: List[str] = Field(
        default_factory=list,
        description="Companies candidate prefers not to apply to",
    )
    excluded_domains: List[str] = Field(
        default_factory=list,
        description="Domains candidate prefers to avoid",
    )


class CandidateKB(BaseModel):
    """
    Complete in-memory Candidate Knowledge Base.
    Composed of Profile, Skills, Claims, Experience, and Preferences.
    """

    profile: CandidateProfile
    skills: CandidateSkills
    claims: CandidateClaims
    experience: CandidateExperience
    preferences: CandidatePreferences

    def get_skill(self, skill_id: str) -> Optional[SkillRecord]:
        for s in self.skills.skills:
            if s.id == skill_id:
                return s
        return None

    def get_claim(self, claim_id: str) -> Optional[ClaimRecord]:
        for c in self.claims.claims:
            if c.id == claim_id:
                return c
        return None

    def create_evidence_reference(self, ref_id: str) -> EvidenceReference:
        """
        Create a Phase 3A EvidenceReference for a given claim or skill ID.
        Never embeds claim content, only ID and disclosure level.
        """
        claim = self.get_claim(ref_id)
        if claim:
            return EvidenceReference(ref_id=claim.id, disclosure=claim.disclosure)

        skill = self.get_skill(ref_id)
        if skill:
            return EvidenceReference(ref_id=skill.id, disclosure=skill.disclosure)

        # If not found, return conservative undetermined reference
        return EvidenceReference(ref_id=ref_id, disclosure=DisclosureLevel.UNDETERMINED)
