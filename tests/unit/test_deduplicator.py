import pytest
from datetime import datetime, timezone
from backend.jobs.deduplicator import Deduplicator
from backend.jobs.models import Job

def make_job(source, source_job_id, url=None, apply=None, title=None, company=None, location=None):
    return Job(
        source=source,
        source_job_id=source_job_id,
        job_url=url or f"https://test.com/{source_job_id}",
        application_url=apply,
        title=title,
        company=company,
        location=location,
        discovered_at=datetime.now(timezone.utc)
    )

def test_empty_deduplicator():
    d = Deduplicator()
    jobs = [make_job("s", "1"), make_job("s", "2")]
    assert len(d.filter(jobs)) == 2

def test_exact_duplicate():
    d = Deduplicator()
    jobs = [make_job("s", "1"), make_job("s", "1")]
    assert len(d.filter(jobs)) == 1

def test_same_url_different_source():
    d = Deduplicator()
    jobs = [
        make_job("s1", "1", url="https://test.com/job/1"),
        make_job("s2", "2", url="https://test.com/job/1/")
    ]
    assert len(d.filter(jobs)) == 1

def test_same_title_diff_company():
    d = Deduplicator()
    jobs = [
        make_job("s1", "1", title="Engineer", company="A", location="NY", url="1.com"),
        make_job("s1", "2", title="Engineer", company="B", location="NY", url="2.com")
    ]
    assert len(d.filter(jobs)) == 2

def test_same_company_diff_location():
    d = Deduplicator()
    jobs = [
        make_job("s1", "1", title="Engineer", company="A", location="NY", url="1.com"),
        make_job("s1", "2", title="Engineer", company="A", location="CA", url="2.com")
    ]
    assert len(d.filter(jobs)) == 2

def test_url_variants():
    d = Deduplicator()
    jobs = [
        make_job("s1", "1", url="https://test.com/job"),
        make_job("s2", "2", url="https://test.com/job/")
    ]
    assert len(d.filter(jobs)) == 1
