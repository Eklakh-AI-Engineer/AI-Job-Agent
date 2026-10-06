# AI Job Agent Technology Stack

## Implemented stack

| Layer | Technology |
|---|---|
| Backend | Python / FastAPI |
| Persistence | PostgreSQL / SQLAlchemy / Alembic |
| Vector search | pgvector |
| Background work | Redis / Celery |
| Retrieval | lexical, dense and hybrid components |
| Embeddings | provider abstraction |
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
- multiple embedding provider/model options

These are real repository components, but their production readiness still depends on the validation work in PENDING_IMPLEMENTATION_PLAN.md.

## Planned validation / maturity

- locked v1 embedding model and vector dimension
- calibrated candidate-job ranking
- 50-100 case golden evaluation benchmark
- professional PDF/DOCX document rendering
- deterministic mock ATS
- full product E2E
- Grafana dashboards and OpenTelemetry tracing
- backup/restore and capacity validation

Architecture specifications may discuss technologies not yet implemented. Specifications are not runtime evidence.