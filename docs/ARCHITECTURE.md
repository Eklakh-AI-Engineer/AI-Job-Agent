# AI Job Agent Architecture

## Current implementation boundary

The repository now contains discovery, candidate intelligence, document, application, automation, observability and frontend layers in addition to the original API foundation.

```text
Job Sources
  -> Greenhouse / Lever / Workday / Apify
  -> discovery + normalization + deduplication
  -> JobPosting persistence
       -> requirement extraction + deterministic evaluation
       -> embedding / lexical / hybrid search
  -> Candidate Knowledge Base
       -> documents + ATS analysis
       -> application lifecycle + audit
       -> human-gated Playwright automation
  -> Next.js agent-oriented frontend
```

## Implemented responsibilities

- FastAPI /api/v1, authentication and authorization
- PostgreSQL + pgvector, SQLAlchemy and Alembic
- Redis + Celery background infrastructure
- Candidate KB persistence/versioning
- Greenhouse, Lever, Workday and Apify discovery components
- normalization, deduplication and job ingestion
- deterministic requirement extraction and candidate-job evaluation
- embedding providers and semantic/hybrid retrieval infrastructure
- resume/cover-letter generation, review state and ATS analysis
- application state, audit events and Playwright automation
- Next.js frontend with dashboard, opportunities, copilot, documents, applications, activity and profile
- Prometheus metrics and deployment scaffolding

## Known architectural gaps

1. The application path now uses `JobPosting` directly for evaluation and documents. The legacy `backend/jobs` model remains only for compatibility with older unit fixtures and is outside the application path.
2. Listing discovery can persist a placeholder description; complete detail-page JD extraction is P1.1.
3. Deterministic evaluation exists, but calibrated candidate-job ranking is still pending.
4. Embedding provider/model/dimension compatibility needs a locked v1 contract.
5. Current document rendering is text-based; professional PDF/DOCX artifacts remain pending.
6. Browser automation needs deterministic mock-ATS and controlled real-ATS validation.
7. The current E2E smoke test is an API health check, not the full product path.
8. CI, observability and production deployment still require hardening.

See [PENDING_IMPLEMENTATION_PLAN.md](../PENDING_IMPLEMENTATION_PLAN.md).