"""
tests/unit/test_requirements.py

Phase 3B unit tests: Deterministic Job → JobRequirements extraction.

Verifies:
- Complete job mapping
- Minimal job with optional fields None
- Whitespace handling & empty skill list filtering
- Non-invention of requirements (no inference from title/description)
- Explicit eligibility extraction & formatting
- Deterministic extraction of domain, seniority, and constraints from explicit data
- TypeError / ValueError validation on invalid inputs
- Compatibility with canonical Job and FixtureSource
"""

import pytest
from datetime import datetime, timezone
from backend.jobs.models import Job
from backend.evaluation.models import JobRequirements
from backend.evaluation.requirements import extract_requirements
from backend.jobs.sources.fixture import FixtureSource
from backend.jobs.normalizer import normalize


def test_extract_requirements_complete_job():
    job = Job(
        id="test-job-123",
        source="greenhouse",
        source_job_id="gh-456",
        company="Anthropic",
        title="Research Engineer",
        location="San Francisco, CA",
        work_mode="hybrid",
        job_url="https://anthropic.com/jobs/456",
        application_url="https://anthropic.com/apply/456",
        description="Develop frontier models.",
        experience_requirement="3+ years in ML engineering",
        education_requirement="B.S. or M.S. in Computer Science",
        required_skills=["Python", "PyTorch", "Distributed Systems"],
        preferred_skills=["CUDA", "Triton"],
        eligibility="Must be authorized to work in the US",
        compensation="$200,000 - $300,000",
        discovered_at=datetime.now(timezone.utc),
    )

    req = extract_requirements(job)

    assert isinstance(req, JobRequirements)
    assert req.job_id == "test-job-123"
    assert req.role == "Research Engineer"
    assert req.location_requirements == "San Francisco, CA"
    assert req.work_mode == "hybrid"
    assert req.experience_requirements == "3+ years in ML engineering"
    assert req.education_requirements == "B.S. or M.S. in Computer Science"
    assert req.required_skills == ["Python", "PyTorch", "Distributed Systems"]
    assert req.preferred_skills == ["CUDA", "Triton"]
    assert req.eligibility_requirements == ["Must be authorized to work in the US"]
    assert req.seniority is None
    assert req.domain_requirements == []
    assert req.other_constraints == []


def test_extract_requirements_minimal_job():
    job = Job(
        source="manual",
        source_job_id="man-001",
        job_url="https://example.com/job/1",
        discovered_at=datetime.now(timezone.utc),
    )

    req = extract_requirements(job)

    assert isinstance(req, JobRequirements)
    assert req.job_id == job.id
    assert req.role is None
    assert req.seniority is None
    assert req.domain_requirements == []
    assert req.required_skills == []
    assert req.preferred_skills == []
    assert req.education_requirements is None
    assert req.experience_requirements is None
    assert req.eligibility_requirements == []
    assert req.location_requirements is None
    assert req.work_mode is None
    assert req.other_constraints == []


def test_extract_requirements_no_invention():
    """
    Ensure the extractor NEVER guesses or infers requirements from freeform title/description.
    """
    job = Job(
        source="test",
        source_job_id="999",
        job_url="https://test.com/job/999",
        discovered_at=datetime.now(timezone.utc),
        title="Senior NLP Engineer (Computer Vision & Healthcare)",
        description="Must have 10 years experience in NLP and Ph.D in Robotics. Remote only.",
    )

    req = extract_requirements(job)

    # Role must only be the clean title string
    assert req.role == "Senior NLP Engineer (Computer Vision & Healthcare)"
    # Seniority must NOT be inferred from title
    assert req.seniority is None
    # Domain requirements must NOT be guessed from title or description keywords
    assert req.domain_requirements == []
    # Experience must NOT be parsed from description text
    assert req.experience_requirements is None
    # Education must NOT be inferred from description text
    assert req.education_requirements is None
    # Work mode must NOT be inferred from description text
    assert req.work_mode is None
    assert req.other_constraints == []


def test_extract_requirements_whitespace_and_empty_cleaning():
    job = Job(
        source="test",
        source_job_id="ws-1",
        job_url="https://test.com/job/ws",
        discovered_at=datetime.now(timezone.utc),
        title="   Software Engineer   ",
        location="   New York, NY   ",
        work_mode="   remote   ",
        experience_requirement="   5 years   ",
        education_requirement="   Bachelor's degree   ",
        required_skills=["  Python  ", "", "   ", "SQL  "],
        preferred_skills=["  AWS  ", "   "],
    )

    req = extract_requirements(job)

    assert req.role == "Software Engineer"
    assert req.location_requirements == "New York, NY"
    assert req.work_mode == "remote"
    assert req.experience_requirements == "5 years"
    assert req.education_requirements == "Bachelor's degree"
    assert req.required_skills == ["Python", "SQL"]
    assert req.preferred_skills == ["AWS"]


def test_extract_requirements_empty_strings_become_none():
    job = Job(
        source="test",
        source_job_id="empty-1",
        job_url="https://test.com/job/empty",
        discovered_at=datetime.now(timezone.utc),
        title="   ",
        location="",
        work_mode="  ",
        experience_requirement="   ",
        education_requirement="",
        eligibility="   ",
    )

    req = extract_requirements(job)

    assert req.role is None
    assert req.location_requirements is None
    assert req.work_mode is None
    assert req.experience_requirements is None
    assert req.education_requirements is None
    assert req.eligibility_requirements == []


def test_extract_requirements_eligibility_parsing():
    job = Job(
        source="test",
        source_job_id="elig-1",
        job_url="https://test.com/job/elig",
        discovered_at=datetime.now(timezone.utc),
        eligibility="US Citizen or Permanent Resident;\n* Graduation date in 2024\n- No visa sponsorship provided",
    )

    req = extract_requirements(job)

    assert req.eligibility_requirements == [
        "US Citizen or Permanent Resident",
        "Graduation date in 2024",
        "No visa sponsorship provided",
    ]


def test_extract_requirements_explicit_source_metadata():
    """
    If raw_source_reference contains explicit structured fields, they are extracted deterministically.
    """
    job = Job(
        source="structured_feed",
        source_job_id="feed-100",
        job_url="https://test.com/feed/100",
        discovered_at=datetime.now(timezone.utc),
        title="Machine Learning Specialist",
        raw_source_reference={
            "seniority": "Staff",
            "domain_requirements": ["NLP", "Information Retrieval"],
            "other_constraints": ["Must pass security clearance"],
        },
    )

    req = extract_requirements(job)

    assert req.role == "Machine Learning Specialist"
    assert req.seniority == "Staff"
    assert req.domain_requirements == ["NLP", "Information Retrieval"]
    assert req.other_constraints == ["Must pass security clearance"]


def test_extract_requirements_type_and_value_errors():
    with pytest.raises(TypeError, match="Job cannot be None"):
        extract_requirements(None)

    with pytest.raises(TypeError, match="Expected Job instance"):
        extract_requirements({"title": "Not a job"})

    invalid_job = Job(
        id="temp",
        source="test",
        source_job_id="1",
        job_url="https://test.com",
        discovered_at=datetime.now(timezone.utc),
    )
    invalid_job.id = ""

    with pytest.raises(ValueError, match="Job must have a valid non-empty id"):
        extract_requirements(invalid_job)


def test_extract_requirements_with_fixture_source():
    """
    Ensure all normalized jobs from the existing FixtureSource extract cleanly into JobRequirements.
    """
    source = FixtureSource()
    raw_records = source.fetch()

    jobs = [normalize(r, source.source_name) for r in raw_records]

    for job in jobs:
        req = extract_requirements(job)
        assert isinstance(req, JobRequirements)
        assert req.job_id == job.id
        if job.title:
            assert req.role == job.title.strip()
        if job.location:
            assert req.location_requirements == job.location.strip()
        if job.work_mode:
            assert req.work_mode == job.work_mode.strip()
