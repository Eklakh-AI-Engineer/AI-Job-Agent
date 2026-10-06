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
- Prometheus metrics, production HTTP hardening and CI release gates

## Known architectural gaps

1. The application path now uses `JobPosting` directly for evaluation and documents. The legacy `backend/jobs` model remains only for compatibility with older unit fixtures and is outside the application path.
2. Discovery now fetches each detail page before persistence; failed extraction is skipped and reported rather than persisted as a placeholder. P1.2 still owns structured-field normalization/provenance.
3. Candidate-job ranking is now a versioned hybrid scorer combining deterministic evidence signals and semantic similarity; golden-set calibration remains pending.
4. The v1 embedding contract is locked to OpenAI `text-embedding-3-small` / `1536` dimensions; incompatible configured models fail at startup and incompatible payloads fail before persistence.
5. Document rendering now produces auditable PDF/DOCX artifacts with integrity metadata.
6. Browser automation has deterministic mock-ATS coverage and a separate live dry-run validation gate.
7. A service-level true-pipeline E2E exists; browser-level frontend QA and live ATS evidence remain separate release gates.
8. CI now gates backend/frontend correctness; observability and deployment hardening are documented with remaining environment-level controls.

See [PENDING_IMPLEMENTATION_PLAN.md](../PENDING_IMPLEMENTATION_PLAN.md).