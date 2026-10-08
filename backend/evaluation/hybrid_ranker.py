"""Candidate ↔ job hybrid ranking.

Combines deterministic evidence-based evaluation with semantic similarity.
The ranking is versioned, deterministic for a fixed embedding/model, and
returns its component scores for auditability.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

from evaluation.candidate_models import CandidateKB
from evaluation.models import (
    EligibilityStatus,
    EvaluationResult,
    JobRequirements,
    RoleMatchStatus,
)
from evaluation.evaluator import evaluate_candidate_against_job


RANKING_VERSION = "hybrid-v1"
RANKING_WEIGHTS = {
    "semantic": 0.25,
    "technical": 0.30,
    "role": 0.15,
    "experience": 0.10,
    "education": 0.05,
    "preference": 0.10,
    "evidence": 0.05,
}


def _parse_required_years(text: str | None) -> float | None:
    if not text:
        return None
    matches = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", text.lower())]
    return max(matches) if matches else None


def _candidate_experience_years(kb: CandidateKB) -> float:
    months = sum(
        exp.duration_months or 0
        for exp in kb.experience.work_experience
        if exp.verified
    )
    return months / 12.0


def experience_score(requirements: JobRequirements, kb: CandidateKB) -> float:
    required = _parse_required_years(requirements.experience_requirements)
    if required is None or required <= 0:
        return 50.0
    actual = _candidate_experience_years(kb)
    if actual >= required:
        return 100.0
    if actual >= required * 0.75:
        return 75.0
    if actual >= required * 0.5:
        return 50.0
    return 0.0


def education_score(requirements: JobRequirements, kb: CandidateKB) -> float:
    requirement = (requirements.education_requirements or "").lower()
    if not requirement:
        return 50.0
    degree = kb.profile.education.degree.lower()
    field = kb.profile.education.field_of_study.lower()
    if any(token in requirement for token in ("bachelor", "b.tech", "undergraduate")):
        if "bachelor" in degree or "b.tech" in degree or "btech" in degree:
            return 100.0
    if any(token in requirement for token in ("master", "m.tech", "graduate")):
        if "master" in degree or "m.tech" in degree or "mtech" in degree:
            return 100.0
    if field and field in requirement:
        return 100.0
    return 50.0


def preference_score(job, kb: CandidateKB) -> float:
    preferences = kb.preferences
    company = (job.company or "").lower()
    if any(company == excluded.lower() for excluded in preferences.excluded_companies):
        return 0.0

    score_parts = []
    if preferences.preferred_work_modes:
        mode = (job.work_mode or "").lower()
        score_parts.append(
            100.0 if any(mode == x.lower() for x in preferences.preferred_work_modes) else 0.0
        )
    if preferences.preferred_locations:
        location = (job.location or "").lower()
        score_parts.append(
            100.0 if any(x.lower() in location for x in preferences.preferred_locations) else 50.0
        )
    return sum(score_parts) / len(score_parts) if score_parts else 50.0


def candidate_text(kb: CandidateKB) -> str:
    """Build a stable semantic representation from public candidate evidence."""
    skills = ", ".join(sorted(s.name for s in kb.skills.skills))
    roles = ", ".join(kb.profile.target_roles)
    projects = " ".join(
        f"{p.title}: {' '.join(p.skills_used)} {p.description or ''}"
        for p in kb.experience.projects
        if p.verified
    )
    experience = " ".join(
        f"{e.role} at {e.company}"
        for e in kb.experience.work_experience
        if e.verified
    )
    return (
        f"Target roles: {roles}. Skills: {skills}. "
        f"Experience: {experience}. Projects: {projects}. "
        f"Education: {kb.profile.education.degree} in {kb.profile.education.field_of_study}."
    )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("Embedding vectors must be non-empty and have equal dimensions.")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_score(similarity: float) -> float:
    return round(max(0.0, min(100.0, ((similarity + 1.0) / 2.0) * 100.0)), 2)


async def rank_candidate_job(job, candidate_kb: CandidateKB) -> Tuple[EvaluationResult, Dict[str, float]]:
    """Rank a canonical JobPosting against a candidate KB."""
    from app.services.embedding_service import generate_search_embedding
    from app.services.job_detail_extraction import clean_job_text

    requirements = __import__("backend.evaluation.requirements", fromlist=["extract_requirements"]).extract_requirements(job)
    evaluation = evaluate_candidate_against_job(requirements, candidate_kb)

    job_text = clean_job_text(
        f"{job.title}. {job.company}. {job.location or ''}. "
        f"{job.job_description}. Required skills: {', '.join(job.required_skills or [])}"
    )
    result = await generate_search_embedding(job_text)
    candidate_result = await generate_search_embedding(candidate_text(candidate_kb))
    similarity = cosine_similarity(result, candidate_result)

    components = {
        "semantic": semantic_score(similarity),
        "technical": evaluation.technical_match or 0.0,
        "role": {
            RoleMatchStatus.EXACT_MATCH: 100.0,
            RoleMatchStatus.RELATED_MATCH: 75.0,
            RoleMatchStatus.UNCERTAIN: 50.0,
            RoleMatchStatus.NO_MATCH: 0.0,
        }[evaluation.role_match.status] if evaluation.role_match else 50.0,
        "experience": experience_score(requirements, candidate_kb),
        "education": education_score(requirements, candidate_kb),
        "preference": preference_score(job, candidate_kb),
        "evidence": evaluation.evidence_quality or 0.0,
    }

    if evaluation.eligibility and evaluation.eligibility.status == EligibilityStatus.NOT_ELIGIBLE:
        ranking_score = 0.0
    else:
        ranking_score = sum(components[k] * RANKING_WEIGHTS[k] for k in RANKING_WEIGHTS)
        ranking_score = round(max(0.0, min(100.0, ranking_score)), 2)

    priority = evaluation.priority
    recommendation = evaluation.recommendation
    if ranking_score >= 90:
        from evaluation.models import PriorityLevel
        priority = PriorityLevel.HIGH_PRIORITY
    elif ranking_score >= 80:
        from evaluation.models import PriorityLevel
        priority = PriorityLevel.STRONG
    elif ranking_score >= 70:
        from evaluation.models import PriorityLevel
        priority = PriorityLevel.REASONABLE
    elif ranking_score >= 60:
        from evaluation.models import PriorityLevel
        priority = PriorityLevel.REVIEW
    else:
        from evaluation.models import PriorityLevel
        priority = PriorityLevel.REJECT

    from evaluation.models import RecommendationStatus
    if ranking_score >= 75 and evaluation.eligibility and evaluation.eligibility.status == EligibilityStatus.ELIGIBLE and evaluation.role_match and evaluation.role_match.status in (RoleMatchStatus.EXACT_MATCH, RoleMatchStatus.RELATED_MATCH):
        recommendation = RecommendationStatus.APPLY
    elif ranking_score >= 60:
        recommendation = RecommendationStatus.REVIEW
    else:
        recommendation = RecommendationStatus.REJECT

    evaluation = evaluation.model_copy(
        update={
            "fit_score": ranking_score,
            "priority": priority,
            "recommendation": recommendation,
            "semantic_similarity": similarity,
            "ranking_version": RANKING_VERSION,
            "ranking_components": components,
            "experience_match": components["experience"],
            "preference_match": components["preference"],
            "project_match": components["technical"],
        }
    )
    return evaluation, components
