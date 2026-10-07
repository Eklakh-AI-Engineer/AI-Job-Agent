# AI Job Agent

> AI-assisted career operating system for job discovery, candidate-job intelligence, application documents, and human-gated application workflows.

## Current status

The repository is substantially beyond the original backend-foundation milestone. Project claims use four states: **Implemented**, **Integrated**, **Validated**, and **Planned**.

| Capability | Status |
|---|---|
| FastAPI /api/v1 backend | 🟢 Implemented / integrated |
| PostgreSQL + pgvector | 🟢 Implemented |
| Redis + Celery | 🟢 Implemented / integrated |
| Candidate Knowledge Base | 🟢 Implemented / integrated |
| Greenhouse / Lever / Workday / Apify discovery | 🟢 Implemented |
| Normalization / deduplication | 🟢 Implemented |
| Complete JD extraction | 🟢 Implemented / validated with extraction evidence |
| Deterministic candidate-job evaluation | 🟢 Implemented |
| Versioned hybrid candidate-job ranking | 🟢 Implemented; empirical calibration requires labelled outcomes |
| Embeddings / semantic / hybrid search | 🟢 Implemented |
| Resume / cover-letter workflow | 🟢 Implemented / artifact-tested |
| ATS analysis | 🟢 Implemented |
| Application lifecycle + audit | 🟢 Implemented |
| Playwright ATS automation | 🟢 Implemented / unit-tested |
| Controlled ATS E2E validation | 🟢 Mock E2E + real Lever dry-run validated |
| Next.js frontend | 🟢 Implemented / integrated |
| Backend product E2E | 🟢 Validated in CI; frontend live QA is separate |
| CI release gates | 🟢 Backend/frontend CI + pipeline + CodeQL + regression contract |
| Prometheus metrics | 🟢 Implemented |
| Grafana / tracing / production hardening | 🟠 Pending |

**Current source of truth for remaining work:** [PENDING_IMPLEMENTATION_PLAN.md](PENDING_IMPLEMENTATION_PLAN.md).

## Architecture

```text
Job Sources: Greenhouse / Lever / Workday / Apify
                    |
                    v
         Discovery + normalization
                    |
                    v
             JobPosting storage
                    |
          +---------+----------+
          |                    |
          v                    v
   Requirements/eval     Embeddings/search
          |                    |
          +---------+----------+
                    |
                    v
             Candidate KB
               /       \
              v         v
       Documents     Applications
       + ATS         + audit
                    |
                    v
                 Next.js
```

This describes the current implementation boundary. The core backend intelligence and controlled application path are implemented and CI-validated. Remaining evidence work is empirical ranking calibration on human-labelled jobs, frontend live integration QA, broader real-ATS evidence, and production operational hardening.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Technology

- Python, FastAPI, SQLAlchemy, PostgreSQL, pgvector
- Redis, Celery, Alembic, pytest, Playwright
- Next.js 16, React 19, TypeScript, Tailwind CSS v4
- Prometheus, Docker / Docker Compose, GitHub Actions, CodeQL

See [docs/TECH_STACK.md](docs/TECH_STACK.md).

## Local development

```bash
git clone https://github.com/Eklakh-AI-Engineer/AI-Job-Agent.git
cd AI-Job-Agent
cp .env.example .env
docker compose up -d --build
pytest
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run lint
npm run build
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Verification evidence

Current CI evidence includes the backend test suite, frontend lint/typecheck/tests/build, controlled pipeline E2E, CodeQL, and real ATS dry-run validation. Check GitHub Actions for the latest run rather than treating README numbers as immutable release evidence.

## Documentation

| Document | Purpose |
|---|---|
| [Pending implementation plan](PENDING_IMPLEMENTATION_PLAN.md) | Current remaining-work source of truth |
| [Architecture](docs/ARCHITECTURE.md) | Current implementation boundary |
| [Development](docs/DEVELOPMENT.md) | Setup and testing |
| [Tech stack](docs/TECH_STACK.md) | Implemented vs planned technology |
| [Roadmap](docs/ROADMAP.md) | Milestones and remaining evolution |
| [Security](docs/SECURITY.md) | Security and responsible automation |
| [API reference](docs/10_API/) | API contracts |

The older Revised implementation plan is retained as a historical implementation record. Specifications in the numbered docs directories are not proof of runtime implementation.

## Engineering principles

1. Truthful scope: distinguish implemented, integrated, validated and planned work.
2. Auditable evidence: preserve source and candidate evidence.
3. Human control: external submission remains approval-gated.
4. Reproducibility: tests, migrations, evaluation and configuration should be repeatable.
5. No fabricated candidate claims.
6. Incremental autonomy: automate only after supporting contracts are tested.

## License

Licensed under the MIT License.

## Evaluation boundary

The repository contains a reproducible **50-query × 5-candidate benchmark fixture** at `docs/evaluation/benchmark_job_ranking_v1.jsonl`. It is explicitly machine-generated and not human-gold. The regression gate protects the evaluation contract; it must not be presented as production ranking quality. Empirical calibration is implemented as a dependency-free sigmoid fitting module and should only be fitted against independently human-labelled jobs.
