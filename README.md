# AI Job Agent

> Engineering-first career operating system for job discovery, candidate↔job intelligence, document generation, and human-gated application workflows.

## Release status

The repository is in the **v1 completion and validation phase**. The implementation is substantially complete; remaining work is primarily empirical validation against real data/environments.

| Capability | Status |
|---|---|
| FastAPI `/api/v1` backend | 🟢 Implemented |
| PostgreSQL + pgvector | 🟢 Implemented |
| Redis + Celery | 🟢 Implemented |
| Candidate Knowledge Base | 🟢 Implemented / integrated |
| Greenhouse / Lever / Workday / Apify discovery | 🟢 Implemented |
| Canonical `JobPosting` pipeline | 🟢 Implemented |
| JD detail extraction | 🟢 Implemented |
| Structured JD normalization + provenance | 🟢 Implemented |
| Candidate-job deterministic evaluation | 🟢 Implemented |
| Hybrid ranking + explanations | 🟢 Implemented |
| Ranking calibration utility | 🟢 Implemented; empirical calibration pending |
| 50-query benchmark infrastructure | 🟢 Implemented; final adjudicated workbook frozen externally but not committed at the CI input path |
| Ranking metrics | 🟢 Implemented |
| Ranking regression gate | 🟠 Fail-closed gate implemented; production-authoritative baseline pending |
| Resume / cover-letter generation | 🟢 Implemented |
| PDF / DOCX artifacts | 🟢 Implemented |
| ATS analysis | 🟢 Implemented |
| Human approval gate | 🟢 Implemented |
| Mock ATS E2E | 🟢 Implemented |
| Backend true-pipeline E2E | 🟢 Implemented |
| Frontend build/type/unit CI | 🟢 Implemented |
| Frontend live integration smoke tests | 🟠 Basic live smoke passed; expanded checks exposed an intermittent PgBouncer/asyncpg health issue, fix deployed/revalidation pending |
| SSRF / upload security controls | 🟢 Implemented |
| Prometheus + structured logging | 🟢 Implemented |
| Production deployment configuration | 🟢 Implemented for Vercel + Render + Supabase topology |
| Real ATS dry-run evidence | 🟢 Two public Lever pages passed dry-run validation; no submission occurred |
| Human-verified ranking benchmark | 🟠 Adjudication complete in frozen workbook; CI input and production-job mapping still pending |
| Production deployment | 🟠 Vercel frontend/API deployed; basic health smoke passes; authenticated workflows, authoritative ranking baseline, and restore validation remain pending |

**Important:** source code being present is not treated as validation. A capability is considered validated only when its tests, failure paths, runtime evidence and documentation agree.

## Target architecture

```text
                         Vercel / Next.js
                               |
                               v
                        Render / FastAPI
                               |
             +-----------------+------------------+
             |                 |                  |
             v                 v                  v
       Supabase DB          Redis             Storage
       PostgreSQL           / Celery          S3-compatible
       + pgvector              |              artifacts
             |                 v
             |          Background workers
             |                 |
             +--------+--------+
                      |
                      v
              Job discovery / JD extraction
                      |
                      v
                Canonical JobPosting
                      |
             +--------+---------+
             |                  |
             v                  v
       Candidate KB        Retrieval/search
             |                  |
             +--------+---------+
                      v
               Hybrid ranking
                      |
             +--------+---------+
             |                  |
             v                  v
        Documents          Explanations
             |
             v
       Human approval gate
             |
             v
       ATS dry-run / submission
             |
             v
          Outcomes
             |
             v
       Evaluation + regression gate
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for implementation boundaries and [docs/deployment/VERCEL_RENDER_SUPABASE.md](docs/deployment/VERCEL_RENDER_SUPABASE.md) for production topology.

## Evaluation

The repository contains a reproducible ranking evaluation stack:

- `docs/evaluation/golden_job_ranking_v1.jsonl` — provisional 50-query benchmark;
- `scripts/evaluate_ranking.py` — metric runner;
- `scripts/validate_benchmark.py` — structural validation and SHA-256 fingerprinting;
- `scripts/ranking_regression_gate.py` — baseline/threshold enforcement;
- `backend/evaluation/calibration.py` — deterministic weight-calibration implementation;
- `docs/evaluation/benchmark_status.json` — benchmark lifecycle state.

The benchmark is **not** called golden until real jobs are human-reviewed, disagreements are adjudicated, and the dataset is frozen with a recorded hash.

## Verification

Backend:

```bash
pytest
pytest -m postgres tests/integration_pg
```

Frontend:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

Live integration:

```bash
LIVE_API_URL=https://api.example.com npm run test:live
FRONTEND_URL=https://app.example.com npm run test:live:frontend
```

The primary CI workflow also runs the true pipeline E2E, benchmark structure validation, dependency auditing, frontend build gates and the conditional ranking regression gate.

## Security boundary

- Authentication and authorization are enforced at the API layer.
- Production secrets and wildcard CORS are rejected at startup.
- Authentication endpoints are rate-limited.
- Server-side browser/HTTP URL fetches reject private/local destinations.
- External document uploads are restricted to validated PDF/DOCX artifacts.
- External application submission remains explicitly approval-gated.
- Job-board content is treated as untrusted input.
- CodeQL and dependency-review/pip-audit checks are part of the repository security workflow.

See [docs/SECURITY.md](docs/SECURITY.md).

## Deployment

### Observed live deployment (2026-10-09)

- **Vercel frontend:** `https://ai-job-agent-theta.vercel.app`
- **Vercel FastAPI API:** `https://ai-job-agent-api-mu.vercel.app`
- **Database:** the live `/health` response reported `database=healthy`.
- **Monitoring:** backend health, Prometheus metrics, and frontend shell smoke passed in [run 37879029230](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37879029230).

This proves deployment and basic health, not full production readiness. Authenticated user workflows, real persisted-job benchmark mapping, production ranking regression, and database/storage restore remain release gates.

### Documented target topology

The repository also includes a Render + managed Redis configuration for a FastAPI web service and Celery worker, with Supabase PostgreSQL/pgvector/Storage. That topology is a documented deployment option; the observed live API above is currently hosted on Vercel. Do not claim the Render worker is live without separate deployment evidence.

The repository includes `render.yaml` and deployment documentation. Production secrets must remain outside Git.

## Engineering principles

1. **Truthful scope** — distinguish implemented, integrated, validated and pending.
2. **Auditable evidence** — preserve source evidence and ranking explanations.
3. **Human control** — external submission remains approval-gated.
4. **Reproducibility** — tests, migrations, benchmarks and configuration are versioned.
5. **No fabricated candidate claims** — generated documents stay constrained by candidate evidence.
6. **Regression enforcement** — ranking changes must be measurable before they become release candidates.

## Documentation

| Document | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Current system boundaries |
| [Development](docs/DEVELOPMENT.md) | Local setup and test commands |
| [Evaluation](docs/evaluation/README.md) | Ranking benchmark and regression process |
| [Frontend live QA](docs/testing/FRONTEND_LIVE_QA.md) | Live integration checklist |
| [Deployment](docs/deployment/VERCEL_RENDER_SUPABASE.md) | Vercel/Render/Supabase topology |
| [Security](docs/SECURITY.md) | Security boundary and controls |
| [Pending implementation plan](PENDING_IMPLEMENTATION_PLAN.md) | Remaining validation work |

Historical audit and implementation-plan documents are retained under their historical paths and are not the current source of truth.

## License

MIT
