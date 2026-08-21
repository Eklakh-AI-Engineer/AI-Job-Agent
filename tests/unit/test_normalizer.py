import pytest
from backend.jobs.normalizer import normalize
from backend.jobs.models import Job

def test_normalize_title_case_whitespace():
    raw = {"title": " software engineer ", "source_id": "1", "url": "test.com"}
    job = normalize(raw, "test")
    assert job.title == "Software Engineer"

def test_normalize_company_whitespace():
    raw = {"company": " Tech Corp ", "source_id": "1", "url": "test.com"}
    job = normalize(raw, "test")
    assert job.company == "Tech Corp"

def test_normalize_url_scheme():
    raw = {"url": "test.com", "source_id": "1"}
    job = normalize(raw, "test")
    assert job.job_url == "https://test.com"

def test_normalize_valid_url_unchanged():
    raw = {"url": "http://test.com", "source_id": "1"}
    job = normalize(raw, "test")
    assert job.job_url == "http://test.com"

def test_normalize_missing_optional_fields():
    raw = {"source_id": "1", "url": "test.com"}
    job = normalize(raw, "test")
    assert job.title is None
    assert job.company is None
    assert job.location is None

def test_normalize_malformed_raw():
    job = normalize({}, "test")
    assert job.source == "test"
    assert job.source_job_id == ""
    assert job.job_url == ""
    assert job.title is None
    assert job.company is None
    assert job.location is None

def test_normalize_source_and_discovered_at():
    raw = {"source_id": "1", "url": "test.com"}
    job = normalize(raw, "test")
    assert job.source == "test"
    assert job.discovered_at is not None
