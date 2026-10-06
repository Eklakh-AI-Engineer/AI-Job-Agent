"""
backend/evaluation/evaluator.py

Phase 3C: Deterministic Candidate–Job Evaluation Engine.

Rules:
- Pure functions, no LLM calls, no network access
- All decisions based on explicit evidence from CandidateKB
- Uncertainty is explicit: UNCERTAIN when evidence insufficient
- Disclosure policy enforced: never embed restricted claim content
"""

from __future__ import annotations

import re
from typing import List, Optional, Set, Dict
from dataclasses import dataclass

from .models import (
    EvaluationResult,
    JobRequirements,
    SkillMatch,
    SkillMatchStatus,
    EligibilityResult,
    EligibilityStatus,
    RoleMatch,
    RoleMatchStatus,
    RecommendationStatus,
    PriorityLevel,
    EvidenceReference,
    DisclosureLevel,
)
from .candidate_models import CandidateKB, SkillRecord, ClaimRecord, APPROVED_TARGET_ROLES


# ---------------------------------------------------------------------------
# Skill Matching
# ---------------------------------------------------------------------------

# Canonical skill aliases for partial matching
SKILL_ALIASES: Dict[str, List[str]] = {
    "python": ["py", "python3"],
    "pytorch": ["torch", "pytorch-lightning"],
    "tensorflow": ["tf", "keras", "tf.keras"],
    "javascript": ["js", "ecmascript", "node.js", "nodejs"],
    "typescript": ["ts"],
    "machine learning": ["ml", "machine-learning"],
    "deep learning": ["dl", "deep-learning"],
    "natural language processing": ["nlp", "natural-language-processing"],
    "computer vision": ["cv", "computer-vision"],
    "aws": ["amazon web services", "amazon-web-services"],
    "gcp": ["google cloud platform", "google-cloud-platform"],
    "azure": ["microsoft azure", "microsoft-azure"],
    "kubernetes": ["k8s", "kube"],
    "docker": ["containerization", "containers"],
    "sql": ["postgresql", "postgres", "mysql", "sqlite"],
    "ci/cd": ["cicd", "continuous integration", "continuous deployment"],
    "git": ["github", "gitlab", "bitbucket"],
    "react": ["reactjs", "react.js"],
    "vue": ["vuejs", "vue.js"],
    "fastapi": ["starlette"],
    "django": [],
    "flask": [],
    "rust": ["rs"],
    "go": ["golang"],
    "java": ["spring", "spring boot"],
    "c++": ["cpp", "cplusplus"],
    "kafka": ["apache kafka"],
    "spark": ["apache spark", "pyspark"],
    "airflow": ["apache airflow"],
    "redis": [],
    "mongodb": ["mongo"],
    "elasticsearch": ["elastic search", "elastic-search"],
    "graphql": [],
    "rest": ["restful", "rest api"],
    "grpc": [],
    "microservices": ["micro-services", "microservice architecture"],
    "distributed systems": ["distributed computing"],
    "cuda": ["nvidia cuda", "gpu programming"],
    "triton": ["nvidia triton", "triton inference server"],
    "onnx": ["open neural network exchange"],
    "transformers": ["huggingface transformers", "bert", "gpt"],
    "llm": ["large language model", "large-language-model"],
    "rag": ["retrieval augmented generation", "retrieval-augmented-generation"],
    "fine-tuning": ["finetuning", "model fine-tuning"],
    "prompt engineering": ["prompt design"],
    "mlops": ["ml ops", "machine learning operations"],
    "data engineering": ["data pipelines", "etl", "elt"],
    "feature engineering": ["feature extraction"],
    "model deployment": ["model serving", "model hosting"],
    "a/b testing": ["ab testing", "experimentation"],
    "statistics": ["statistical analysis", "probability"],
    "linear algebra": ["matrix algebra"],
    "calculus": [],
    "probability": ["probabilistic modeling"],
    "optimization": ["mathematical optimization"],
    "reinforcement learning": ["rl", "deep rl", "deep reinforcement learning"],
    "generative ai": ["genai", "generative artificial intelligence"],
    "diffusion models": ["stable diffusion", "diffusion"],
    "gans": ["generative adversarial networks"],
    "vaes": ["variational autoencoders"],
    "attention mechanism": ["self-attention", "multi-head attention"],
    "transformer architecture": ["encoder-decoder", "decoder-only"],
}


def _normalize_skill(skill: str) -> str:
    """Normalize skill string for comparison."""
    return skill.lower().strip()


def _skill_matches(job_skill: str, candidate_skill: str) -> bool:
    """Check if candidate skill matches job skill (exact or alias)."""
    job_norm = _normalize_skill(job_skill)
    cand_norm = _normalize_skill(candidate_skill)
    
    if job_norm == cand_norm:
        return True
    
    # Check aliases
    for canonical, aliases in SKILL_ALIASES.items():
        if job_norm == canonical or job_norm in aliases:
            if cand_norm == canonical or cand_norm in aliases:
                return True
    
    return False


def _skill_partially_matches(job_skill: str, candidate_skill: str) -> bool:
    """Check if candidate skill is transferable/related to job skill."""
    job_norm = _normalize_skill(job_skill)
    cand_norm = _normalize_skill(candidate_skill)
    
    # Check if candidate skill is in job skill's transferable list
    for canonical, aliases in SKILL_ALIASES.items():
        if job_norm == canonical or job_norm in aliases:
            if cand_norm in aliases or any(cand_norm in a for a in aliases):
                return True
    
    # Check substring match (e.g., "python" in "python programming")
    if job_norm in cand_norm or cand_norm in job_norm:
        if len(job_norm) > 3 and len(cand_norm) > 3:  # Avoid false positives
            return True
    
    return False


def evaluate_skill_match(
    job_skill: str,
    kb: CandidateKB,
) -> SkillMatch:
    """
    Evaluate a single job skill against the candidate KB.
    
    Returns SkillMatch with status and evidence references.
    """
    job_skill_norm = _normalize_skill(job_skill)
    
    # Find matching verified skills
    verified_matches: List[EvidenceReference] = []
    partial_matches: List[EvidenceReference] = []
    unverified_matches: List[EvidenceReference] = []
    
    for skill in kb.skills.skills:
        if _skill_matches(job_skill, skill.name):
            evidence = kb.create_evidence_reference(skill.id)
            if skill.verified and skill.evidence_claims:
                # Has verified claims backing it
                verified_matches.append(evidence)
            elif skill.verified:
                # Verified skill but no explicit claim links
                verified_matches.append(evidence)
            else:
                unverified_matches.append(evidence)
        elif _skill_partially_matches(job_skill, skill.name):
            evidence = kb.create_evidence_reference(skill.id)
            partial_matches.append(evidence)
    
    # Also check claims directly for skill mentions
    for claim in kb.claims.claims:
        claim_text_lower = claim.statement.lower()
        if job_skill_norm in claim_text_lower:
            evidence = kb.create_evidence_reference(claim.id)
            if claim.verified:
                verified_matches.append(evidence)
            else:
                unverified_matches.append(evidence)
    
    # Determine status
    if verified_matches:
        return SkillMatch(
            skill=job_skill,
            status=SkillMatchStatus.VERIFIED_MATCH,
            evidence_references=verified_matches,
            rationale=f"Verified evidence found for '{job_skill}' via {len(verified_matches)} source(s)",
        )
    elif partial_matches:
        return SkillMatch(
            skill=job_skill,
            status=SkillMatchStatus.PARTIAL_MATCH,
            evidence_references=partial_matches,
            rationale=f"Transferable/partial evidence for '{job_skill}' via {len(partial_matches)} source(s)",
        )
    elif unverified_matches:
        return SkillMatch(
            skill=job_skill,
            status=SkillMatchStatus.NO_VERIFIED_EVIDENCE,
            evidence_references=unverified_matches,
            rationale=f"Skill mentioned but no verified evidence for '{job_skill}'",
        )
    else:
        return SkillMatch(
            skill=job_skill,
            status=SkillMatchStatus.UNCERTAIN,
            evidence_references=[],
            rationale=f"No evidence found for '{job_skill}' in candidate KB",
        )


# ---------------------------------------------------------------------------
# Eligibility Evaluation
# ---------------------------------------------------------------------------

def evaluate_eligibility(
    requirements: JobRequirements,
    kb: CandidateKB,
) -> EligibilityResult:
    """
    Evaluate eligibility requirements against candidate KB.
    
    Returns EligibilityResult with explicit matched/failed/uncertain lists.
    """
    matched: List[str] = []
    failed: List[str] = []
    uncertain: List[str] = []
    evidence_refs: List[EvidenceReference] = []
    
    # Work authorization
    for req in requirements.eligibility_requirements:
        req_lower = req.lower()
        
        if "citizen" in req_lower or "permanent resident" in req_lower or "authorized" in req_lower:
            # Check work authorization
            wa = kb.profile.work_authorization
            if wa.authorized_locations:
                matched.append(req)
                evidence_refs.append(
                    EvidenceReference(
                        ref_id="work_authorization",
                        disclosure=DisclosureLevel.PUBLIC
                    )
                )
            else:
                failed.append(req)
        
        elif "graduation" in req_lower or "degree" in req_lower:
            # Check education
            edu = kb.profile.education
            if edu.graduation_year:
                matched.append(req)
                evidence_refs.append(
                    EvidenceReference(
                        ref_id="education",
                        disclosure=DisclosureLevel.PUBLIC
                    )
                )
            else:
                uncertain.append(req)
        
        elif "visa" in req_lower or "sponsor" in req_lower:
            wa = kb.profile.work_authorization
            if wa.requires_visa_sponsorship:
                failed.append(req)
            else:
                matched.append(req)
                evidence_refs.append(
                    EvidenceReference(
                        ref_id="work_authorization",
                        disclosure=DisclosureLevel.PUBLIC
                    )
                )
        
        elif "security clearance" in req_lower or "clearance" in req_lower:
            # Can't evaluate from KB
            uncertain.append(req)
        
        else:
            # Unknown requirement type - uncertain
            uncertain.append(req)
    
    # Determine overall status
    if failed:
        status = EligibilityStatus.NOT_ELIGIBLE
    elif uncertain and not matched:
        status = EligibilityStatus.UNCERTAIN
    else:
        status = EligibilityStatus.ELIGIBLE
    
    rationale = ""
    if failed:
        rationale = f"Failed {len(failed)} requirement(s): {', '.join(failed)}"
    elif uncertain:
        rationale = f"Uncertain on {len(uncertain)} requirement(s); {len(matched)} met"
    else:
        rationale = f"All {len(matched)} eligibility requirement(s) met"
    
    return EligibilityResult(
        status=status,
        matched_requirements=matched,
        failed_requirements=failed,
        uncertain_requirements=uncertain,
        evidence_references=evidence_refs,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Role Matching
# ---------------------------------------------------------------------------

# Related role mappings for RELATED_MATCH
RELATED_ROLES: Dict[str, List[str]] = {
    "AI Engineer": ["ML Engineer", "Generative AI Engineer"],
    "ML Engineer": ["AI Engineer", "Data Scientist"],
    "Generative AI Engineer": ["AI Engineer", "ML Engineer"],
    "Software Engineer": ["ML Engineer", "Data Scientist"],
    "Data Scientist": ["ML Engineer", "Software Engineer"],
}


def evaluate_role_match(
    requirements: JobRequirements,
    kb: CandidateKB,
) -> RoleMatch:
    """
    Evaluate role alignment against candidate's target roles.
    """
    requested_role = requirements.role
    candidate_roles = kb.profile.target_roles
    
    if not requested_role:
        return RoleMatch(
            requested_role=None,
            matched_target_role=None,
            status=RoleMatchStatus.UNCERTAIN,
            rationale="Job role not specified in requirements",
            evidence_references=[],
        )
    
    # Check exact match
    for role in candidate_roles:
        if role.lower() == requested_role.lower():
            evidence = EvidenceReference(
                ref_id=f"target_role:{role}",
                disclosure=DisclosureLevel.PUBLIC
            )
            return RoleMatch(
                requested_role=requested_role,
                matched_target_role=role,
                status=RoleMatchStatus.EXACT_MATCH,
                rationale=f"Job role '{requested_role}' exactly matches candidate target role '{role}'",
                evidence_references=[evidence],
            )
    
    # Check related match
    for role in candidate_roles:
        related = RELATED_ROLES.get(role, [])
        for rel in related:
            if rel.lower() == requested_role.lower():
                evidence = EvidenceReference(
                    ref_id=f"target_role:{role}",
                    disclosure=DisclosureLevel.PUBLIC
                )
                return RoleMatch(
                    requested_role=requested_role,
                    matched_target_role=role,
                    status=RoleMatchStatus.RELATED_MATCH,
                    rationale=f"Job role '{requested_role}' is closely related to candidate target role '{role}'",
                    evidence_references=[evidence],
                )
    
    return RoleMatch(
        requested_role=requested_role,
        matched_target_role=None,
        status=RoleMatchStatus.NO_MATCH,
        rationale=f"Job role '{requested_role}' does not match any candidate target role: {candidate_roles}",
        evidence_references=[],
    )


# ---------------------------------------------------------------------------
def _basic_experience_score(requirements: JobRequirements, kb: CandidateKB) -> float:
    """Deterministic experience score from verified work history."""
    if not requirements.experience_requirements:
        return 50.0
    match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", requirements.experience_requirements.lower())
    if not match:
        return 50.0
    required = float(match.group(1))
    actual = sum(e.duration_months or 0 for e in kb.experience.work_experience if e.verified) / 12.0
    if actual >= required:
        return 100.0
    if actual >= required * 0.75:
        return 75.0
    if actual >= required * 0.5:
        return 50.0
    return 0.0


def _basic_preference_score(requirements: JobRequirements, kb: CandidateKB) -> float:
    """Deterministic preference score from explicit work-mode/location preferences."""
    parts = []
    prefs = kb.preferences
    if prefs.preferred_work_modes and requirements.work_mode:
        parts.append(100.0 if any(requirements.work_mode.lower() == x.lower() for x in prefs.preferred_work_modes) else 0.0)
    if prefs.preferred_locations and requirements.location_requirements:
        location = requirements.location_requirements.lower()
        parts.append(100.0 if any(x.lower() in location for x in prefs.preferred_locations) else 50.0)
    return sum(parts) / len(parts) if parts else 50.0


# Fit Score Calculation
# ---------------------------------------------------------------------------

def calculate_fit_score(
    matched_skills: List[SkillMatch],
    partial_skills: List[SkillMatch],
    missing_skills: List[SkillMatch],
    uncertain_skills: List[SkillMatch],
    eligibility: EligibilityResult,
    role_match: RoleMatch,
    kb: CandidateKB,
    requirements: Optional[JobRequirements] = None,
) -> tuple[float, PriorityLevel, RecommendationStatus]:
    """
    Calculate overall fit score (0-100) and derive priority + recommendation.
    
    Weighted components:
    - Required skills: 40%
    - Preferred skills: 15%
    - Eligibility: 20%
    - Role match: 15%
    - Evidence quality: 10%
    """
    # If not eligible, hard floor
    if eligibility.status == EligibilityStatus.NOT_ELIGIBLE:
        return 0.0, PriorityLevel.REJECT, RecommendationStatus.REJECT
    
    # Skill scoring
    total_required = len(matched_skills) + len(partial_skills) + len(missing_skills) + len(uncertain_skills)
    
    if total_required > 0:
        skill_score = (
            len(matched_skills) * 100 +
            len(partial_skills) * 50 +
            len(uncertain_skills) * 25 +
            len(missing_skills) * 0
        ) / total_required
    else:
        skill_score = 50  # Neutral if no skills specified
    
    # Eligibility score
    eligibility_score = {
        EligibilityStatus.ELIGIBLE: 100,
        EligibilityStatus.UNCERTAIN: 50,
        EligibilityStatus.NOT_ELIGIBLE: 0,
    }[eligibility.status]
    
    # Role match score
    role_score = {
        RoleMatchStatus.EXACT_MATCH: 100,
        RoleMatchStatus.RELATED_MATCH: 75,
        RoleMatchStatus.UNCERTAIN: 50,
        RoleMatchStatus.NO_MATCH: 0,
    }[role_match.status]
    
    # Evidence quality score (based on verified vs unverified)
    total_evidence = sum(len(m.evidence_references) for m in matched_skills + partial_skills + missing_skills + uncertain_skills)
    verified_evidence = sum(
        1 for m in matched_skills + partial_skills + missing_skills + uncertain_skills
        for ref in m.evidence_references
        if ref.disclosure == DisclosureLevel.PUBLIC
    )
    evidence_score = (verified_evidence / total_evidence * 100) if total_evidence > 0 else 30
    
    # Weighted fit score
    fit_score = (
        skill_score * 0.40 +
        eligibility_score * 0.20 +
        role_score * 0.15 +
        evidence_score * 0.10 +
        (_basic_experience_score(requirements, kb) if requirements else 50.0) * 0.075 +
        (_basic_preference_score(requirements, kb) if requirements else 50.0) * 0.075
    )
    
    fit_score = round(max(0, min(100, fit_score)), 1)
    
    # Derive priority
    if fit_score >= 90:
        priority = PriorityLevel.HIGH_PRIORITY
    elif fit_score >= 80:
        priority = PriorityLevel.STRONG
    elif fit_score >= 70:
        priority = PriorityLevel.REASONABLE
    elif fit_score >= 60:
        priority = PriorityLevel.REVIEW
    else:
        priority = PriorityLevel.REJECT
    
    # Derive recommendation
    if fit_score >= 75 and eligibility.status == EligibilityStatus.ELIGIBLE and role_match.status in (RoleMatchStatus.EXACT_MATCH, RoleMatchStatus.RELATED_MATCH):
        recommendation = RecommendationStatus.APPLY
    elif fit_score >= 60:
        recommendation = RecommendationStatus.REVIEW
    else:
        recommendation = RecommendationStatus.REJECT
    
    return fit_score, priority, recommendation


# ---------------------------------------------------------------------------
# Main Evaluation Function
# ---------------------------------------------------------------------------

def evaluate_candidate_against_job(
    job_requirements: JobRequirements,
    candidate_kb: CandidateKB,
) -> EvaluationResult:
    """
    Main evaluation function: candidate KB vs job requirements.
    
    Returns complete EvaluationResult with all sub-evaluations.
    """
    # 1. Evaluate required skills
    matched_skills: List[SkillMatch] = []
    partial_skills: List[SkillMatch] = []
    missing_skills: List[SkillMatch] = []
    uncertain_skills: List[SkillMatch] = []
    
    for skill in job_requirements.required_skills:
        match = evaluate_skill_match(skill, candidate_kb)
        if match.status == SkillMatchStatus.VERIFIED_MATCH:
            matched_skills.append(match)
        elif match.status == SkillMatchStatus.PARTIAL_MATCH:
            partial_skills.append(match)
        elif match.status == SkillMatchStatus.NO_VERIFIED_EVIDENCE:
            missing_skills.append(match)
        else:
            uncertain_skills.append(match)
    
    # 2. Evaluate preferred skills (bonus, not penalized)
    preferred_matched: List[SkillMatch] = []
    preferred_partial: List[SkillMatch] = []
    for skill in job_requirements.preferred_skills:
        match = evaluate_skill_match(skill, candidate_kb)
        if match.status == SkillMatchStatus.VERIFIED_MATCH:
            preferred_matched.append(match)
        elif match.status == SkillMatchStatus.PARTIAL_MATCH:
            preferred_partial.append(match)
    
    # 3. Evaluate eligibility
    eligibility = evaluate_eligibility(job_requirements, candidate_kb)
    
    # 4. Evaluate role match
    role_match = evaluate_role_match(job_requirements, candidate_kb)
    
    # 5. Calculate fit score (extract sub-scores for detailed breakdown)
    # Compute skill score
    total_required = len(matched_skills) + len(partial_skills) + len(missing_skills) + len(uncertain_skills)
    
    if total_required > 0:
        skill_score = (
            len(matched_skills) * 100 +
            len(partial_skills) * 50 +
            len(uncertain_skills) * 25 +
            len(missing_skills) * 0
        ) / total_required
    else:
        skill_score = 50
    
    # Eligibility score
    eligibility_score = {
        EligibilityStatus.ELIGIBLE: 100,
        EligibilityStatus.UNCERTAIN: 50,
        EligibilityStatus.NOT_ELIGIBLE: 0,
    }[eligibility.status]
    
    # Role match score
    role_score = {
        RoleMatchStatus.EXACT_MATCH: 100,
        RoleMatchStatus.RELATED_MATCH: 75,
        RoleMatchStatus.UNCERTAIN: 50,
        RoleMatchStatus.NO_MATCH: 0,
    }[role_match.status]
    
    # Evidence quality score
    total_evidence = sum(len(m.evidence_references) for m in matched_skills + partial_skills + missing_skills + uncertain_skills)
    verified_evidence = sum(
        1 for m in matched_skills + partial_skills + missing_skills + uncertain_skills
        for ref in m.evidence_references
        if ref.disclosure == DisclosureLevel.PUBLIC
    )
    evidence_score = (verified_evidence / total_evidence * 100) if total_evidence > 0 else 30
    
    # Weighted baseline score; the hybrid ranker later adds semantic similarity.
    experience_component = _basic_experience_score(job_requirements, candidate_kb)
    preference_component = _basic_preference_score(job_requirements, candidate_kb)
    fit_score = (
        skill_score * 0.40 +
        eligibility_score * 0.20 +
        role_score * 0.15 +
        evidence_score * 0.10 +
        experience_component * 0.075 +
        preference_component * 0.075
    )
    
    fit_score = round(max(0, min(100, fit_score)), 1)
    
    # Derive priority
    if fit_score >= 90:
        priority = PriorityLevel.HIGH_PRIORITY
    elif fit_score >= 80:
        priority = PriorityLevel.STRONG
    elif fit_score >= 70:
        priority = PriorityLevel.REASONABLE
    elif fit_score >= 60:
        priority = PriorityLevel.REVIEW
    else:
        priority = PriorityLevel.REJECT
    
    # Derive recommendation
    if fit_score >= 75 and eligibility.status == EligibilityStatus.ELIGIBLE and role_match.status in (RoleMatchStatus.EXACT_MATCH, RoleMatchStatus.RELATED_MATCH):
        recommendation = RecommendationStatus.APPLY
    elif fit_score >= 60:
        recommendation = RecommendationStatus.REVIEW
    else:
        recommendation = RecommendationStatus.REJECT
    
    # 6. Collect all evidence references
    all_evidence: List[EvidenceReference] = []
    for match in matched_skills + partial_skills + missing_skills + uncertain_skills + preferred_matched + preferred_partial:
        all_evidence.extend(match.evidence_references)
    all_evidence.extend(eligibility.evidence_references)
    all_evidence.extend(role_match.evidence_references)
    
    # Deduplicate evidence references
    seen_refs: Set[str] = set()
    unique_evidence: List[EvidenceReference] = []
    for ref in all_evidence:
        if ref.ref_id not in seen_refs:
            seen_refs.add(ref.ref_id)
            unique_evidence.append(ref)
    
    # 7. Generate narrative
    strengths = []
    gaps = []
    risks = []
    
    if matched_skills:
        strengths.append(f"Strong match on {len(matched_skills)} required skill(s): {', '.join(m.skill for m in matched_skills)}")
    if preferred_matched:
        strengths.append(f"Bonus: matches {len(preferred_matched)} preferred skill(s)")
    
    if partial_skills:
        gaps.append(f"Partial evidence for {len(partial_skills)} skill(s): {', '.join(m.skill for m in partial_skills)}")
    if missing_skills:
        gaps.append(f"Missing verified evidence for {len(missing_skills)} required skill(s): {', '.join(m.skill for m in missing_skills)}")
    if uncertain_skills:
        gaps.append(f"Cannot evaluate {len(uncertain_skills)} required skill(s): {', '.join(m.skill for m in uncertain_skills)}")
    
    if eligibility.status == EligibilityStatus.NOT_ELIGIBLE:
        risks.append(f"Eligibility failure: {', '.join(eligibility.failed_requirements)}")
    elif eligibility.status == EligibilityStatus.UNCERTAIN:
        risks.append(f"Uncertain eligibility: {', '.join(eligibility.uncertain_requirements)}")
    
    if role_match.status == RoleMatchStatus.NO_MATCH:
        risks.append(f"Role mismatch: job requires '{role_match.requested_role}' but candidate targets {candidate_kb.profile.target_roles}")
    elif role_match.status == RoleMatchStatus.UNCERTAIN:
        risks.append("Cannot determine role alignment")
    
    eligibility_issues = eligibility.failed_requirements + [f"Uncertain: {r}" for r in eligibility.uncertain_requirements]
    
    return EvaluationResult(
        job_id=job_requirements.job_id,
        eligibility=eligibility,
        fit_score=fit_score,
        priority=priority,
        recommendation=recommendation,
        role_match=role_match,
        technical_match=round(skill_score, 1),
        project_match=round(skill_score, 1),
        experience_match=round(_basic_experience_score(job_requirements, candidate_kb), 1),
        preference_match=round(_basic_preference_score(job_requirements, candidate_kb), 1),
        evidence_quality=round(evidence_score, 1),
        matched_skills=matched_skills,
        partial_skills=partial_skills,
        missing_skills=missing_skills,
        eligibility_issues=eligibility_issues,
        strengths=strengths,
        gaps=gaps,
        risks=risks,
        evidence_references=unique_evidence,
    )