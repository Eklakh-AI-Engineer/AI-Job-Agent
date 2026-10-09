# AI Job Agent — Release Audit (2026-10-09)

## Decision

**Release status: BLOCKED — do not tag v1.0.0 yet.**

The repository has meaningful code/CI evidence, but the current benchmark source, live environment configuration, production database mapping, deployment, and restore validation do not support a production-ready claim. This document records observed evidence, not intended capabilities.

## Gate scoreboard

| Gate | Status | Evidence / remaining action |
|---|---|---|
| Backend + frontend CI | PASS on commit `60c9308aee298eee0be8c0cb0eb1deb160da5b6d` | [CI run 37878922771](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878922771). Backend tests including true-pipeline E2E, frontend lint/type/test/build, dependency audit, benchmark structure, synthetic comparison, and benchmark evaluator regression tests passed on that commit. Re-run after later workflow changes. |
| True-pipeline E2E defect | FIXED AND VERIFIED | The failure was caused by importing the same Pydantic evaluation models under both `backend.evaluation.*` and `evaluation.*`, producing distinct class identities. The E2E test now imports the canonical `evaluation.*` package and the ranker no longer dynamically imports `backend.evaluation.requirements`. |
| Human label adjudication | ADJUDICATION COMPLETE; repository artifact contract still needs verification | The frozen workbook manifest records 500 rows, 100 synthetic job groups, 141 second reviews, 83 two-reviewer consensuses, and 58 third adjudications. Final workbook SHA-256: `ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e`. Source workbook SHA-256: `908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`. CI currently evaluates `docs/evaluation/Human_Benchmark_Labeled_v1.xlsx`; ensure that path contains the final-gold column/artifact before treating its scoreboard as adjudicated. |
| Human evaluator schema | CODE TEST PASS; FINAL GOLD ARTIFACT NOT IN CI INPUT | Evaluator now prefers `Final Gold Label` / `Final Chosen Label` over the first-pass `Human Label`, and reports the selected column, frozen state, and production-authority state. A regression test protects this contract. |
| Real persisted-job mapping | BLOCKED | `JOB-001`…`JOB-100` are synthetic IDs. No authorized connection to the AI Job Agent production database was available during this audit to prove a one-to-one mapping to `job_postings.id` records. Do not fabricate mappings or mark this gate complete. |
| Production ranking baseline | BLOCKED | `docs/evaluation/baseline.json` and `latest.json` are explicitly non-authoritative reference metrics. They are not runtime-ranker outputs over mapped production records. |
| Regression gate | FAIL-CLOSED GUARD IMPLEMENTED | `scripts/ranking_regression_gate.py` now rejects non-authoritative baselines by default. General CI labels the existing comparison as synthetic plumbing only. Manual workflow: [production-ranking-regression.yml](../../.github/workflows/production-ranking-regression.yml). It must remain blocked until an authoritative baseline and runtime result are committed. |
| Scheduled monitoring | PASS for production health/metrics/shell smoke | [Run 37879029230](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37879029230) passed URL validation, backend `/health`, backend `/metrics` (`http_requests_total` present), and frontend HTML shell checks using the verified production aliases `https://ai-job-agent-api-mu.vercel.app` and `https://ai-job-agent-theta.vercel.app`. The older [run 37858845933](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37858845933) failed because the secrets were empty; the workflow now has verified public-alias fallbacks and still supports secret/input overrides. |
| Frontend live QA | PASS — limited production smoke | [Run 37879071209](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37879071209) passed all three live checks: API health, unauthenticated protected-route rejection, and frontend HTML shell. The first run, [37878998138](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878998138), exposed a lock mismatch: `frontend/package.json` requires Next/eslint-config-next 16.3.8 while `package-lock.json` still pins 16.2.12. The live QA workflow now uses `npm install` so smoke tests can run, but synchronize and commit the lockfile before claiming reproducible clean installs. |
| Clean frontend dependency install | BLOCKED | `npm ci` fails because `package.json` and `package-lock.json` disagree (Next/eslint-config-next 16.3.8 vs 16.2.12, plus transitive lock differences). Live QA used `npm install` and passed, but this is not a substitute for a synchronized lockfile. Regenerate and commit `frontend/package-lock.json`, then require `npm ci` in CI. |
| Real ATS dry run | PASS — two public Lever pages | [Run 37878526195](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878526195) passed. Both pages returned `success=true`, `dry_run=true`, no errors, and mapped the disposable fields. No application was submitted. Evidence artifact: [real-ats-dry-run-evidence](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878526195/artifacts/11593586461), SHA-256 `12f09b8c3db743722d3b3a152da9ef47d8d290b20c4b7f0c74a8118841b84ded`. Re-run after the JSON newline correction: [run 37878767157](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878767157), artifact [real-ats-dry-run-evidence](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37878767157/artifacts/11593716604), SHA-256 `e6450797f011941731a283329e48fdc0c7e555c4462b0e8017fc15813658d53d`. |
| Deployment / production smoke | PARTIALLY VERIFIED | Vercel confirms production deployments and stable aliases for the frontend and FastAPI API; monitoring smoke passes. Full production smoke (authenticated user, database-backed job listing, candidate-KB round trip, generated artifact persistence, and approval-gated application workflow) is still pending live QA. |
| Backup / restore | NOT VERIFIED | The runbook explicitly requires a restore into a disposable environment. No authorized AI Job Agent production database and separate restore target were available. The connected Supabase project list does not include an AI Job Agent project, and Vercel environment-variable inspection is denied for the project scope. The database and storage restore cannot safely be run until that access is restored. Never run a destructive restore against production. |
| Monitoring / alert delivery | PARTIAL | Scheduled smoke checks now use verified public aliases and passed once. Alert notification delivery (not just workflow success) has not been exercised. |
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
2. Regenerate and commit `frontend/package-lock.json` from the current `frontend/package.json`; prove `npm ci` succeeds from a clean checkout.
3. Obtain authorized access to the AI Job Agent production database and export the real `job_postings` records needed for the benchmark. Create a reviewed mapping for every synthetic benchmark job; verify IDs, title/company/source URL, and mapping uniqueness. Do not expose candidate PII in evidence artifacts.
4. Run the actual `hybrid-v1` ranker over that frozen mapped benchmark and generate `baseline.json` / `latest.json` with `production_authoritative: true`, identical benchmark hashes, and matching `ranking_version`.
5. Run the manual production ranking gate and preserve its artifact.
6. Keep the verified stable aliases or configure GitHub Actions secrets `LIVE_API_URL` and `FRONTEND_URL`; monitoring now passes. Both current live QA smoke jobs pass using `npm install`; synchronize the lockfile, restore `npm ci`, and re-run before release.
7. Validate production smoke checks, run a real ATS dry run after the latest script commit, and retain artifacts.
8. Verify a database and artifact-storage restore in a separate disposable environment; record backup ID, restore timestamp, row-count checks, migration state, and smoke-test outcome.
9. Re-run the complete CI/E2E suite, review every gate, then create `v1.0.0`.

## Evidence integrity rule

A configured workflow is not a passed workflow. A successful synthetic benchmark comparison is not production ranking evidence. A backup existing is not a verified restore. Any gate without a dated execution artifact remains **NOT VERIFIED**.
