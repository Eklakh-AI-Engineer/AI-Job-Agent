"""
Unit tests for backend/app/services/job_service.py
"""

import pytest

from app.schemas.job import JobPostingCreate
from app.services.errors import JobAlreadyExistsError, JobNotFoundError
from app.services.job_service import (
    count_jobs,
    create_job,
    get_job_by_id,
    get_job_by_url,
    get_job_or_raise,
    list_jobs,
)


def make_payload(url: str = "https://example.com/jobs/1", **overrides):
    data = {
        "title": "AI Engineer",
        "company": "Example Corp",
        "location": "Remote",
        "job_description": "Build agentic pipelines.",
        "url": url,
        "source": "greenhouse",
    }
    data.update(overrides)
    return JobPostingCreate(**data)


async def test_create_job_persists_posting(db_session):
    job = await create_job(db_session, make_payload())

    assert job.id is not None
    assert job.title == "AI Engineer"
    assert job.source == "greenhouse"
    assert await count_jobs(db_session) == 1


async def test_create_job_rejects_duplicate_url(db_session):
    await create_job(db_session, make_payload())
    with pytest.raises(JobAlreadyExistsError):
        await create_job(db_session, make_payload())


async def test_get_job_by_url_finds_posting(db_session):
    await create_job(db_session, make_payload())
    found = await get_job_by_url(db_session, "https://example.com/jobs/1")
    assert found is not None


async def test_get_job_by_id_returns_none_when_missing(db_session):
    assert await get_job_by_id(db_session, 999) is None


async def test_list_jobs_returns_newest_first(db_session):
    for index in range(3):
        await create_job(db_session, make_payload(url=f"https://example.com/jobs/{index}"))

    jobs = await list_jobs(db_session)
    assert [job.url for job in jobs] == [
        "https://example.com/jobs/2",
        "https://example.com/jobs/1",
        "https://example.com/jobs/0",
    ]


async def test_list_jobs_respects_limit_and_offset(db_session):
    for index in range(5):
        await create_job(db_session, make_payload(url=f"https://example.com/jobs/{index}"))

    page = await list_jobs(db_session, limit=2, offset=1)
    assert len(page) == 2


async def test_list_jobs_filters_by_source_and_company(db_session):
    await create_job(db_session, make_payload(url="https://example.com/a"))
    await create_job(db_session, make_payload(url="https://example.com/b", source="lever"))
    await create_job(db_session, make_payload(url="https://example.com/c", company="Other Inc"))

    # 'a' and 'c' are greenhouse; 'b' is lever.
    assert len(await list_jobs(db_session, source="greenhouse")) == 2
    assert len(await list_jobs(db_session, company="Other Inc")) == 1
    # Filters combine with AND, not OR.
    assert len(await list_jobs(db_session, company="Other Inc", source="lever")) == 0
    assert len(await list_jobs(db_session, company="Example Corp", source="lever")) == 1


async def test_list_jobs_clamps_non_positive_limit_to_default(db_session):
    await create_job(db_session, make_payload())
    # A zero or negative limit must not silently return nothing.
    assert len(await list_jobs(db_session, limit=0)) == 1


async def test_get_job_or_raise_returns_posting(db_session):
    created = await create_job(db_session, make_payload())
    assert (await get_job_or_raise(db_session, created.id)).id == created.id


async def test_get_job_or_raise_raises_when_missing(db_session):
    with pytest.raises(JobNotFoundError):
        await get_job_or_raise(db_session, 404)
