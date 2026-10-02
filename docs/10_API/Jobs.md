# Jobs

> **Status:** Partially implemented — Phase 3 (storage and read/ingest API).
> Semantic matching and embeddings arrive with the Matching Agent in Phase 4.

Job postings are the canonical records produced by the discovery pipeline and
consumed by the matching and application agents.

## Endpoints

All job endpoints require a bearer token.

| Method | Path | Success | Purpose |
|---|---|---|---|
| GET | `/api/v1/jobs` | 200 | List postings, newest first |
| POST | `/api/v1/jobs` | 201 | Ingest a discovered posting |
| GET | `/api/v1/jobs/{job_id}` | 200 | Read one posting |

### `GET /api/v1/jobs`

| Query param | Type | Default | Notes |
|---|---|---|---|
| `limit` | int 1–500 | 100 | Page size |
| `offset` | int ≥ 0 | 0 | Results to skip |
| `company` | string | — | Exact-match filter |
| `source` | string | — | Exact-match filter on the origin board |

Filters combine with **AND**.

```json
{
  "items": [
    {
      "id": 1,
      "title": "AI Engineer",
      "company": "Example Corp",
      "location": "Remote",
      "job_description": "Build agentic pipelines.",
      "url": "https://example.com/jobs/1",
      "source": "greenhouse",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### `POST /api/v1/jobs`

```json
{
  "title": "AI Engineer",
  "company": "Example Corp",
  "location": "Remote",
  "job_description": "Build agentic pipelines.",
  "url": "https://example.com/jobs/1",
  "source": "greenhouse"
}
```

`title`, `company`, `job_description`, `url` and `source` are required. `url` is
unique: ingesting a duplicate returns `409 Conflict`, which is what makes the
discovery pipeline safe to re-run.

Responses: `201`, `409` on duplicate URL, `422` on validation failure,
`401` without a token.

### `GET /api/v1/jobs/{job_id}`

Responses: `200`, `404` if the id does not exist, `401` without a token.

## Notes and limitations

- **The `embedding` column is never exposed.** `job_postings.embedding` is a
  1536-dimension pgvector column used for semantic search. It is an internal
  implementation detail and is deliberately absent from every request and
  response schema.
- **Ingestion is currently open to any authenticated user.** It is exercised by
  the discovery pipeline. A dedicated ingestion scope is planned alongside the
  Discovery Agent in Phase 4.
- **`source` is free-form** today (`greenhouse`, `lever`, `fixture`, …). It will
  be constrained to a controlled vocabulary once the source adapters land.
