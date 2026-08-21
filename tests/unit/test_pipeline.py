import pytest
from backend.jobs.sources.fixture import FixtureSource
from backend.jobs.normalizer import normalize
from backend.jobs.deduplicator import Deduplicator
from backend.jobs.repository import JobRepository

def test_full_pipeline():
    source = FixtureSource()
    raw_records = source.fetch()
    
    jobs = [normalize(r, source.source_name) for r in raw_records]
    
    dedup = Deduplicator()
    kept_jobs = dedup.filter(jobs)
    
    repo = JobRepository("sqlite:///:memory:")
    for job in kept_jobs:
        repo.upsert(job)
        
    assert repo.count() > 0
    assert repo.count() < len(raw_records)
    
    saved_jobs = repo.get_all()
    for job in saved_jobs:
        assert job.source == source.source_name
        assert job.id is not None
        assert job.id != ""
