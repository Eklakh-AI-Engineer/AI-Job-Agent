# v1 Release Runbook

## Release gates

1. CI backend, true-pipeline E2E, frontend build/test, security and benchmark validation are green.
2. Ranking regression gate passes.
3. Human benchmark is independently adjudicated and frozen before production ranking claims.
4. Frontend live QA passes against the deployed API/frontend.
5. ATS dry-run evidence is captured without external submission.
6. Production smoke checks pass.
7. Monitoring signals and alert delivery are verified.
8. Backup/restore is verified for the production database and artifact storage.
9. Final audit is updated from observed evidence.
10. Only then create the v1.0.0 tag.

## Current evidence boundary

The repository has reproducible local/CI evidence for the application pipeline, but live deployment, real ATS browser execution, production monitoring, and production backup/restore require external service access.

Never mark those gates complete from configuration alone.
