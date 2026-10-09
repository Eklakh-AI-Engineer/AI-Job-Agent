# AI Job Agent

> An engineering-first job-search and application-assistance system that discovers opportunities, evaluates candidate–job fit, explains ranking decisions, prepares application documents, and keeps external submission behind explicit human approval.

**Release status: pre-v1.0 validation.** The core pipeline and major infrastructure are implemented, and CI plus selected live smoke checks have passed. The release is **not yet production-certified**: the final frozen benchmark artifact must be the exact CI input, synthetic benchmark job IDs still need verified mapping to real persisted records before production ranking can be measured, and several operational checks remain incomplete.

## Current status at a glance

| Area | Status | What the evidence supports |
|---|---|---|
| FastAPI backend and API routes | Implemented | Automated backend and true-pipeline E2E checks passed in recorded CI |
| PostgreSQL / pgvector, Redis / Celery | Implemented/configured | Runtime health probes reported a healthy database; this alone does not certify every background workflow |
| Job discovery and canonical job pipeline | Implemented | Includes normalization, provenance, deduplication and structured job data |
| Candidate–job evaluation and hybrid ranking | Implemented | Deterministic evaluation, ranking metrics and explanations are present |
| Candidate Knowledge Base | Implemented/integrated | End-to-end production validation remains part of authenticated QA |
| Resume / cover letter generation and artifacts | Implemented | PDF/DOCX generation and ATS analysis are included |
| Human approval boundary | Implemented | External application submission is intended to remain approval-gated |
| Human-reviewed ranking benchmark | Frozen and human-verified | 500 labeled candidate–job rows across 100 synthetic job groups; independent adjudication is recorded |
| Benchmark artifact consumed by CI | **Needs reconciliation** | CI's workbook hash differs from the recorded final frozen workbook hash |
| Production job mapping and ranking baseline | **Blocked** | Synthetic `JOB-*` identifiers are not yet proven to map to actual persisted jobs; existing scores are not production-authoritative |
| Regression gate | Fail-closed | Correctly blocks release until authoritative runtime-ranker results are available |
| Backend/frontend CI | Pass — recorded | Backend tests, true-pipeline E2E, frontend lint/type/test/build, security and benchmark checks passed in recorded CI |
| Live health and frontend smoke | Pass — recorded | Five consecutive database-health probes, auth-boundary checks and frontend shell checks passed |
| Real ATS dry run | Pass — recorded | Two public Lever pages passed dry-run checks; no application was submitted |
| Authenticated production workflow QA | Incomplete | Credentials for a disposable test account are not configured, so those tests were skipped |
| Alert delivery and database/storage restore | Not verified | Workflow smoke passed, but notification delivery and a restore into a separate disposable target have not been proven |
| v1.0.0 release | **Blocked** | Do not tag until the release gates below pass |

This status is evidence-based and intentionally distinguishes implemented code from validated production behavior.

## What the system does

- Discovers job postings through configured sources/connectors.
- Normalizes job descriptions into a canonical representation, preserving source provenance.
- Evaluates candidate–job compatibility using structured requirements and candidate evidence.
- Uses hybrid ranking and supplies explanations for ranking decisions.
- Supports candidate knowledge retrieval and generation of application documents.
- Produces resume/cover-letter artifacts and ATS-oriented analysis.
- Keeps external application submission behind an explicit human-approval boundary.
- Exposes evaluation tooling for ranking metrics, benchmark validation and regression checks.

## Architecture

```text
Job sources / connectors
          |
          v
 Discovery -> Normalization -> Deduplication
          |            |
          v            v
     Provenance   Canonical JobPosting
                       |
             +---------+----------+
             |                    |
             v                    v
       Candidate KB        Retrieval / search
             |                    |
             +---------+----------+
                       v
                 Hybrid ranking
                       |
             +---------+----------+
             |                    |
             v                    v
       Match explanations   Evaluation metrics
             |
             v
   Resume / cover-letter generation
             |
             v
      Human approval boundary
             |
             v
     ATS dry-run / submission
```

**Deployment shape:** Next.js frontend and FastAPI API have observed Vercel deployment aliases; monitoring checks have reported healthy database connectivity. The repository also documents a Vercel + Render + Supabase topology, including a Render/Celery option. Do not infer that every documented service is actively deployed just because configuration exists.

- Frontend: `https://ai-job-agent-theta.vercel.app`
- API: `https://ai-job-agent-api-mu.vercel.app`

See [architecture](docs/ARCHITECTURE.md) and [deployment topology](docs/deployment/VERCEL_RENDER_SUPABASE.md).

## Ranking evaluation and benchmark

The ranking evaluation stack includes:

- `docs/evaluation/golden_job_ranking_v1.jsonl` — benchmark fixture;
- `scripts/evaluate_ranking.py` — ranking metric runner;
- `scripts/validate_benchmark.py` — benchmark structure and SHA-256 validation;
- `scripts/ranking_regression_gate.py` — fail-closed baseline comparison;
- `backend/evaluation/calibration.py` — deterministic weight-calibration utility;
- `docs/evaluation/benchmark_status.json` — benchmark lifecycle/provenance state.

The gold benchmark is recorded as independently adjudicated and human-verified. Its frozen workbook SHA-256 is:

```text
ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e
```

The currently recorded CI workbook hash is `908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`, so the final artifact and CI input still need reconciliation.

The benchmark has 500 candidate–job rows, 100 synthetic job groups, and five candidates per group. **Current reference metrics are not production ranking performance.** Before enabling a production-quality claim, the team must:
1. Put the exact frozen adjudicated workbook (or a hash-verified equivalent) at the CI evaluator input and confirm the recorded SHA-256.
2. Map each synthetic job group to a real persisted/discovered job, verifying IDs and auditable job references without including candidate PII in evidence.
3. Run the actual runtime ranker on the mapped frozen benchmark.
4. Generate baseline/latest metrics with matching benchmark fingerprints and ranking versions, then run the production regression gate.

The gate intentionally fails closed while results are not marked production-authoritative. This is expected protection, not a passing quality score.

## Verification

Run the project's checks from a clean checkout.

### Backend

```bash
pytest
pytest -m postgres tests/integration_pg
```

### Frontend

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

### Live integration smoke tests

```bash
LIVE_API_URL=https://api.example.com npm run test:live
FRONTEND_URL=https://app.example.com npm run test:live:frontend
```

Use disposable credentials and test data for authenticated QA. Do not run destructive restore procedures against production. A successful configured workflow is not evidence until its run and artifact are inspected.

## Security and application safety

- API authentication and authorization protect private routes.
- Production secrets must remain in environment/secret stores, never in source control.
- Startup configuration rejects unsafe production defaults.
- Authentication endpoints are rate-limited.
- Server-side URL fetching rejects private/local destinations to reduce SSRF exposure.
- Uploaded documents are restricted to validated formats.
- Job-board content is treated as untrusted external input.
- Generated application documents should remain grounded in candidate-provided evidence.
- External application submission must stay behind explicit human approval; ATS dry-run evidence must not be represented as a submitted application.

See [security documentation](docs/SECURITY.md).

## Deployment and operational readiness

Basic deployment and health checks have passed in recorded runs, including backend health, metrics and frontend-shell checks. The real ATS dry run also passed on two public Lever pages without submitting applications.

The following still require evidence before release:

- successful authenticated QA of profile, job listing/export and candidate-KB paths using a disposable account;
- exact gold-workbook/CI hash reconciliation;
- verified persisted-job mapping and runtime-ranker baseline;
- production regression gate passing against that authoritative baseline;
- actual monitoring notification delivery;
- database **and** artifact-storage restore into a separate disposable environment, followed by row-count/migration/smoke verification.

The detailed, timestamped evidence and gate decisions live in the [release audit](docs/operations/RELEASE_AUDIT_2026-10-09.md) and [release runbook](docs/operations/RELEASE_RUNBOOK.md). Until all mandatory gates pass, **do not create the `v1.0.0` release tag**.

## Repository documentation

| Document | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | System boundaries and components |
| [Development](docs/DEVELOPMENT.md) | Local environment and development workflow |
| [Evaluation guide](docs/evaluation/README.md) | Benchmark, metrics and regression process |
| [Deployment topology](docs/deployment/VERCEL_RENDER_SUPABASE.md) | Deployment configuration and service layout |
| [Frontend live QA](docs/testing/FRONTEND_LIVE_QA.md) | Live integration checks |
| [Security](docs/SECURITY.md) | Security controls and boundaries |
| [Release runbook](docs/operations/RELEASE_RUNBOOK.md) | Release gates and sequence |
| [Release audit — 2026-10-09](docs/operations/RELEASE_AUDIT_2026-10-09.md) | Evidence-backed release status |
| [Documentation index](docs/DOCUMENTATION_INDEX.md) | Documentation navigation and source-of-truth guidance |
| [Contributing](CONTRIBUTING.md) | Development and validation expectations |
| [Changelog](CHANGELOG.md) | Release-relevant changes |
| [Pending implementation plan](PENDING_IMPLEMENTATION_PLAN.md) | Remaining work and validation tasks |

Historical audit documents are retained for provenance. Use the current release audit and runbook for release decisions.

## Engineering principles

1. **Evidence over assertion:** distinguish implementation, integration and validated behavior.
2. **Reproducibility:** version tests, migrations, benchmarks and configuration.
3. **Human control:** keep external application submission approval-gated.
4. **Auditability:** preserve benchmark hashes, source evidence and release artifacts.
5. **Candidate-data integrity:** do not fabricate qualifications or candidate achievements.
6. **Fail-closed promotion:** no production ranking certification without authoritative mapped-data metrics.

## License

MIT
