"""
backend/app/services/ats_service.py

Deterministic ATS (Applicant Tracking System) optimization.

This module analyses a document against a job's requirements and reports:

- keyword coverage (how many required/preferred skills appear),
- an overall ATS score,
- missing keywords the candidate legitimately possesses evidence for.

It never fabricates skills. It only surfaces keywords that already have
public candidate evidence; it will *report* missing keywords but never inject
them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

from backend.evaluation.candidate_models import CandidateKB
from backend.evaluation.models import DisclosureLevel, JobRequirements


@dataclass
class ATSAnalysis:
    """Result of an ATS keyword analysis."""

    score: float  # 0-100
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    coverage_ratio: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "coverage_ratio": round(self.coverage_ratio, 3),
            "recommendations": self.recommendations,
        }


# Words that carry no keyword value
_STOPWORDS: Set[str] = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "has", "that", "this", "from", "not", "but", "all", "can", "any", "who",
    "job", "role", "work", "team", "years", "year", "experience", "ability",
    "knowledge", "strong", "good", "plus", "etc", "using", "use", "new",
}


def _normalize(text: str) -> str:
    return text.lower()


def _tokenize(text: str) -> Set[str]:
    """Tokenize free text into meaningful lowercase tokens."""
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]{1,}", _normalize(text))
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}


def _phrase_present(phrase: str, text_lower: str) -> bool:
    """Check whether a (possibly multi-word) skill/phrase appears in text."""
    phrase_norm = _normalize(phrase).strip()
    if not phrase_norm:
        return False
    # Use word-boundary-ish match but allow substrings for things like "c++"
    if re.search(r"[^a-z0-9]", phrase_norm):
        return phrase_norm in text_lower
    return re.search(rf"\b{re.escape(phrase_norm)}\b", text_lower) is not None


def _public_claim_text(kb: CandidateKB) -> str:
    """Collect text from public claims/skills only."""
    parts: List[str] = []
    for claim in kb.claims.claims:
        if claim.disclosure == DisclosureLevel.PUBLIC:
            parts.append(claim.statement)
            parts.append(claim.title)
    for skill in kb.skills.skills:
        if skill.disclosure == DisclosureLevel.PUBLIC:
            parts.append(skill.name)
    for exp in kb.experience.work_experience:
        if exp.disclosure == DisclosureLevel.PUBLIC:
            parts.append(exp.role)
            parts.append(exp.company)
    for proj in kb.experience.projects:
        if proj.disclosure == DisclosureLevel.PUBLIC:
            parts.append(proj.title)
            parts.extend(proj.skills_used)
    return " ".join(parts)


def analyze_ats(
    document_text: str,
    requirements: JobRequirements,
    candidate_kb: CandidateKB,
) -> ATSAnalysis:
    """
    Compute an ATS analysis for ``document_text`` against job requirements.

    Scoring:
      - Required-skill coverage: 70% weight
      - Preferred-skill coverage: 30% weight

    Missing keywords that the candidate has *no* public evidence for are
    listed separately from those they could legitimately add.
    """
    doc_lower = _normalize(document_text)
    public_evidence = _normalize(_public_claim_text(candidate_kb))

    required = list(requirements.required_skills)
    preferred = list(requirements.preferred_skills)

    matched: List[str] = []
    missing: List[str] = []

    for skill in required + preferred:
        if _phrase_present(skill, doc_lower):
            matched.append(skill)
        else:
            missing.append(skill)

    # Coverage
    def coverage(skills: List[str]) -> float:
        if not skills:
            return 1.0
        present = sum(1 for s in skills if _phrase_present(s, doc_lower))
        return present / len(skills)

    req_cov = coverage(required)
    pref_cov = coverage(preferred)

    # Weighted score
    if required and preferred:
        score = (req_cov * 0.7 + pref_cov * 0.3) * 100
    elif required:
        score = req_cov * 100
    elif preferred:
        score = pref_cov * 100
    else:
        score = 100.0

    recommendations: List[str] = []
    # Missing keywords the candidate can legitimately add
    addable = [m for m in missing if _phrase_present(m, public_evidence)]
    unbacked = [m for m in missing if m not in addable]

    if addable:
        recommendations.append(
            "Consider highlighting these skills you have evidence for: "
            + ", ".join(addable[:10])
        )
    if unbacked:
        recommendations.append(
            "Skills not found in your verified profile (do not fabricate): "
            + ", ".join(unbacked[:10])
        )
    if req_cov < 0.5 and required:
        recommendations.append(
            "Required-skill coverage is below 50%; tailor your summary to the role."
        )

    total = len(required) + len(preferred)
    coverage_ratio = (len(matched) / total) if total else 1.0

    return ATSAnalysis(
        score=score,
        matched_keywords=matched,
        missing_keywords=missing,
        coverage_ratio=coverage_ratio,
        recommendations=recommendations,
    )


def extract_job_keywords(requirements: JobRequirements, max_keywords: int = 25) -> List[str]:
    """
    Extract a de-duplicated, ordered keyword list from job requirements.
    Required skills come first, then preferred skills.
    """
    seen: Set[str] = set()
    ordered: List[str] = []
    for skill in list(requirements.required_skills) + list(requirements.preferred_skills):
        key = _normalize(skill)
        if key and key not in seen:
            seen.add(key)
            ordered.append(skill)
        if len(ordered) >= max_keywords:
            break
    return ordered