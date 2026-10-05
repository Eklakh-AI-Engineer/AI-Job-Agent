# AI Job Agent

> **A backend foundation for an AI-assisted career operating system.**

AI Job Agent is an evolving platform for job discovery, candidate/job matching, application assistance, and career workflow automation. The repository currently focuses on the **backend foundation and API delivery layer**; the broader autonomous multi-agent vision remains roadmap work.

## Current status

**Current documented milestone: Phase 3 — Backend Foundation.**

| Area | Current status |
|---|---|
| FastAPI backend | Implemented |
| Versioned API routing | Implemented |
| Authentication | Implemented |
| User profile endpoints | Implemented |
| Job CRUD / ingestion foundation | Implemented |
| PostgreSQL + pgvector integration | Implemented in stack |
| Redis integration | Implemented in stack |
| Alembic migrations | Implemented |
| SQLite-backed fast tests | Implemented |
| Real-Postgres integration tests | Implemented |
| Autonomous job discovery | Roadmap |
| Semantic matching agent | Roadmap / evolving |
| Resume optimization agent | Roadmap |
| Cover-letter generation | Roadmap |
| Browser application automation | Roadmap |
| Learning / career analytics | Roadmap |
| Full production deployment | Not claimed |

The project is intentionally **not** represented as a completed 24/7 autonomous application agent.

---

## What exists today

The current backend exposes versioned API routes under `/api/v1` and includes:

- account registration and login;
- bearer-token authentication;
- caller profile access;
- job posting ingestion and listing;
- database-backed persistence;
- health checks;
- service-layer separation;
- migration support;
- local Docker Compose development.

Interactive FastAPI documentation is available at `/docs` when the local API is running.

### API examples

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/users/me
GET  /api/v1/jobs
POST /api/v1/jobs
GET  /api/v1/jobs/{id}
GET  /health
```

See the detailed contracts under [docs/10_API/](docs/10_API/).

---

## Architecture

The current implementation should be understood as:

```text
Client
  |
  v
FastAPI /api/v1
  |
  +--> Authentication / Authorization
  |
  +--> API Routers
  |
  +--> Service Layer
  |
  +--> Persistence
          |
          +--> PostgreSQL / pgvector
          +--> Redis
          +--> Alembic migrations
```

The larger target architecture adds discovery, parsing, matching, resume optimization, application assistance, tracking, and analytics around this foundation. Those components are documented as **future scope**, not current implementation.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Technology

Current repository technology includes:

- **Python**
- **FastAPI**
- **PostgreSQL + pgvector**
- **Redis**
- **SQLAlchemy**
- **Alembic**
- **Docker / Docker Compose**
- **pytest**

The repository also contains design documentation for future AI/automation components. Those planned technologies should not be interpreted as proof that every listed component is currently implemented.

See [docs/TECH_STACK.md](docs/TECH_STACK.md).

---

## Local development

Clone the repository using its actual path:

```bash
git clone https://github.com/Eklakh-AI-Engineer/AI-Job-Agent.git
cd AI-Job-Agent
cp .env.example .env
```

Start the local stack:

```bash
docker compose up -d --build
```

Run the default test suite:

```bash
pytest
```

Run the PostgreSQL integration suite when the database is available:

```bash
pytest -m postgres tests/integration_pg
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the maintained development workflow.

---

## Verification

The repository's current README records a previous verification baseline of:

- **188 fast tests**
- **13 real-Postgres integration tests**

These figures are retained as **recorded verification**, not as a claim that the suite was freshly executed during this documentation maintenance.

Run the suite locally or rely on CI before treating test counts as current evidence.

---

## Documentation

| Document | Purpose |
|---|---|
| [Documentation index](docs/README.md) | Current docs and reference map |
| [Architecture](docs/ARCHITECTURE.md) | Implemented backend boundary vs future platform |
| [Development](docs/DEVELOPMENT.md) | Setup and testing |
| [Tech stack](docs/TECH_STACK.md) | Current vs planned technology |
| [Roadmap](docs/ROADMAP.md) | Future phases and milestones |
| [Security](docs/SECURITY.md) | Security boundary and controls |
| [API reference](docs/10_API/) | Detailed endpoint contracts |
| [Deferred components](docs/deferred-components.md) | Explicitly deferred architecture |

The numbered `docs/00_*` through `docs/11_*` directories contain the project's detailed research/specification corpus. The top-level files in `docs/` provide the maintained entry points.

---

## Engineering principles

1. **Truthful scope** — implemented and planned functionality are explicitly separated.
2. **Human control** — external application submission remains approval-gated by design.
3. **Service boundaries** — routers should not absorb domain/service responsibilities.
4. **Reproducibility** — tests, migrations, and local infrastructure should be repeatable.
5. **No fabricated candidate claims** — resume/job tailoring must use the candidate's real qualifications.
6. **Incremental autonomy** — automation should be added only after its supporting contracts are implemented and tested.

---

## Security and responsibility

AI Job Agent assists with career workflows; it does not replace user judgment.

Users remain responsible for reviewing generated materials and final submissions. Automated interaction with third-party job platforms must respect their terms and applicable policies.

See [docs/SECURITY.md](docs/SECURITY.md).

---

## License

Licensed under the [MIT License](LICENSE).
