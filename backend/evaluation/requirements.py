"""
backend/evaluation/requirements.py

Phase 3B: Deterministic Job → JobRequirements extraction.

Rules:
- Maps canonical Job fields into JobRequirements.
- Preserves None or empty defaults when information is unavailable.
- Never invents, hallucinates, or probabilistically infers requirements.
- The application path consumes the unified ``JobPosting`` model directly. The structural protocol keeps the pure evaluator independent of SQLAlchemy.
"""

from typing import List, Optional, Protocol, runtime_checkable
from .models import JobRequirements


@runtime_checkable
class JobLike(Protocol):
    """Minimal canonical job contract consumed by requirement extraction.

    The application path uses ``app.models.job.JobPosting`` directly. The
    protocol remains structural so the pure evaluation package stays independent
    of SQLAlchemy while legacy fixtures are migrated.
    """

    id: object
    title: Optional[str]
    location: Optional[str]
    work_mode: Optional[str]
    required_skills: List[str]
    preferred_skills: List[str]
    experience_requirement: Optional[str]
    education_requirement: Optional[str]
    eligibility: Optional[str]
    raw_source_reference: Optional[dict]

def _clean_str(val: Optional[str]) -> Optional[str]:
    """Return stripped string if non-empty, otherwise None."""
    if val is None:
        return None
    cleaned = str(val).strip()
    return cleaned if cleaned else None


def _clean_str_list(items: Optional[List[str]]) -> List[str]:
    """Return list of non-empty stripped strings."""
    if not items:
        return []
    cleaned_items: List[str] = []
    for item in items:
        if item is not None:
            c = str(item).strip()
            if c:
                cleaned_items.append(c)
    return cleaned_items


def _extract_eligibility(job: JobLike) -> List[str]:
    """
    Extract eligibility requirements only from explicit eligibility information.
    """
    eligibility_list: List[str] = []

    if job.eligibility:
        if isinstance(job.eligibility, list):
            eligibility_list.extend(_clean_str_list(job.eligibility))
        elif isinstance(job.eligibility, str):
            for line in job.eligibility.splitlines():
                parts = line.split(";") if ";" in line else [line]
                for part in parts:
                    cleaned = part.strip().lstrip("-*• ").strip()
                    if cleaned:
                        eligibility_list.append(cleaned)

    # If not present on top-level Job.eligibility, check raw_source_reference for explicit fields
    if (
        not eligibility_list
        and job.raw_source_reference
        and isinstance(job.raw_source_reference, dict)
    ):
        raw_elig = job.raw_source_reference.get(
            "eligibility_requirements"
        ) or job.raw_source_reference.get("eligibility")
        if isinstance(raw_elig, list):
            eligibility_list.extend(_clean_str_list(raw_elig))
        elif isinstance(raw_elig, str):
            for line in raw_elig.splitlines():
                parts = line.split(";") if ";" in line else [line]
                for part in parts:
                    cleaned = part.strip().lstrip("-*• ").strip()
                    if cleaned:
                        eligibility_list.append(cleaned)

    return eligibility_list


def _extract_domain_requirements(job: JobLike) -> List[str]:
    """
    Domain requirements must only be populated when deterministically derived from explicit job data.
    Never inferred or guessed from job title or description.
    """
    if job.raw_source_reference and isinstance(job.raw_source_reference, dict):
        raw_domains = (
            job.raw_source_reference.get("domain_requirements")
            or job.raw_source_reference.get("domains")
            or job.raw_source_reference.get("domain")
        )
        if isinstance(raw_domains, list):
            return _clean_str_list(raw_domains)
        elif isinstance(raw_domains, str):
            c = _clean_str(raw_domains)
            return [c] if c else []
    return []


def _extract_other_constraints(job: JobLike) -> List[str]:
    """
    Other constraints must only contain explicitly identifiable constraints.
    Never inferred.
    """
    if job.raw_source_reference and isinstance(job.raw_source_reference, dict):
        raw_constraints = job.raw_source_reference.get(
            "other_constraints"
        ) or job.raw_source_reference.get("constraints")
        if isinstance(raw_constraints, list):
            return _clean_str_list(raw_constraints)
        elif isinstance(raw_constraints, str):
            c = _clean_str(raw_constraints)
            return [c] if c else []
    return []


def _extract_seniority(job: JobLike) -> Optional[str]:
    """
    Extract seniority only if explicitly provided in structured source data.
    Never guessed or inferred from freeform title or description text.
    """
    if job.raw_source_reference and isinstance(job.raw_source_reference, dict):
        raw_seniority = job.raw_source_reference.get("seniority")
        return _clean_str(raw_seniority)
    return None


def extract_requirements(job: JobLike) -> JobRequirements:
    """
    Deterministically extract JobRequirements from a canonical Job instance.

    Mapping:
    - job.id -> job_id
    - job.title -> role
    - job.required_skills -> required_skills
    - job.preferred_skills -> preferred_skills
    - job.experience_requirement -> experience_requirements
    - job.education_requirement -> education_requirements
    - job.location -> location_requirements
    - job.work_mode -> work_mode
    - explicit domain info -> domain_requirements
    - explicit eligibility info -> eligibility_requirements
    - explicit constraints -> other_constraints
    - explicit seniority -> seniority

    Unavailable information remains None or empty list.
    """
    if job is None:
        raise TypeError("Job cannot be None")
    
    # Reject plain dicts - must be a proper Job-like object
    if isinstance(job, dict):
        raise TypeError("Expected JobPosting-like instance, got dict")
    
    if not hasattr(job, 'id') or not job.id:
        raise ValueError("Job must have a valid non-empty id")

    return JobRequirements(
        job_id=str(job.id),  # Ensure string ID
        role=_clean_str(job.title),
        seniority=_extract_seniority(job),
        domain_requirements=_extract_domain_requirements(job),
        required_skills=_clean_str_list(job.required_skills),
        preferred_skills=_clean_str_list(job.preferred_skills),
        education_requirements=_clean_str(job.education_requirement),
        experience_requirements=_clean_str(job.experience_requirement),
        eligibility_requirements=_extract_eligibility(job),
        location_requirements=_clean_str(job.location),
        work_mode=_clean_str(job.work_mode),
        other_constraints=_extract_other_constraints(job),
    )