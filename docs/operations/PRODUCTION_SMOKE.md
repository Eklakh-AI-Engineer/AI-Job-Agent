# Production Smoke Checklist

## Backend
- GET /health returns HTTP 200 and database=healthy.
- GET /metrics returns Prometheus exposition.
- Protected API rejects unauthenticated access.
- Authenticated test account can load profile and jobs.
- Ranking endpoint returns components and ranking_version.
- Candidate KB round-trip succeeds.
- Resume and cover-letter generation succeeds.
- Approval gate prevents submission without explicit approval.
- Approved mock/dry-run submission records an audit event.

## Frontend
- Application shell returns HTTP 200.
- Login succeeds with a disposable account.
- Invalid credentials render an actionable error.
- Dashboard loads jobs and empty/error states.
- Evaluation view renders ranking evidence.
- Candidate KB save/load works.
- Document generation status is visible.
- Approval gate is visible before submission.

## Evidence
Record timestamp, deployment SHA, API URL, frontend URL, test account identifier (never password), HTTP status, and screenshots/log references. Do not commit secrets.


## Observed evidence — 2026-10-09

The verified production aliases are:

- Frontend: `https://ai-job-agent-theta.vercel.app`
- API: `https://ai-job-agent-api-mu.vercel.app`

[Production monitoring run 37879741621](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37879741621) passed five consecutive `/health` probes (`status=ok`, `database=healthy`), `/metrics` (Prometheus metric present), and frontend HTML shell checks. [Live QA run 37879724894](https://github.com/Eklakh-AI-Engineer/AI-Job-Agent/actions/runs/37879724894) passed five repeated health probes, both unauthenticated-route checks, and the frontend shell check.

**Still unverified:** authenticated profile/job-listing reads, candidate-KB persistence, ranking response/version, document generation and artifact persistence, approval lifecycle, and restore validation. The current live QA suite does not exercise these authenticated workflows because a disposable production test account/credential pair has not been configured. Do not create a permanent production test account without an explicit cleanup plan.
