"""
backend/evaluation/candidate_loader.py

Deterministic YAML loader and cross-file validator for Candidate KB (Phase 3C).
"""

from pathlib import Path
from typing import Union, Dict, Any, Set
import yaml

from backend.evaluation.candidate_models import (
    CandidateKB,
    CandidateProfile,
    CandidateSkills,
    CandidateClaims,
    CandidateExperience,
    CandidatePreferences,
)


def validate_candidate_kb(kb: CandidateKB) -> None:
    """
    Run deterministic cross-file referential integrity and consistency validations.

    Validates:
    - Unique IDs across skills, claims, work experience, and projects.
    - All evidence claim references resolve to known claims in claims.yaml.
    - All verified skills are backed by at least one claim, and all backing claims are verified.
    - Associated skill ID references in claims resolve to known skills.
    - Experience/project claim references resolve to known claims.
    """
    # 1. Duplicate ID validation
    seen_skills: Set[str] = set()
    for s in kb.skills.skills:
        if s.id in seen_skills:
            raise ValueError(f"Duplicate skill ID found: '{s.id}'")
        seen_skills.add(s.id)

    seen_claims: Set[str] = set()
    claim_by_id = {}
    for c in kb.claims.claims:
        if c.id in seen_claims:
            raise ValueError(f"Duplicate claim ID found: '{c.id}'")
        seen_claims.add(c.id)
        claim_by_id[c.id] = c

    seen_exp: Set[str] = set()
    for e in kb.experience.work_experience:
        if e.id in seen_exp:
            raise ValueError(f"Duplicate work experience ID found: '{e.id}'")
        seen_exp.add(e.id)

    seen_proj: Set[str] = set()
    for p in kb.experience.projects:
        if p.id in seen_proj:
            raise ValueError(f"Duplicate project ID found: '{p.id}'")
        seen_proj.add(p.id)

    # 2. Skill referential integrity and verified consistency
    for s in kb.skills.skills:
        for cid in s.evidence_claims:
            if cid not in claim_by_id:
                raise ValueError(
                    f"Skill '{s.id}' ({s.name}) references non-existent claim '{cid}'"
                )
        if s.verified:
            if not s.evidence_claims:
                raise ValueError(
                    f"Verified skill '{s.id}' ({s.name}) must have at least one supporting evidence claim"
                )
            for cid in s.evidence_claims:
                claim = claim_by_id[cid]
                if not claim.verified:
                    raise ValueError(
                        f"Verified skill '{s.id}' ({s.name}) references unverified claim '{cid}'"
                    )

    # 3. Work experience referential integrity
    for e in kb.experience.work_experience:
        for cid in e.claims:
            if cid not in claim_by_id:
                raise ValueError(
                    f"Work experience '{e.id}' references non-existent claim '{cid}'"
                )

    # 4. Project referential integrity
    for p in kb.experience.projects:
        for cid in p.claims:
            if cid not in claim_by_id:
                raise ValueError(
                    f"Project '{p.id}' references non-existent claim '{cid}'"
                )

    # 5. Claim associated skill references
    for c in kb.claims.claims:
        for sref in c.associated_skills:
            if sref.startswith("SKILL-") and sref not in seen_skills:
                raise ValueError(
                    f"Claim '{c.id}' references non-existent skill '{sref}'"
                )


def load_candidate_kb_from_dict(raw_data: Dict[str, Any]) -> CandidateKB:
    """
    Construct and validate a CandidateKB from an in-memory dictionary.
    """
    kb = CandidateKB(
        profile=CandidateProfile(**raw_data.get("profile", {})),
        skills=CandidateSkills(**raw_data.get("skills", {})),
        claims=CandidateClaims(**raw_data.get("claims", {})),
        experience=CandidateExperience(**raw_data.get("experience", {})),
        preferences=CandidatePreferences(**raw_data.get("preferences", {})),
    )
    validate_candidate_kb(kb)
    return kb


def load_candidate_kb_from_dir(directory: Union[Path, str]) -> CandidateKB:
    """
    Load, parse, and validate a CandidateKB from a directory containing:
    - profile.yaml
    - skills.yaml
    - claims.yaml
    - experience.yaml
    - preferences.yaml
    """
    dir_path = Path(directory)
    required_files = {
        "profile": dir_path / "profile.yaml",
        "skills": dir_path / "skills.yaml",
        "claims": dir_path / "claims.yaml",
        "experience": dir_path / "experience.yaml",
        "preferences": dir_path / "preferences.yaml",
    }

    for name, path in required_files.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing required Candidate KB file: {path}")

    raw_data: Dict[str, Any] = {}
    for name, path in required_files.items():
        with open(path, "r", encoding="utf-8") as f:
            try:
                content = yaml.safe_load(f)
            except yaml.YAMLError as err:
                raise ValueError(f"Malformed YAML in {path}: {err}") from err
            raw_data[name] = content or {}

    return load_candidate_kb_from_dict(raw_data)
