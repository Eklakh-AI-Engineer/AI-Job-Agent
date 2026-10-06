"""
backend/app/services/cover_letter_service.py

Deterministic cover-letter generation.

The letter is composed from the job posting and the candidate's **public**
evidence only. It references matched skills and, where available, a relevant
public claim as a concrete example. It never invents achievements, employers,
or skills.

A pluggable ``narrative_hook`` may be supplied later (e.g. an LLM), but the
default implementation is fully deterministic so output is reproducible and
testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from backend.evaluation.candidate_models import CandidateKB
from backend.evaluation.models import DisclosureLevel, JobRequirements


@dataclass
class CoverLetter:
    """Structured cover letter."""

    greeting: str
    opening: str
    body_paragraphs: List[str]
    closing: str
    signature: str
    used_claim_ids: List[str] = field(default_factory=list)

    def render_text(self) -> str:
        lines: List[str] = [self.greeting, ""]
        lines.append(self.opening)
        lines.append("")
        for para in self.body_paragraphs:
            lines.append(para)
            lines.append("")
        lines.append(self.closing)
        lines.append("")
        lines.append(self.signature)
        return "\n".join(lines).strip() + "\n"


def _matched_skills(kb: CandidateKB, requirements: JobRequirements) -> List[str]:
    """Return public candidate skills that match the job's requirements."""
    job_terms = {
        s.lower()
        for s in list(requirements.required_skills) + list(requirements.preferred_skills)
    }
    matched: List[str] = []
    for skill in kb.skills.skills:
        if skill.disclosure != DisclosureLevel.PUBLIC:
            continue
        if skill.name.lower() in job_terms:
            matched.append(skill.name)
    return matched


def _pick_relevant_claim(
    kb: CandidateKB, matched_skills: List[str]
) -> Optional[str]:
    """
    Pick a public claim whose associated skills overlap with matched skills.

    Returns the claim statement (public only) or None.
    """
    matched_lower = {s.lower() for s in matched_skills}
    for claim in kb.claims.claims:
        if claim.disclosure != DisclosureLevel.PUBLIC:
            continue
        for assoc in claim.associated_skills:
            if assoc.lower() in matched_lower:
                return claim.statement
    return None


def build_cover_letter(
    kb: CandidateKB,
    requirements: JobRequirements,
    company: Optional[str] = None,
    role: Optional[str] = None,
    hiring_manager: Optional[str] = None,
) -> CoverLetter:
    """
    Build a deterministic, evidence-grounded cover letter.
    """
    profile = kb.profile
    used_claims: List[str] = []

    company_name = company or "your company"
    role_name = role or requirements.role or "this role"
    manager = hiring_manager or "Hiring Manager"

    greeting = f"Dear {manager},"

    matched = _matched_skills(kb, requirements)
    matched_text = ", ".join(matched[:6]) if matched else ""

    opening = (
        f"I am writing to express my interest in the {role_name} position at "
        f"{company_name}. As a candidate focused on {', '.join(profile.target_roles)}, "
        f"I believe my background aligns well with the requirements of this role."
    )

    body: List[str] = []

    if matched_text:
        body.append(
            f"My experience spans {matched_text}, which map directly to the "
            f"skills outlined in your posting. I have applied these in "
            f"hands-on projects and professional work."
        )
    else:
        body.append(
            "My background covers several of the core areas outlined in your "
            "posting, and I am eager to apply my skills to this role."
        )

    # Concrete evidence from a relevant public claim
    example = _pick_relevant_claim(kb, matched)
    if example:
        body.append(
            f"One example of my work: {example} I would be glad to elaborate "
            f"on how this experience translates to {company_name}'s needs."
        )
        for claim in kb.claims.claims:
            if (
                claim.disclosure == DisclosureLevel.PUBLIC
                and claim.statement == example
            ):
                used_claims.append(claim.id)
                break

    # Education / eligibility note
    edu = profile.education
    if edu.degree and edu.field_of_study:
        edu_line = (
            f"I hold a {edu.degree} in {edu.field_of_study}"
            + (f" from {edu.institution}" if edu.institution else "")
            + "."
        )
        body.append(edu_line)

    if profile.work_authorization.authorized_locations:
        body.append(
            "I am authorized to work in "
            + ", ".join(profile.work_authorization.authorized_locations)
            + "."
        )

    closing = (
        f"Thank you for considering my application. I would welcome the "
        f"opportunity to discuss how I can contribute to {company_name}."
    )

    signature = f"Sincerely,\n{profile.full_name}"

    return CoverLetter(
        greeting=greeting,
        opening=opening,
        body_paragraphs=body,
        closing=closing,
        signature=signature,
        used_claim_ids=used_claims,
    )