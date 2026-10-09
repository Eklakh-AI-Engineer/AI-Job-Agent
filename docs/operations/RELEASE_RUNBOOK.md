# v1 Release Runbook

## Release gates

1. CI backend, true-pipeline E2E, frontend build/test, security and benchmark validation are green; a clean checkout must pass `npm ci`.
2. Ranking regression gate passes.
3. CI must evaluate the exact frozen adjudicated workbook whose SHA-256 is `ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e`. The currently committed CI input at `docs/evaluation/Human_Benchmark_Labeled_v1.xlsx` has a different recorded hash (`908597ca7e9a995fe83f0fc98d8ae608561543f6f71bdf51eed0cb7408a6ee92`); reconcile the artifact before promotion.
4. Every benchmark job is mapped to a real persisted `job_postings.id`, and the production ranking baseline is generated from runtime ranker output on the frozen dataset.
5. The production ranking regression workflow passes against matching dataset hashes and `ranking_version`.
6. Frontend live QA and authenticated production smoke pass against the deployed API/frontend.
7. ATS dry-run evidence is captured without external submission.
8. Production monitoring signals and alert delivery are verified.
9. Backup/restore is verified for the production database and artifact storage.
10. Final audit is updated from observed evidence.
11. Only then create the v1.0.0 tag.

## Current evidence boundary

As of 2026-10-09, CI, public production health/metrics/shell smoke, basic live API/frontend smoke, and two real ATS dry runs have passed. Release remains blocked by the CI workbook/final frozen-artifact hash mismatch, real persisted-job mapping/runtime baseline, authenticated smoke (credentials are absent and the authenticated path was skipped), verified alert delivery, and production database/storage restore evidence. A green basic health check or source-workbook diagnostic does not satisfy these gates.

Never mark those gates complete from configuration alone.
