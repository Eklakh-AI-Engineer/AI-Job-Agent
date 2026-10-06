# AI Job Agent Technology Stack

## Implemented stack

| Layer | Technology |
|---|---|
| Backend | Python / FastAPI |
| Persistence | PostgreSQL / SQLAlchemy / Alembic |
| Vector search | pgvector |
| Background work | Redis / Celery |
| Retrieval | lexical, dense and hybrid components |
| Embeddings | OpenAI `text-embedding-3-small` (v1, 1536d) behind provider abstraction |
| Browser automation | Playwright |
| Testing | pytest + Node test runner |
| Frontend | Next.js 16 / React 19 / TypeScript |
| Styling | Tailwind CSS v4 |
| Metrics | Prometheus |
| Local infrastructure | Docker / Docker Compose |
| Delivery | GitHub Actions / CodeQL / container publishing |

## Present but not production-complete

- Kubernetes manifests
- Terraform configuration
- monitoring stack
- external ATS automation
- provider abstraction retained for future migrations; v1 runtime contract is 1536 dimensions

These are real repository components, but their production readiness still depends on the validation work in PENDING_IMPLEMENTATION_PLAN.md.

## Planned validation / maturity

- future embedding-model migration (requires full vector regeneration + compatibility validation)
- calibrated candidate-job ranking
- 50-100 case golden evaluation benchmark
- professional PDF/DOCX document rendering
- deterministic mock ATS
- full product E2E
- Grafana dashboards and OpenTelemetry tracing
- backup/restore and capacity validation

Architecture specifications may discuss technologies not yet implemented. Specifications are not runtime evidence.