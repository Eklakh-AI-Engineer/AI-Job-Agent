# Tech Stack

## Backend
| Choice | Rationale |
|---|---|
| **Python 3.12** | Best ecosystem for AI/LLM tooling and browser automation |
| **FastAPI** | Async-native, typed, auto-generated OpenAPI docs; faster than Django for API-first services |
| **PostgreSQL + pgvector** | Relational integrity for application data, native vector similarity search for job matching without a separate vector DB |
| **Redis** | Caching, Celery broker, rate-limit counters |
| **Celery** (Temporal as a future upgrade path) | Mature, widely deployed async task queue for agent runs |
| **SQLAlchemy + Alembic** | Typed ORM with reliable migrations |

## AI / LLM
| Choice | Rationale |
|---|---|
| **Claude / GPT-class models** (pluggable) | Long-context resume/JD reasoning; provider-agnostic client layer to avoid lock-in |
| **Sentence-embedding model** | Semantic job–profile matching |
| **Reranker** | Precision pass on top-K matches before spending LLM tokens on tailoring |

## Automation
| Choice | Rationale |
|---|---|
| **Playwright** | Reliable, modern browser automation with strong async support and multi-browser coverage |

## Infrastructure
| Choice | Rationale |
|---|---|
| **Docker / Docker Compose** | Reproducible local dev, identical images across environments |
| **Kubernetes** | Production orchestration, autoscaling agent workers |
| **Terraform** | Declarative, versioned cloud infrastructure |
| **GitHub Actions** | CI/CD tightly integrated with the repository |
| **NGINX** | Reverse proxy / TLS termination |

## Observability
| Choice | Rationale |
|---|---|
| **Prometheus** | Metrics collection |
| **Grafana** | Dashboards |
| **Structured logging (JSON) + Sentry** | Error tracking and debugging across async agent workers |

## Storage
| Choice | Rationale |
|---|---|
| **PostgreSQL** | Primary relational store |
| **S3-compatible object storage** | Resume/cover-letter files, generated artifacts |
| **pgvector** | Avoids operating a separate vector database at this scale |

## Alternatives Considered
Full comparisons and decision records live in [`docs/02_Architecture/`](docs/02_Architecture/) as they are written (e.g., FastAPI vs. Django/NestJS, Celery vs. Temporal, PostgreSQL vs. MongoDB).
