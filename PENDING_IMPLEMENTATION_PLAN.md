# Pending Implementation Plan — AI Job Agent

**Last updated:** 2026-10-06  
**Repository:** `Eklakh-AI-Engineer/AI-Job-Agent`  
**Branch:** `main`  
**Purpose:** Single source of truth for work that is still required to move AI Job Agent from a feature-rich implementation to a validated, reproducible v1 release.

---

## 1. Scope and status rules

This document intentionally lists **only remaining work**. Completed implementation is not repeated as pending.

### Status levels

| Status | Meaning |
|---|---|
| 🔴 BLOCKING | Must be completed before calling the system end-to-end validated |
| 🟠 HIGH | Important for a credible v1 / portfolio release |
| 🟡 MEDIUM | Valuable hardening or product maturity |
| 🟢 OPTIONAL | Post-v1 enhancement |

### Completion rule

A feature is not considered complete merely because source code exists.

A capability becomes **validated** only when:

1. the implementation exists;
2. its contracts are tested;
3. the happy path is exercised end-to-end;
4. failure paths are tested where applicable;
5. measurable evidence is recorded;
6. documentation matches the actual behavior.

---

# 2. Current baseline

The repository already contains substantial implementation across:

- FastAPI backend and versioned API;
- PostgreSQL + pgvector;
- Redis + Celery;
- candidate KB persistence/versioning;
- deterministic candidate/job evaluation;
- embedding providers and semantic/hybrid search;
- Greenhouse, Lever, Workday and Apify discovery components;
- resume and cover-letter generation services;
- ATS analysis;
- application state/audit workflow;
- Playwright-based browser automation with dry-run and approval gates;
- Next.js frontend;
- agent-oriented dashboard, opportunities, copilot, documents, activity and profile experiences;
- Prometheus metrics;
- Kubernetes manifests;
- CodeQL and Docker publishing workflows.

The frontend is **not a pending rebuild item**. The frontend source is now directly present under `frontend/` in this repository and should be preserved while its integration is validated.

---

# 3. Critical path to v1

The minimum dependency order is:

```text
Repository correctness
        ↓
Real JD extraction
        ↓
Canonical structured JobPosting
        ↓
Candidate ↔ Job ranking
        ↓
Golden evaluation set + metrics
        ↓
Professional document artifacts
        ↓
Application E2E validation
        ↓
Backend + frontend CI
        ↓
Production hardening
        ↓
Release evidence + v1
```

Do not optimize deployment infrastructure before the core intelligence path has measurable validation.

---

# 4. Phase P0 — Repository and implementation correctness 🔴

## P0.1 Remove generated repository noise

- [x] Remove `tree_output.txt` (~4 MB generated tree dump).
- [x] Confirm generated Celery/runtime artifacts are ignored.
- [x] Search repository tree for generated caches/local runtime artifacts; known runtime patterns are covered by `.gitignore`.
- [ ] Keep source documentation and design artifacts only when they provide reproducible engineering value.

**Acceptance:** repository contains source, tests, configuration and useful documentation—not generated local runtime output.

---

## P0.2 Reconcile documentation with implementation

The root README currently describes an earlier backend-foundation milestone and understates the implementation now present in the repository.

- [x] Rewrite root README current-status section.
- [x] Clearly distinguish:
  - implemented;
  - integrated;
  - validated;
  - planned.
- [x] Update architecture diagram to reflect the actual implementation boundary.
- [x] Update roadmap so completed implementation is separated from remaining validation work.
- [x] Link this file as the canonical pending-work tracker.
- [x] Preserve historical implementation plans as historical records rather than using them as current status.

**Acceptance:** a reviewer reading only `README.md` can understand what works today and what remains without inspecting source code.

---

## P0.3 Establish one canonical job pipeline

- [x] Define `JobPosting` as the canonical persisted job representation.
- [x] Evaluation and document generation consume canonical `JobPosting` objects directly.
- [x] Keep the legacy `backend/jobs` model only for compatibility with older unit fixtures.
- [x] Remove the legacy adapter from the active application path.
- [x] Document the compatibility boundary in the architecture specification.

**Acceptance:** the active discovery → normalization → persistence → evaluation → search path uses `JobPosting` as the canonical representation.

---

## P0.4 Fix and lock the embedding contract

The system supports multiple embedding providers/dimensions while the persisted vector schema must have a compatible dimensionality.

- [x] Choose the v1 production contract: OpenAI `text-embedding-3-small`, 1536 dimensions.
- [x] Keep the database vector dimension at `VECTOR(1536)`.
- [x] Validate configured provider/model/dimension compatibility at application startup.
- [x] Validate generated payload dimensions before persistence and search.
- [x] Validate direct database writes through `update_job_embedding`.
- [x] Cover backfill/regeneration through the same provider contract.
- [x] Define model-change procedure: regenerate all stored vectors before changing the schema/index contract; do not mix dimensions in one index.
- [x] Preserve model and dimension in embedding task results/metrics for reproducibility.

**Acceptance:** no provider can silently write vectors incompatible with the configured database schema.

---

# 5. Phase P1 — Real job intelligence 🔴

## P1.1 Complete job-detail / JD extraction

- [x] Fetch the canonical detail page for every discovered listing before persistence.
- [x] Extract the actual visible job description/body with source-aware selectors plus a conservative DOM fallback.
- [x] Use the detail URL as the application URL when the source does not provide a separate one.
- [x] Preserve raw source evidence/reference and extraction metadata.
- [x] Record extraction method, timestamp, selector, description length and failure reason.
- [x] Never persist `Pending extraction...` or another fabricated placeholder.
- [x] Skip failed detail extractions rather than ingesting incomplete records.
- [x] Add unit coverage for normalization and extraction evidence metadata.

Remaining structured-field normalization is intentionally handled by P1.2 so explicit source values can be distinguished from inferred values.

**Acceptance:** a discovered job progresses from listing → verified detail-page JD → canonical `JobPosting`, with failed extraction visible in task errors rather than silently persisted.

---

## P1.2 Normalize and validate extracted requirements

- [ ] Normalize skill aliases into canonical skills.
- [ ] Preserve original wording for evidence.
- [ ] Distinguish explicit requirements from inferred/uncertain information.
- [ ] Validate dates, experience ranges and education fields.
- [ ] Add extraction confidence/status metadata where appropriate.
- [ ] Add regression fixtures for malformed and incomplete JDs.

**Acceptance:** evaluator/search receives structured, provenance-aware requirements rather than raw scraper output.

---

# 6. Phase P2 — Candidate ↔ job matching 🔴

Semantic search exists, but search similarity alone is not the same as candidate-job ranking.

## P2.1 Build the ranking pipeline

Implemented as `backend/evaluation/hybrid_ranker.py`.

- [x] Explicit feature set: semantic, technical, role, experience, education, preference, evidence.
- [x] Versioned deterministic weights in `RANKING_WEIGHTS`.
- [x] Combine lexical/evidence-based evaluation with candidate↔job semantic similarity.
- [x] Apply hard eligibility rejection before final ranking.
- [x] Produce stable 0–100 ranking output.
- [x] Return explainable component scores and ranking version.
- [x] Preserve matched, partial and missing skill breakdowns from the deterministic evaluator.
- [x] Integrate the ranker into the evaluation service/API.

**Acceptance:** given the same candidate KB, job, embedding model and ranking configuration, ranking is deterministic and explainable.

---

## P2.2 Calibrate current evaluation scoring

- [x] Replace placeholder preference/experience scoring with measurable features.
- [x] Calculate experience fit from verified work-history duration against explicit years requirements.
- [x] Calculate preference fit from explicit work-mode/location preferences.
- [x] Document and version every hybrid-ranking weight.
- [x] Add regression tests for ranking primitives.
- [x] Keep hard eligibility rejection separate from soft ranking.

**Acceptance:** no production ranking component is an unexplained constant.

---

# 7. Phase P3 — Evaluation system 🔴

## P3.1 Create the golden evaluation dataset

A 50-query × 5-candidate **provisional** benchmark now exists at `docs/evaluation/golden_job_ranking_v1.jsonl`. It is deliberately not marked complete because the repository does not yet contain a sufficiently large real persisted corpus and the cases are not human-verified. See `docs/evaluation/README.md` for the promotion procedure.

Target:

- [ ] 50–100 representative jobs/queries.
- [ ] Gold relevance labels.
- [ ] Gold matched skills.
- [ ] Gold missing skills.
- [ ] Gold eligibility outcomes.
- [ ] Gold preferred-job ordering where possible.
- [ ] Human rationale/evidence references.

Include difficult cases:

- strong keyword overlap but poor actual fit;
- semantically similar but ineligible roles;
- missing mandatory requirements;
- related-role matches;
- noisy/incomplete JDs;
- preference conflicts.

---

## P3.2 Define ranking metrics

- [x] Precision@K.
- [x] Recall@K.
- [x] nDCG@K.
- [x] MRR where applicable.
- [x] Binary precision/recall/F1 utilities.
- [x] Macro aggregation across query groups.
- [x] Reproducible runner in `scripts/evaluate_ranking.py`.
- [x] Metric definitions documented in `docs/evaluation/METRICS.md`.

**Acceptance:** the benchmark can be scored reproducibly from a frozen gold mapping and an ordered prediction file.

---

## P3.3 Add regression evaluation

- [ ] Create a reproducible evaluation command.
- [ ] Store dataset version.
- [ ] Store model/config version.
- [ ] Store metric output.
- [ ] Fail CI when critical metrics regress beyond defined thresholds.
- [ ] Publish evaluation results in `docs/evaluation/`.

**Acceptance:** matching improvements can be measured instead of judged only by screenshots or manual inspection.

---

# 8. Phase P4 — Document intelligence 🔴

## P4.1 Generate real professional artifacts

The document pipeline must produce uploadable resume/cover-letter artifacts rather than relying on plain-text output.

Implement:

- [ ] PDF resume generation.
- [ ] DOCX resume generation.
- [ ] PDF cover-letter generation.
- [ ] DOCX cover-letter generation.
- [ ] Stable filenames and metadata.
- [ ] Versioned artifacts.
- [ ] Artifact integrity checks.
- [ ] Storage abstraction for local/S3.
- [ ] Download/preview API contract.

---

## P4.2 Evidence and ATS validation

- [ ] Every generated claim maps to candidate evidence.
- [ ] Track claim IDs in document metadata.
- [ ] Run ATS analysis against the generated artifact.
- [ ] Verify required keywords are represented without fabrication.
- [ ] Add document regression tests.
- [ ] Add a human-review checklist.

**Acceptance:** an approved document is a real PDF/DOCX artifact suitable for application upload and auditable back to candidate evidence.

---

# 9. Phase P5 — Application automation validation 🔴

The browser automation implementation exists. The remaining requirement is proving that it works reliably against controlled targets.

## P5.1 Mock ATS test harness

Create deterministic local/mock ATS pages for:

- [ ] Greenhouse-like form.
- [ ] Lever-like form.
- [ ] Workday-like form.
- [ ] File upload.
- [ ] Required fields.
- [ ] Optional fields.
- [ ] Validation errors.
- [ ] Successful submission.
- [ ] Duplicate/replay behavior.

---

## P5.2 Real supported-ATS validation

For permitted test environments:

- [ ] Maintain a small ATS compatibility matrix.
- [ ] Test dry-run first.
- [ ] Verify selector configuration.
- [ ] Verify resume/cover-letter upload.
- [ ] Verify evidence screenshots.
- [ ] Verify failure recovery.
- [ ] Verify idempotency.
- [ ] Verify approval gate.
- [ ] Never bypass robots.txt, rate limits, platform rules or human approval.

**Acceptance:** application automation is labelled with the exact ATS flows actually validated, not broadly claimed as universally reliable.

---

# 10. Phase P6 — End-to-end product path 🔴

Replace the current placeholder-level smoke test with a real deterministic pipeline test.

Target:

```text
Seed candidate KB
       ↓
Seed/discover job
       ↓
Extract JD
       ↓
Normalize
       ↓
Evaluate
       ↓
Rank
       ↓
Generate resume
       ↓
Generate cover letter
       ↓
Approve
       ↓
Dry-run application
       ↓
Mock ATS submission
       ↓
Audit event
```

- [ ] Build one deterministic E2E fixture.
- [ ] Verify database state transitions.
- [ ] Verify generated artifacts.
- [ ] Verify audit events.
- [ ] Verify frontend-visible API state.
- [ ] Verify failure/rollback behavior.
- [ ] Run this test in CI.

**Acceptance:** one command proves the core product loop works from discovery/input to application audit.

---

# 11. Phase P7 — CI and reproducibility 🟠

Current GitHub automation should be expanded beyond CodeQL/Docker publishing.

Create a standard CI workflow that verifies:

- [ ] Python dependency installation.
- [ ] Unit tests.
- [ ] Integration tests where services are available.
- [ ] Database migrations.
- [ ] Frontend dependency installation.
- [ ] Frontend tests.
- [ ] TypeScript compilation.
- [ ] Next.js production build.
- [ ] Lint.
- [ ] E2E smoke test.
- [ ] Evaluation regression where practical.

Add caching and service containers where appropriate.

**Acceptance:** a fresh GitHub commit produces machine-verifiable backend + frontend health signals.

---

# 12. Phase P8 — Frontend integration validation 🟠

The frontend implementation is already present and should not be rebuilt.

Remaining work:

- [ ] Verify every frontend API call maps to a live backend endpoint.
- [ ] Test authentication expiry/401 behavior.
- [ ] Test empty/loading/error states.
- [ ] Test candidate KB save/load round trip.
- [ ] Test evaluation display against real API responses.
- [ ] Test document generation/approval workflow.
- [ ] Test application dry-run and approval gates.
- [ ] Test responsive behavior on the primary supported viewport range.
- [ ] Record frontend build evidence in CI.

**Acceptance:** frontend is not merely visually complete; its critical workflows are backed by real API behavior.

---

# 13. Phase P9 — Observability and production hardening 🟠

## P9.1 Observability

- [ ] Add Grafana dashboards for:
  - API latency/error rate;
  - discovery throughput;
  - duplicate rate;
  - embedding failures;
  - evaluation throughput;
  - application success/failure;
  - Celery queue/task health.
- [ ] Add distributed tracing with OpenTelemetry.
- [ ] Correlate request/task/application IDs.

## P9.2 Reliability

- [ ] Database backup strategy.
- [ ] Restore procedure.
- [ ] RPO/RTO targets.
- [ ] Load test baseline.
- [ ] Capacity assumptions.
- [ ] Alert thresholds.
- [ ] Celery failure/retry monitoring.

## P9.3 Kubernetes hardening

Existing manifests should be hardened rather than treated as proof of production readiness.

- [ ] Replace placeholder image references.
- [ ] Replace example hostnames.
- [ ] Add HPA.
- [ ] Add PodDisruptionBudget.
- [ ] Add NetworkPolicies.
- [ ] Add readiness/liveness probes where missing.
- [ ] Add resource requests/limits.
- [ ] Use external/sealed secrets.
- [ ] Add frontend deployment/ingress only if production deployment is actually targeted.

---

# 14. Phase P10 — Security and responsible automation 🟠

- [ ] Review all secret/config paths.
- [ ] Confirm no credentials or tokens are committed.
- [ ] Run dependency vulnerability scanning.
- [ ] Review SSRF exposure in URL-fetching/discovery components.
- [ ] Review arbitrary file upload/document handling.
- [ ] Review browser automation domain restrictions.
- [ ] Verify authentication and authorization on every sensitive API.
- [ ] Verify rate limits on expensive endpoints.
- [ ] Verify application automation remains approval-gated.
- [ ] Document third-party platform/ATS usage constraints.

---

# 15. Phase P11 — Analytics and learning loop 🟡

Once applications are actually being tracked, capture outcomes:

```text
Recommendation
      ↓
Application
      ↓
Interview / rejection / offer
      ↓
Outcome data
      ↓
Ranking analysis
      ↓
Future calibration
```

Implement:

- [ ] Application outcome taxonomy.
- [ ] Interview/outcome timestamps.
- [ ] Recommendation-to-application conversion.
- [ ] Application-to-interview conversion.
- [ ] Interview-to-offer conversion.
- [ ] Source quality.
- [ ] Skill-gap analytics.
- [ ] Post-application feedback.
- [ ] Offline re-ranking experiments.

Do not claim “learning” until real outcome data exists.

---

# 16. Phase P12 — Portfolio-grade engineering evidence 🟠

For each flagship capability, publish evidence rather than marketing claims.

## Architecture

- [ ] System architecture diagram.
- [ ] Discovery → matching → application sequence diagram.
- [ ] Data model diagram.
- [ ] Browser automation safety boundary diagram.

## Evaluation

- [ ] Golden dataset methodology.
- [ ] Metric definitions.
- [ ] Baseline vs improved ranking results.
- [ ] Failure cases.
- [ ] Error analysis.

## Tradeoffs

Document decisions such as:

- [ ] deterministic vs LLM-based extraction;
- [ ] lexical vs dense vs hybrid retrieval;
- [ ] embedding model choice;
- [ ] synchronous vs Celery execution;
- [ ] browser automation vs API integration;
- [ ] human approval vs full autonomy;
- [ ] PostgreSQL/pgvector vs external vector DB.

## Failure analysis

Include at least 2–3 real examples:

- [ ] false positive;
- [ ] false negative;
- [ ] JD extraction failure;
- [ ] browser automation failure;
- [ ] document/evidence failure.

Each should state:

```text
Observed failure
→ Root cause
→ Impact
→ Fix
→ Regression test
```

---

# 17. Phase P13 — Release gate 🏁

AI Job Agent can be called **v1 validated** only when all of the following are true:

### Core intelligence

- [ ] Real job discovery works for the documented supported sources.
- [ ] Full JD extraction works for supported sources.
- [ ] Candidate/job matching is measurable.
- [ ] Golden evaluation set exists.
- [ ] Ranking metrics are published.
- [ ] No placeholder scoring remains in production ranking.

### Documents

- [ ] Resume PDF/DOCX generation works.
- [ ] Cover-letter PDF/DOCX generation works.
- [ ] Evidence provenance is preserved.
- [ ] ATS analysis is reproducible.

### Application

- [ ] Mock ATS E2E passes.
- [ ] At least one documented real ATS flow is validated where legally/technically appropriate.
- [ ] Approval gate is enforced.
- [ ] Dry-run is safe.
- [ ] Audit trail is complete.
- [ ] Idempotency is verified.

### Product

- [ ] Frontend builds in CI.
- [ ] Critical frontend workflows hit real backend APIs.
- [ ] E2E smoke test passes.

### Engineering

- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] Migrations pass.
- [ ] CodeQL passes.
- [ ] CI passes.
- [ ] No generated repository noise.
- [ ] Documentation matches implementation.

### Production

- [ ] Secrets are externally managed.
- [ ] Monitoring exists.
- [ ] Backups/restore are documented.
- [ ] Deployment manifests contain no placeholders.
- [ ] Reliability limits are documented.

---

# 18. Recommended execution order

| Order | Workstream | Priority | Exit evidence |
|---:|---|---|---|
| 1 | Repository cleanup + docs reconciliation | 🔴 | Clean repo + truthful README |
| 2 | Canonical job pipeline audit | 🔴 | One documented job path |
| 3 | Embedding contract | 🔴 | Dimension/model validation tests |
| 4 | Real JD extraction | 🔴 | Source fixtures + extracted JDs |
| 5 | Candidate/job ranking | 🔴 | Reproducible ranking API |
| 6 | Golden evaluation set | 🔴 | 50–100 labelled cases + metrics |
| 7 | PDF/DOCX documents | 🔴 | Real uploadable artifacts |
| 8 | Mock ATS + E2E | 🔴 | Automated application test |
| 9 | Backend/frontend CI | 🟠 | Green CI workflow |
| 10 | Frontend integration QA | 🟠 | Critical workflows verified |
| 11 | Production hardening | 🟠 | Deployment/observability evidence |
| 12 | Portfolio evidence | 🟠 | Diagrams + evaluation + failures |
| 13 | Analytics/learning loop | 🟡 | Outcome dataset + analysis |
| 14 | v1 release | 🏁 | All release gates green |

---

# 19. Definition of done

The project is finished for the current v1 scope when:

> **A fresh clone can run the system, discover real supported jobs, extract structured JDs, rank them against a versioned candidate profile using a measurable hybrid evaluator, generate auditable PDF/DOCX application documents, pass a human approval gate, safely execute a documented application flow against a controlled ATS, record the complete audit trail, and prove the critical path through CI and reproducible evaluation.**

Anything beyond that—additional job sources, autonomous learning, advanced LLM generation, broader ATS coverage, recommendation feedback loops—is post-v1 unless explicitly promoted into the release scope.
