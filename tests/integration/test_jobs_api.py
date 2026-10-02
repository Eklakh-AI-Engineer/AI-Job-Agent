"""
Integration tests for the job posting endpoints.
"""


def make_job(url: str = "https://example.com/jobs/1", **overrides):
    payload = {
        "title": "AI Engineer",
        "company": "Example Corp",
        "location": "Remote",
        "job_description": "Build agentic pipelines.",
        "url": url,
        "source": "greenhouse",
    }
    payload.update(overrides)
    return payload


async def test_create_job_returns_201(api_client, auth_headers):
    response = await api_client.post(
        "/api/v1/jobs", headers=auth_headers, json=make_job()
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["url"] == "https://example.com/jobs/1"
    assert body["source"] == "greenhouse"
    # The pgvector embedding is internal and must not be exposed.
    assert "embedding" not in body


async def test_create_job_rejects_duplicate_url(api_client, auth_headers):
    first = await api_client.post("/api/v1/jobs", headers=auth_headers, json=make_job())
    assert first.status_code == 201, first.text

    second = await api_client.post("/api/v1/jobs", headers=auth_headers, json=make_job())
    assert second.status_code == 409, second.text


async def test_create_job_rejects_missing_required_field(api_client, auth_headers):
    payload = make_job()
    payload.pop("job_description")

    response = await api_client.post("/api/v1/jobs", headers=auth_headers, json=payload)
    assert response.status_code == 422, response.text


async def test_create_job_requires_authentication(api_client):
    response = await api_client.post("/api/v1/jobs", json=make_job())
    assert response.status_code == 401, response.text


async def test_list_jobs_requires_authentication(api_client):
    response = await api_client.get("/api/v1/jobs")
    assert response.status_code == 401, response.text


async def test_list_jobs_returns_paginated_envelope(api_client, auth_headers):
    for index in range(3):
        created = await api_client.post(
            "/api/v1/jobs", headers=auth_headers, json=make_job(url=f"https://e.com/{index}")
        )
        assert created.status_code == 201, created.text

    response = await api_client.get("/api/v1/jobs", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    # Newest first.
    assert body["items"][0]["url"] == "https://e.com/2"


async def test_list_jobs_supports_pagination(api_client, auth_headers):
    for index in range(4):
        await api_client.post(
            "/api/v1/jobs", headers=auth_headers, json=make_job(url=f"https://e.com/{index}")
        )

    response = await api_client.get("/api/v1/jobs?limit=2&offset=1", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 2


async def test_list_jobs_supports_filters(api_client, auth_headers):
    await api_client.post("/api/v1/jobs", headers=auth_headers, json=make_job(url="https://e.com/a"))
    await api_client.post(
        "/api/v1/jobs", headers=auth_headers, json=make_job(url="https://e.com/b", source="lever")
    )

    response = await api_client.get("/api/v1/jobs?source=lever", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["source"] == "lever"


async def test_get_job_by_id(api_client, auth_headers):
    created = await api_client.post("/api/v1/jobs", headers=auth_headers, json=make_job())
    job_id = created.json()["id"]

    response = await api_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == job_id


async def test_get_job_by_id_returns_404_for_missing(api_client, auth_headers):
    response = await api_client.get("/api/v1/jobs/999999", headers=auth_headers)
    assert response.status_code == 404, response.text
