"""Jobs flow exercised against a real Postgres database."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.postgres


async def test_ingest_then_list_then_read(api_client, auth_headers):
    body = {
        "title": "Senior Platform Engineer",
        "company": "Acme Co",
        "location": "Remote",
        "job_description": "Build internal tooling with Python and Postgres.",
        "url": "https://jobs.acme.example/senior-platform-engineer",
        "source": "greenhouse",
    }
    ingest = await api_client.post("/api/v1/jobs", json=body, headers=auth_headers)
    assert ingest.status_code == 201
    job_id = ingest.json()["id"]

    listing = await api_client.get("/api/v1/jobs", headers=auth_headers)
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] >= 1
    assert any(item["id"] == job_id for item in body["items"])

    detail = await api_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["company"] == "Acme Co"


async def test_duplicate_url_returns_409(api_client, auth_headers):
    body = {
        "title": "SWE",
        "company": "Beta Inc",
        "job_description": "Backend role.",
        "url": "https://jobs.beta.example/swe",
        "source": "lever",
    }
    first = await api_client.post("/api/v1/jobs", json=body, headers=auth_headers)
    assert first.status_code == 201

    second = await api_client.post("/api/v1/jobs", json=body, headers=auth_headers)
    assert second.status_code == 409


async def test_list_filtered_by_company_and_source(api_client, auth_headers):
    for entry in [
        ("Greenhouse Co", "greenhouse", "https://jobs.gh.example/1"),
        ("Greenhouse Co", "greenhouse", "https://jobs.gh.example/2"),
        ("Lever Co", "lever", "https://jobs.lever.example/1"),
    ]:
        company, source, url = entry
        await api_client.post(
            "/api/v1/jobs",
            json={
                "title": "Engineer",
                "company": company,
                "job_description": "Generic role.",
                "url": url,
                "source": source,
            },
            headers=auth_headers,
        )

    by_source = await api_client.get(
        "/api/v1/jobs", params={"source": "greenhouse"}, headers=auth_headers
    )
    assert by_source.status_code == 200
    assert all(item["source"] == "greenhouse" for item in by_source.json()["items"])

    by_company = await api_client.get(
        "/api/v1/jobs", params={"company": "Lever Co"}, headers=auth_headers
    )
    assert by_company.status_code == 200
    assert all(item["company"] == "Lever Co" for item in by_company.json()["items"])
    assert len(by_company.json()["items"]) == 1
