# AI Job Agent — Release Audit (2026-10-09)

## Decision

**Release status: BLOCKED — do not tag v1.0.0 yet.**

The repository has meaningful code/CI evidence, but the current benchmark source, live environment configuration, production database mapping, deployment, and restore validation do not support a production-ready claim. This document records observed evidence, not intended capabilities.

## Gate scoreboard

| Gate | Status | Evidence / remaining action |
|---|---|---|
| Backend + frontend CI | PASS on commit `40af7749543ac5c96fcd676191906f8d7e0479ab` | [CI run 37878526151](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878526151). Backend tests including true-pipeline E2E, frontend lint/type/test/build, dependency audit, benchmark structure, and synthetic comparison passed on that commit. Re-run after later benchmark evaluator changes. |
| True-pipeline E2E defect | FIXED in code; revalidation pending latest CI | The failure was caused by importing the same Pydantic evaluation models under both `backend.evaluation.*` and `evaluation.*`, producing distinct class identities. The E2E test now imports the canonical `evaluation.*` package and the ranker no longer dynamically imports `backend.evaluation.requirements`. |
| Human label adjudication | ADJUDICATION COMPLETE; repository artifact contract still needs verification | The frozen workbook manifest records 500 rows, 100 synthetic job groups, 141 second reviews, 83 two-reviewer consensuses, and 58 third adjudications. Final workbook SHA-256: `ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e`. Source workbook SHA-256: `908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`. CI currently evaluates `docs/evaluation/Human_Benchmark_Labeled_v1.xlsx`; ensure that path contains the final-gold column/artifact before treating its scoreboard as adjudicated. |
| Human evaluator schema | FIXED IN CODE; revalidation pending latest CI | Evaluator now prefers `Final Gold Label` / `Final Chosen Label` over the first-pass `Human Label`, and reports the selected column, frozen state, and production-authority state. A regression test protects this contract. |
| Real persisted-job mapping | BLOCKED | `JOB-001`…`JOB-100` are synthetic IDs. No authorized connection to the AI Job Agent production database was available during this audit to prove a one-to-one mapping to `job_postings.id` records. Do not fabricate mappings or mark this gate complete. |
| Production ranking baseline | BLOCKED | `docs/evaluation/baseline.json` and `latest.json` are explicitly non-authoritative reference metrics. They are not runtime-ranker outputs over mapped production records. |
| Regression gate | FAIL-CLOSED GUARD IMPLEMENTED | `scripts/ranking_regression_gate.py` now rejects non-authoritative baselines by default. General CI labels the existing comparison as synthetic plumbing only. Manual workflow: [production-ranking-regression.yml](../../.github/workflows/production-ranking-regression.yml). It must remain blocked until an authoritative baseline and runtime result are committed. |
| Scheduled monitoring | BLOCKED by configuration | [Run 37858845933](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37858845933) failed at URL validation: both `LIVE_API_URL` and `FRONTEND_URL` were empty. It did not reach health/metrics checks. The workflow now prints an actionable error and accepts manual HTTPS URL overrides; configure repository Actions secrets to enable recurring monitoring. |
| Frontend live QA | NOT RUN against production | Workflow supports manual HTTPS URL overrides. It still needs verified deployed API and frontend URLs, then must pass both live jobs. |
| Real ATS dry run | PASS — two public Lever pages | [Run 37878526195](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878526195) passed. Both pages returned `success=true`, `dry_run=true`, no errors, and mapped the disposable fields. No application was submitted. Evidence artifact: [real-ats-dry-run-evidence](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878526195/artifacts/11593586461), SHA-256 `12f09b8c3db743722d3b3a152da9ef47d8d290b20c4b7f0c74a8118841b84ded`. Re-run after the JSON newline correction commit. |
| Deployment / production smoke | NOT VERIFIED | No current production API/frontend URLs or authorized AI Job Agent database access were available to validate health, authentication, persisted jobs, artifact storage, and end-to-end frontend/API behavior. |
| Backup / restore | NOT VERIFIED | The runbook explicitly requires a restore into a disposable environment. No authorized AI Job Agent production database and separate restore target were available. Never run a destructive restore against production. |
| Monitoring / alert delivery | NOT VERIFIED | Scheduled checks are configured, but secrets are missing and alert delivery has not been exercised. |
| Release tag `v1.0.0` | BLOCKED | Create only after every release gate above has evidence and the authoritative ranking gate passes. |

## Changes made during this audit

- Fixed duplicate Pydantic model identity in the true-pipeline E2E path by standardizing imports to the `evaluation.*` package.
- Made ranking-regression comparison fail closed unless baseline and latest results are explicitly production-authoritative. The synthetic comparison requires an explicit opt-in and is labelled non-production.
- Added a manual production ranking gate that preserves its output as a GitHub Actions artifact.
- Improved monitoring and live-QA workflows with HTTPS validation and manual URL overrides while preserving recurring monitoring's need for configured secrets.
- Added JSON output and a 90-day evidence artifact for the real ATS dry-run workflow.
- Corrected the human benchmark evaluator to prefer adjudicated gold labels when present and to report whether the selected input is actually frozen/authoritative.

## Required actions to unblock release

1. Commit the exact frozen `Human_Gold_Final_v1.xlsx` artifact (or an equivalent complete, reviewed machine-readable gold dataset) to the repository; preserve and verify its SHA-256. Ensure CI evaluates the adjudicated labels, not first-pass labels.
2. Obtain authorized access to the AI Job Agent production database and export the real `job_postings` records needed for the benchmark. Create a reviewed mapping for every synthetic benchmark job; verify IDs, title/company/source URL, and mapping uniqueness. Do not expose candidate PII in evidence artifacts.
3. Run the actual `hybrid-v1` ranker over that frozen mapped benchmark and generate `baseline.json` / `latest.json` with `production_authoritative: true`, identical benchmark hashes, and matching `ranking_version`.
4. Run the manual production ranking gate and preserve its artifact.
5. Configure GitHub Actions secrets `LIVE_API_URL` and `FRONTEND_URL` with verified HTTPS deployment URLs; rerun production monitoring and frontend live QA.
6. Validate production smoke checks, run a real ATS dry run after the latest script commit, and retain artifacts.
7. Verify a database and artifact-storage restore in a separate disposable environment; record backup ID, restore timestamp, row-count checks, migration state, and smoke-test outcome.
8. Re-run the complete CI/E2E suite, review every gate, then create `v1.0.0`.

## Evidence integrity rule

A configured workflow is not a passed workflow. A successful synthetic benchmark comparison is not production ranking evidence. A backup existing is not a verified restore. Any gate without a dated execution artifact remains **NOT VERIFIED**.
