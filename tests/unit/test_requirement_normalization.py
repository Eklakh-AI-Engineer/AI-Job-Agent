"""Regression coverage for structured job requirement normalization."""

from types import SimpleNamespace

from backend.evaluation.requirements import extract_requirements, normalize_skill_list


def _job(**overrides):
    data = dict(
        id=1,
        title="ML Engineer",
        location="Remote",
        work_mode="remote",
        required_skills=["python3", "PyTorch", "torch", "Postgres"],
        preferred_skills=["k8s", "React.js"],
        experience_requirement="2+ years",
        education_requirement="Bachelor's degree in Computer Science",
        eligibility="Graduating 2027",
        raw_source_reference={},
        job_description="A" * 200,
        posted_date="2026-10",
        closing_date="2026-12-31",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_skill_aliases_are_canonical_and_deduplicated():
    assert normalize_skill_list(["python3", "Python", "torch", "PyTorch"]) == [
        "Python",
        "PyTorch",
    ]


def test_requirements_preserve_provenance_and_validate_dates():
    result = extract_requirements(_job())
    assert result.required_skills == ["Python", "PyTorch", "PostgreSQL"]
    assert result.preferred_skills == ["Kubernetes", "React"]
    assert result.normalization_version == "requirements-v1"
    assert result.field_provenance["required_skills"] == "explicit_normalized"
    assert result.field_provenance["posted_date"] == "valid_reduced_precision"
    assert result.field_provenance["closing_date"] == "valid"
    assert result.extraction_confidence == 1.0


def test_invalid_dates_are_marked_without_inference():
    result = extract_requirements(_job(posted_date="not-a-date", closing_date="2026-99"))
    assert result.field_provenance["posted_date"] == "invalid"
    assert result.field_provenance["closing_date"] == "invalid"


def test_missing_structured_fields_are_explicitly_unknown():
    result = extract_requirements(
        _job(
            experience_requirement=None,
            education_requirement=None,
            eligibility=None,
            location=None,
            work_mode=None,
        )
    )
    assert result.field_provenance["experience_requirements"] == "unknown"
    assert result.field_provenance["education_requirements"] == "unknown"
    assert result.field_provenance["eligibility_requirements"] == "unknown"
    assert result.field_provenance["location_requirements"] == "unknown"
    assert result.field_provenance["work_mode"] == "unknown"
