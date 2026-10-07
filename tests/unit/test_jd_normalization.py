from backend.app.services.jd_normalization import (
    normalize_date,
    normalize_education,
    normalize_job_requirements,
    normalize_skill_list,
    parse_experience_range,
)


def test_skill_aliases_are_canonical_and_deduplicated():
    assert normalize_skill_list(["Python 3", "python", "PyTorch", "py torch", "K8s"]) == [
        "python", "pytorch", "kubernetes"
    ]


def test_experience_range_normalization():
    assert parse_experience_range("2-4 years")["min_years"] == 2.0
    assert parse_experience_range("2-4 years")["max_years"] == 4.0
    assert parse_experience_range("3+ years")["min_years"] == 3.0
    assert parse_experience_range("3+ years")["max_years"] is None
    assert parse_experience_range("unknown")["status"] == "unparsed"


def test_education_normalization():
    result = normalize_education("B.Tech in Computer Science")
    assert result["level"] == "bachelor"
    assert result["fields"] == ["computer science"]
    assert result["status"] == "explicit"


def test_date_validation():
    assert normalize_date("2026-10-07")["iso"] == "2026-10-07"
    assert normalize_date("2026/10/07")["status"] == "explicit"
    assert normalize_date("not-a-date")["status"] == "invalid"


def test_normalization_preserves_provenance_and_never_infers():
    result = normalize_job_requirements(
        {
            "required_skills": ["Python", "Py Torch"],
            "preferred_skills": ["K8s"],
            "experience_requirement": "2+ years",
            "education_requirement": "Bachelor's degree in Data Science",
            "posted_date": "2026-10-07",
            "closing_date": "not-a-date",
        }
    )
    assert result["required_skills"] == ["python", "pytorch"]
    assert result["preferred_skills"] == ["kubernetes"]
    assert result["normalization"]["version"] == "jd-normalization-v1"
    assert result["normalization"]["fields"]["required_skills"]["inferred"] is False
    assert result["normalization"]["fields"]["experience"]["min_years"] == 2.0
    assert result["normalization"]["fields"]["closing_date"]["status"] == "invalid"
