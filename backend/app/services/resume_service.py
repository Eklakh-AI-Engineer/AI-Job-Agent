"""
backend/app/services/resume_service.py

Deterministic resume tailoring.

Builds a resume from a candidate's **public** evidence only, ordered to
emphasise the skills a specific job requires. No content is invented: every
line traces back to a claim, skill, experience, or project in the candidate KB.

Restricted and undetermined evidence is never included in the output, and the
set of referenced claim IDs is returned for the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from app.services.ats_service import analyze_ats, extract_job_keywords
from backend.evaluation.candidate_models import CandidateKB
from backend.evaluation.models import DisclosureLevel, JobRequirements


@dataclass
class TailoredResume:
    """Structured, job-tailored resume."""

    header: Dict[str, str]
    summary: str
    skills: List[str]
    experience: List[Dict[str, str]]
    projects: List[Dict[str, str]]
    education: Dict[str, str]
    used_claim_ids: List[str] = field(default_factory=list)
    ats: Dict = field(default_factory=dict)

    def render_text(self) -> str:
        """Render the resume as plain text (ATS-friendly)."""
        lines: List[str] = []
        h = self.header
        lines.append(h.get("name", ""))
        contact = " | ".join(
            v for v in [h.get("email", ""), h.get("location", "")] if v
        )
        if contact:
            lines.append(contact)
        lines.append("")

        if self.summary:
            lines.append("SUMMARY")
            lines.append(self.summary)
            lines.append("")

        if self.skills:
            lines.append("SKILLS")
            lines.append(", ".join(self.skills))
            lines.append("")

        if self.experience:
            lines.append("EXPERIENCE")
            for exp in self.experience:
                dates = exp.get("dates", "")
                header = f"{exp.get('role', '')} — {exp.get('company', '')}"
                if dates:
                    header += f" ({dates})"
                lines.append(header)
                if exp.get("highlights"):
                    lines.append(exp["highlights"])
                lines.append("")
            lines.append("")

        if self.projects:
            lines.append("PROJECTS")
            for proj in self.projects:
                lines.append(proj.get("title", ""))
                if proj.get("description"):
                    lines.append(proj["description"])
                if proj.get("skills"):
                    lines.append(f"Technologies: {proj['skills']}")
                lines.append("")
            lines.append("")

        if self.education:
            e = self.education
            lines.append("EDUCATION")
            edu_line = f"{e.get('degree', '')}, {e.get('field_of_study', '')}"
            if e.get("institution"):
                edu_line += f" — {e['institution']}"
            if e.get("graduation_year"):
                edu_line += f" ({e['graduation_year']})"
            lines.append(edu_line)

        return "\n".join(lines).strip() + "\n"


def _skill_relevance(skill_name: str, job_keywords: List[str]) -> int:
    """Lower is better. Skills matching job keywords sort first."""
    name = skill_name.lower()
    for i, kw in enumerate(job_keywords):
        if name == kw.lower():
            return i
    return len(job_keywords) + 1


def build_tailored_resume(
    kb: CandidateKB,
    requirements: JobRequirements,
) -> TailoredResume:
    """
    Build a job-tailored resume from the candidate's public evidence.
    """
    job_keywords = extract_job_keywords(requirements)
    used_claims: Set[str] = set()

    # --- Header ---
    profile = kb.profile
    header = {
        "name": profile.full_name,
        "email": profile.email or "",
        "location": (
            profile.work_authorization.authorized_locations[0]
            if profile.work_authorization.authorized_locations
            else ""
        ),
    }

    # --- Skills (public, ordered by job relevance) ---
    public_skills = [
        s for s in kb.skills.skills if s.disclosure == DisclosureLevel.PUBLIC
    ]
    # Only include verified skills whose evidence is public
    skills_sorted = sorted(
        public_skills, key=lambda s: _skill_relevance(s.name, job_keywords)
    )
    skill_names: List[str] = []
    for s in skills_sorted:
        skill_names.append(s.name)
        for cid in s.evidence_claims:
            used_claims.add(cid)

    # --- Experience (public only) ---
    experience: List[Dict[str, str]] = []
    for exp in sorted(
        kb.experience.work_experience, key=lambda e: e.end_date or "9999", reverse=True
    ):
        if exp.disclosure != DisclosureLevel.PUBLIC:
            continue
        highlights = []
        for cid in exp.claims:
            claim = kb.get_claim(cid)
            if claim and claim.disclosure == DisclosureLevel.PUBLIC:
                highlights.append(claim.statement)
                used_claims.add(cid)
        dates = ""
        if exp.start_date or exp.end_date:
            dates = f"{exp.start_date or '?'} – {exp.end_date or 'Present'}"
        experience.append(
            {
                "role": exp.role,
                "company": exp.company,
                "dates": dates,
                "highlights": " ".join(highlights),
            }
        )

    # --- Projects (public only) ---
    projects: List[Dict[str, str]] = []
    for proj in kb.experience.projects:
        if proj.disclosure != DisclosureLevel.PUBLIC:
            continue
        for cid in proj.claims:
            used_claims.add(cid)
        projects.append(
            {
                "title": proj.title,
                "description": proj.description or "",
                "skills": ", ".join(proj.skills_used),
            }
        )

    # --- Education ---
    education = {
        "degree": profile.education.degree,
        "field_of_study": profile.education.field_of_study,
        "institution": profile.education.institution or "",
        "graduation_year": str(profile.education.graduation_year or ""),
    }

    # --- Summary (deterministic, no fabrication) ---
    matched = [s for s in skill_names if any(s.lower() == k.lower() for k in job_keywords)]
    role = requirements.role or "the target role"
    if matched:
        summary = (
            f"Candidate targeting {role}, with verified experience in "
            f"{', '.join(matched[:8])}."
        )
    else:
        summary = f"Candidate targeting {role}."

    resume = TailoredResume(
        header=header,
        summary=summary,
        skills=skill_names,
        experience=experience,
        projects=projects,
        education=education,
        used_claim_ids=sorted(used_claims),
    )

    # Compute ATS analysis on the rendered text
    ats = analyze_ats(resume.render_text(), requirements, kb)
    resume.ats = ats.to_dict()

    return resume