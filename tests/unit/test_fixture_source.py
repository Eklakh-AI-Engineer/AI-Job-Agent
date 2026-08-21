import pytest
from backend.jobs.sources.fixture import FixtureSource

def test_fixture_source():
    source = FixtureSource()
    assert source.source_name == "fixture"
    
    records = source.fetch()
    assert isinstance(records, list)
    assert len(records) >= 5
    
    for record in records:
        assert isinstance(record, dict)
