import pytest
from datetime import datetime, timezone
from backend.jobs.models import Job

def test_job_valid_all_required():
    job = Job(
        source="test",
        source_job_id="123",
        job_url="https://test.com",
        discovered_at=datetime.now(timezone.utc)
    )
    assert job.source == "test"
    assert job.source_job_id == "123"
    assert job.job_url == "https://test.com"
    assert job.id is not None
    assert isinstance(job.id, str)

def test_job_valid_all_optional_null():
    job = Job(
        source="test",
        source_job_id="123",
        job_url="https://test.com",
        discovered_at=datetime.now(timezone.utc),
        company=None,
        title=None,
        location=None,
        work_mode=None,
        application_url=None,
        description=None,
        posted_date=None,
        closing_date=None,
        experience_requirement=None,
        education_requirement=None,
        required_skills=[],
        preferred_skills=[],
        eligibility=None,
        compensation=None,
        internship_information=None,
        updated_at=None,
        raw_source_reference=None
    )
    assert job.company is None

def test_job_missing_source():
    with pytest.raises(ValueError):
        Job(source_job_id="123", job_url="https://test.com", discovered_at=datetime.now(timezone.utc))

def test_job_missing_source_job_id():
    with pytest.raises(ValueError):
        Job(source="test", job_url="https://test.com", discovered_at=datetime.now(timezone.utc))

def test_job_missing_job_url():
    with pytest.raises(ValueError):
        Job(source="test", source_job_id="123", discovered_at=datetime.now(timezone.utc))

def test_job_missing_discovered_at():
    with pytest.raises(ValueError):
        Job(source="test", source_job_id="123", job_url="https://test.com")

def test_different_jobs_different_ids():
    job1 = Job(source="test", source_job_id="123", job_url="https://test.com", discovered_at=datetime.now(timezone.utc))
    job2 = Job(source="test", source_job_id="124", job_url="https://test.com", discovered_at=datetime.now(timezone.utc))
    assert job1.id != job2.id
