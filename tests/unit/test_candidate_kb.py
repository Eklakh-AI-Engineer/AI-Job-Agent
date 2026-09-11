"""
tests/unit/test_candidate_kb.py

Phase 3C unit tests: Deterministic Candidate Knowledge Base loader and validator.

Verifies:
- Valid complete KB loading from synthetic fixtures
- Minimal valid KB loading
- Single source of truth: target_roles belongs to profile, not preferences
- Target role constraints (APPROVED_TARGET_ROLES)
- Duplicate ID detection across all entities
- Referential integrity across skills, claims, experience, and projects
- Verified consistency: verified skills must be backed by verified claims
- EvidenceReference safety: public, restricted, undetermined mappings
- Conservative defaults for missing disclosure
- Error handling for malformed YAML and missing files
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.evaluation.candidate_models import (
    CandidateKB,
    CandidateProfile,
    CandidatePreferences,
    APPROVED_TARGET_ROLES,
)
from backend.evaluation.candidate_loader import (
    load_candidate_kb_from_dir,
    load_candidate_kb_from_dict,
    validate_candidate_kb,
)
from backend.evaluation.models import DisclosureLevel

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "candidate"


def test_load_valid_fixture_kb():
    """
    Ensure the synthetic candidate fixture loads cleanly and passes all cross-file validations.
    """
    kb = load_candidate_kb_from_dir(FIXTURE_DIR)
    assert isinstance(kb, CandidateKB)
    assert kb.profile.candidate_id == "CAND-001"
    assert kb.profile.full_name == "Synthetic Candidate"
    assert len(kb.profile.target_roles) == 3
    assert len(kb.skills.skills) == 4
    assert len(kb.claims.claims) == 5
    assert len(kb.experience.work_experience) == 1
    assert len(kb.experience.projects) == 1


def test_minimal_valid_kb():
    """
    Minimal valid CandidateKB with required fields only.
    """
    data = {
        "profile": {
            "candidate_id": "CAND-MIN",
            "full_name": "Minimal Candidate",
            "target_roles": ["Software Engineer"],
            "education": {
                "degree": "B.S.",
                "field_of_study": "Computer Science",
            },
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    kb = load_candidate_kb_from_dict(data)
    assert kb.profile.candidate_id == "CAND-MIN"
    assert kb.profile.target_roles == ["Software Engineer"]


def test_invalid_target_role_rejected():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["Product Manager"],  # Not in approved list
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValidationError, match="Invalid target role 'Product Manager'"):
        load_candidate_kb_from_dict(data)


def test_empty_target_roles_rejected():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": [],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValidationError, match="target_roles cannot be empty"):
        load_candidate_kb_from_dict(data)


def test_target_roles_not_in_preferences():
    """
    Verify architectural rule: preferences does not duplicate target_roles.
    """
    pref = CandidatePreferences(preferred_work_modes=["remote"])
    assert not hasattr(pref, "target_roles")


def test_duplicate_skill_id_rejected():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {
            "skills": [
                {"id": "SKILL-1", "name": "Python"},
                {"id": "SKILL-1", "name": "Python 3"},
            ]
        },
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValueError, match="Duplicate skill ID found: 'SKILL-1'"):
        load_candidate_kb_from_dict(data)


def test_duplicate_claim_id_rejected():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {
            "claims": [
                {"id": "CLAIM-001", "title": "C1", "statement": "S1"},
                {"id": "CLAIM-001", "title": "C2", "statement": "S2"},
            ]
        },
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValueError, match="Duplicate claim ID found: 'CLAIM-001'"):
        load_candidate_kb_from_dict(data)


def test_duplicate_experience_id_rejected():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["Software Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {
            "work_experience": [
                {"id": "EXP-001", "role": "Dev", "company": "Co 1"},
                {"id": "EXP-001", "role": "Dev", "company": "Co 2"},
            ],
            "projects": [],
        },
        "preferences": {},
    }
    with pytest.raises(ValueError, match="Duplicate work experience ID found: 'EXP-001'"):
        load_candidate_kb_from_dict(data)


def test_duplicate_project_id_rejected():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["Software Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {
            "work_experience": [],
            "projects": [
                {"id": "PROJ-001", "title": "App 1"},
                {"id": "PROJ-001", "title": "App 2"},
            ],
        },
        "preferences": {},
    }
    with pytest.raises(ValueError, match="Duplicate project ID found: 'PROJ-001'"):
        load_candidate_kb_from_dict(data)


def test_broken_claim_reference_in_skill():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {
            "skills": [
                {
                    "id": "SKILL-1",
                    "name": "Python",
                    "verified": False,
                    "evidence_claims": ["CLAIM-999"],  # Non-existent
                }
            ]
        },
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValueError, match="references non-existent claim 'CLAIM-999'"):
        load_candidate_kb_from_dict(data)


def test_broken_claim_reference_in_experience():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["Software Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {
            "work_experience": [
                {
                    "id": "EXP-001",
                    "role": "Dev",
                    "company": "Co",
                    "claims": ["CLAIM-888"],  # Non-existent
                }
            ],
            "projects": [],
        },
        "preferences": {},
    }
    with pytest.raises(ValueError, match="references non-existent claim 'CLAIM-888'"):
        load_candidate_kb_from_dict(data)


def test_broken_claim_reference_in_project():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["Software Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {"claims": []},
        "experience": {
            "work_experience": [],
            "projects": [
                {
                    "id": "PROJ-001",
                    "title": "Proj",
                    "claims": ["CLAIM-777"],  # Non-existent
                }
            ],
        },
        "preferences": {},
    }
    with pytest.raises(ValueError, match="references non-existent claim 'CLAIM-777'"):
        load_candidate_kb_from_dict(data)


def test_broken_skill_reference_in_claim():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["Software Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {"skills": []},
        "claims": {
            "claims": [
                {
                    "id": "CLAIM-001",
                    "title": "C1",
                    "statement": "S1",
                    "associated_skills": ["SKILL-999"],  # Non-existent
                }
            ]
        },
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValueError, match="references non-existent skill 'SKILL-999'"):
        load_candidate_kb_from_dict(data)


def test_verified_skill_without_evidence_rejected():
    """
    A skill marked verified: true MUST have at least one supporting evidence claim.
    """
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {
            "skills": [
                {
                    "id": "SKILL-1",
                    "name": "Python",
                    "verified": True,
                    "evidence_claims": [],  # Empty!
                }
            ]
        },
        "claims": {"claims": []},
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(
        ValueError, match="must have at least one supporting evidence claim"
    ):
        load_candidate_kb_from_dict(data)


def test_verified_skill_backed_by_unverified_claim_rejected():
    """
    A verified skill cannot be backed solely by unverified claims.
    """
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {
            "skills": [
                {
                    "id": "SKILL-1",
                    "name": "Python",
                    "verified": True,
                    "evidence_claims": ["CLAIM-001"],
                }
            ]
        },
        "claims": {
            "claims": [
                {
                    "id": "CLAIM-001",
                    "title": "Unverified Claim",
                    "statement": "Statement",
                    "verified": False,  # Unverified!
                }
            ]
        },
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    with pytest.raises(ValueError, match="references unverified claim 'CLAIM-001'"):
        load_candidate_kb_from_dict(data)


def test_evidence_reference_public_and_restricted():
    kb = load_candidate_kb_from_dir(FIXTURE_DIR)

    # Public claim
    ref_pub = kb.create_evidence_reference("CLAIM-001")
    assert ref_pub.ref_id == "CLAIM-001"
    assert ref_pub.disclosure == DisclosureLevel.PUBLIC
    assert ref_pub.is_public_safe is True
    assert ref_pub.is_internal_only is False

    # Restricted claim (CLAIM-002)
    ref_res = kb.create_evidence_reference("CLAIM-002")
    assert ref_res.ref_id == "CLAIM-002"
    assert ref_res.disclosure == DisclosureLevel.RESTRICTED
    assert ref_res.is_public_safe is False
    assert ref_res.is_internal_only is True
    # Verify confidential text is NOT embedded
    assert "statement" not in ref_res.model_dump()
    assert "title" not in ref_res.model_dump()


def test_missing_disclosure_defaults_undetermined():
    data = {
        "profile": {
            "candidate_id": "CAND-001",
            "full_name": "Test",
            "target_roles": ["AI Engineer"],
            "education": {"degree": "B.S.", "field_of_study": "CS"},
        },
        "skills": {
            "skills": [
                {"id": "SKILL-1", "name": "Python"}  # disclosure omitted
            ]
        },
        "claims": {
            "claims": [
                {"id": "CLAIM-001", "title": "C", "statement": "S"}  # disclosure omitted
            ]
        },
        "experience": {"work_experience": [], "projects": []},
        "preferences": {},
    }
    kb = load_candidate_kb_from_dict(data)
    skill = kb.get_skill("SKILL-1")
    claim = kb.get_claim("CLAIM-001")

    assert skill.disclosure == DisclosureLevel.UNDETERMINED
    assert claim.disclosure == DisclosureLevel.UNDETERMINED

    ref = kb.create_evidence_reference("SKILL-1")
    assert ref.is_internal_only is True
    assert ref.is_public_safe is False


def test_missing_file_raises_filenotfound(tmp_path):
    # Empty directory missing profile.yaml etc.
    with pytest.raises(FileNotFoundError, match="Missing required Candidate KB file"):
        load_candidate_kb_from_dir(tmp_path)


def test_malformed_yaml_raises_value_error(tmp_path):
    for f in ["profile.yaml", "skills.yaml", "claims.yaml", "experience.yaml", "preferences.yaml"]:
        (tmp_path / f).write_text("{}", encoding="utf-8")
    # Make profile.yaml invalid YAML syntax
    (tmp_path / "profile.yaml").write_text(":\n  invalid:\n [unclosed", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed YAML"):
        load_candidate_kb_from_dir(tmp_path)
