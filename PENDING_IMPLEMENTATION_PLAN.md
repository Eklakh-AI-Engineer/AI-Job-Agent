# Pending Implementation Plan — AI Job Agent

**Last updated:** 2026-10-07  
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

- [x] Normalize skill aliases into canonical skills.
- [x] Preserve original wording for evidence.
- [x] Distinguish explicit source requirements from inferred/uncertain information.
- [x] Validate dates, experience ranges and education fields.
- [x] Add normalization confidence/status/provenance metadata.
- [x] Add regression fixtures for malformed and incomplete JDs.

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

- [x] Create a reproducible evaluation/gate command.
- [x] Store dataset lifecycle/version metadata.
- [x] Store model/config version in calibration/evaluation artifacts.
- [x] Define metric output artifacts and required keys.
- [x] Implement CI regression enforcement once the benchmark status is `validated`.
- [x] Publish evaluation policy and lifecycle documentation in `docs/evaluation/`.

**Acceptance:** matching improvements can be measured instead of judged only by screenshots or manual inspection.

---

# 8. Phase P4 — Document intelligence 🔴

## P4.1 Generate real professional artifacts

The document pipeline now renders deterministic source content into uploadable PDF
and DOCX artifacts.

- [x] PDF resume generation.
- [x] DOCX resume generation.
- [x] PDF cover-letter generation.
- [x] DOCX cover-letter generation.
- [x] Stable filenames and metadata.
- [x] Versioned artifacts.
- [x] SHA-256 artifact integrity metadata.
- [x] Local/S3-capable binary storage abstraction.
- [x] Approved PDF materialization for browser upload.

**Acceptance:** generated documents are real binary PDF/DOCX artifacts, versioned,
stored through the document abstraction and auditable back to the source text.

---

## P4.2 Evidence and ATS validation

- [x] Every generated claim maps to candidate evidence.
- [x] Track claim IDs in document metadata.
- [x] Run ATS analysis against generated source content before persistence.
- [x] Verify required keywords are represented without fabrication.
- [x] Add document artifact regression tests.
- [x] Add integrity verification before ATS upload.
- [ ] Human-review checklist remains a release-process item.

**Acceptance:** an approved document is a real PDF/DOCX artifact suitable for
application upload and remains auditable to candidate evidence.

---

# 9. Phase P5 — Application automation validation 🔴

The browser automation implementation is now covered by a deterministic mock ATS
and an executable real-ATS dry-run validator.

## P5.1 Mock ATS test harness

- [x] Controlled local ATS form.
- [x] Text field filling.
- [x] Resume upload.
- [x] Cover-letter upload.
- [x] Dry-run non-submission assertion.
- [x] Successful controlled submission.
- [x] Real application orchestration test through the fake form filler.

## P5.2 Real supported-ATS validation

- [x] Maintain ATS compatibility selector maps for Greenhouse, Lever and Workday.
- [x] Provide an executable dry-run validator for current public application URLs.
- [x] Use disposable example.invalid identity values.
- [x] Never click submit during real-ATS validation.
- [x] Preserve robots/rate-limit/human-approval boundaries.
- [ ] Execute and archive live Greenhouse/Lever/Workday browser-run evidence for a
  release snapshot. This is intentionally not marked validated until a browser
  runner has produced the evidence.

**Acceptance:** the repository cannot claim universal ATS reliability; it exposes
the exact validation harness and documents the remaining live evidence requirement.

---

# 10. Phase P6 — End-to-end product path 🔴

A deterministic service-level E2E now exists at
tests/integration/test_true_pipeline_e2e.py.

- [x] Seed candidate KB.
- [x] Seed canonical JobPosting.
- [x] Run real hybrid ranking with deterministic test embeddings.
- [x] Generate resume and cover letter.
- [x] Verify PDF/DOCX artifact metadata.
- [x] Approve the resume.
- [x] Transition application through Matched → Approved.
- [x] Submit through the real application orchestration with a controlled filler.
- [x] Verify Applied state.
- [x] Verify the generated PDF is materialized for upload.
- [x] Run the E2E test through GitHub Actions pipeline validation.

Remaining product-level coverage:

- [ ] Add browser-driven JD discovery/extraction to the same fixture.
- [ ] Add frontend API-state assertions.
- [ ] Add explicit failure/rollback assertions.

**Acceptance:** one deterministic test proves the core backend application loop from
candidate/job input through ranking, artifacts, approval and application audit.

---

# 11. Phase P7 — Backend + frontend CI 🟠

A standard CI workflow now exists at .github/workflows/ci.yml.

- [x] Python dependency installation.
- [x] Backend compileall gate.
- [x] Backend unit tests.
- [x] Frontend dependency installation with npm ci.
- [x] Frontend lint.
- [x] Frontend TypeScript compilation.
- [x] Frontend tests.
- [x] Next.js production build.
- [x] Repository-wide CodeQL remains enabled.
- [x] Final green-run evidence after the latest evaluator/security fixes (CI run 37510352606).

**Acceptance:** a fresh commit produces machine-verifiable backend and frontend health signals.

---

# 12. Phase P8 — Frontend integration validation 🟠

The frontend implementation is preserved and its build/test toolchain is now a release gate.

- [x] Frontend build, lint, typecheck and unit tests are CI-gated.
- [x] Candidate KB helper tests are present.
- [x] Add live backend health and protected-endpoint smoke tests.
- [x] Add live frontend application-shell smoke test.
- [x] Document authentication expiry/401 browser QA.
- [x] Document loading/empty/error, KB, ranking, document and application browser checks.
- [ ] Execute the live QA suite against a deployed environment.
- [ ] Record a browser-level smoke run for the primary supported viewport.

**Acceptance:** critical frontend workflows are backed by live API behavior, not only compile-time checks.

---

# 13. Phase P9 — Observability and production hardening 🟠

Implemented baseline controls are documented in docs/OBSERVABILITY.md.

- [x] Prometheus HTTP/database/Celery/auth/job/embedding/search metrics.
- [x] Request-ID correlation and structured production logging.
- [x] Production secret validation.
- [x] Explicit production CORS.
- [x] Production API docs disabled.
- [x] Baseline HTTP security headers.
- [ ] Restrict /metrics at ingress/network layer.
- [ ] Add alert delivery and operator dashboard.
- [ ] Database backup/restore evidence.
- [ ] Load-test baseline and capacity report.
- [ ] Harden Kubernetes placeholders, resources, HPA, PDB and NetworkPolicies.
- [ ] External secret management in the target deployment.

**Acceptance:** operational signals and deployment controls are backed by an actual target environment, not only local configuration.

---

# 14. Phase P10 — Security and responsible automation 🟠

A first-pass security review is documented in docs/SECURITY_REVIEW.md.

- [x] Production secrets/defaults reviewed.
- [x] Authentication rate limits reviewed.
- [x] CORS and browser security headers hardened.
- [x] Production API documentation disabled.
- [x] CodeQL workflow present.
- [x] Browser automation remains approval-gated and dry-run capable.
- [x] Artifact SHA-256 integrity checked before browser upload.
- [x] Dependency vulnerability scan in CI.
- [x] SSRF review and validation for browser/webhook URL-fetch paths.
- [x] Sensitive-file upload/type/signature/path traversal controls.
- [x] Browser automation URL safety boundary enforced before navigation.
- [x] Authentication rate-limit and authorization regression coverage exists.
- [ ] Production metrics endpoint network restriction.

**Acceptance:** every high-impact external side effect and sensitive API has an explicit security control and regression test.

---

# 15. Phase P11 — Outcome analytics and learning loop 🟡

A pure offline analytics layer now exists at backend/evaluation/outcome_metrics.py.

- [x] Application funnel metrics.
- [x] State transition rates.
- [x] Apply rate by ranking-score bucket.
- [x] Apply rate by job source.
- [x] Unit tests for the analytics primitives.
- [x] Safe offline learning-loop procedure documented.
- [ ] Capture interview/response/offer outcomes in the production data model.
- [ ] Build a recurring anonymized outcome export.
- [ ] Run real outcome analysis after sufficient application volume.
- [ ] Evaluate ranking changes against the frozen golden benchmark.

**Important:** this is analytics infrastructure, not claimed online learning. Automatic retraining remains disabled.

---

# 16. Phase P12 — Architecture, tradeoffs and failure analysis 🟠

Portfolio-grade engineering evidence is now substantially documented.

- [x] Current system architecture diagram/documentation.
- [x] Architecture decision/tradeoff record.
- [x] Failure analysis with real implementation failures.
- [x] Golden-set methodology and metric definitions.
- [x] Human-gold provenance boundary documented.
- [x] ATS safety boundary documented.
- [x] Add discovery → ranking → application sequence diagram.
- [x] Add data-model diagram.
- [x] Add browser-automation safety-boundary diagram.
- [ ] Publish baseline vs improved ranking metrics after human-verified data exists.
- [ ] Add human-reviewed false-positive/false-negative cases.

**Acceptance:** a reviewer can understand not only what the system does, but why the architecture was chosen, where it failed, and how regressions are prevented.

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
