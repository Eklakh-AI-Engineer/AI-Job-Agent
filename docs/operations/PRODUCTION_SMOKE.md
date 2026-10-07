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
