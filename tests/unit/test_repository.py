import pytest
from datetime import datetime, timezone
from backend.jobs.repository import JobRepository
from backend.jobs.models import Job

@pytest.fixture
def repo():
    return JobRepository("sqlite:///:memory:")

def make_job(id_str):
    job = Job(
        source="test",
        source_job_id=id_str,
        job_url="https://test.com",
        discovered_at=datetime.now(timezone.utc),
        title="Test"
    )
    job.id = id_str
    return job

def test_count_empty(repo):
    assert repo.count() == 0

def test_upsert_count(repo):
    repo.upsert(make_job("1"))
    assert repo.count() == 1

def test_get_by_id(repo):
    job = make_job("1")
    repo.upsert(job)
    retrieved = repo.get_by_id("1")
    assert retrieved is not None
    assert retrieved.id == "1"

def test_get_by_source_job_id(repo):
    job = make_job("1")
    repo.upsert(job)
    retrieved = repo.get_by_source_job_id("test", "1")
    assert retrieved is not None
    assert retrieved.id == "1"

def test_get_all(repo):
    repo.upsert(make_job("1"))
    repo.upsert(make_job("2"))
    assert len(repo.get_all()) == 2

def test_upsert_twice(repo):
    job = make_job("1")
    repo.upsert(job)
    repo.upsert(job)
    assert repo.count() == 1

def test_upsert_overwrite(repo):
    job1 = make_job("1")
    repo.upsert(job1)
    
    job2 = make_job("1")
    job2.title = "Updated"
    repo.upsert(job2)
    
    retrieved = repo.get_by_id("1")
    assert retrieved.title == "Updated"
    assert repo.count() == 1

def test_get_by_id_unknown(repo):
    assert repo.get_by_id("unknown") is None
