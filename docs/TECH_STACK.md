# AI Job Agent Technology Stack

## Current backend foundation

| Layer | Current technology |
|---|---|
| Language | Python |
| API | FastAPI |
| Persistence | PostgreSQL |
| Vector support | pgvector |
| Cache / infrastructure | Redis |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Testing | pytest |
| Local infrastructure | Docker / Docker Compose |

## Repository design / future platform

The specification corpus also discusses technologies for future capabilities such as:

- LLM providers;
- embeddings and reranking;
- browser automation;
- Celery/background processing;
- Kubernetes / Terraform;
- Prometheus / Grafana / Sentry.

These should be interpreted as **architecture/design targets unless the corresponding implementation is present and verified**.

## Technology policy

Prefer the existing stack while the backend foundation is being completed. New infrastructure should be justified by an implemented requirement rather than added solely because it appears in the target architecture.
