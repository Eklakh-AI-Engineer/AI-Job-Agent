# Changelog

All notable changes to this project are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/); this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- Phase 1 repository foundation: governance files, tooling, CI/CD, Docker, docs skeleton, test scaffolding, monitoring config.

## [0.4.0] - Backend Foundation
### Added
- FastAPI service skeleton with a versioned API: `/api/v1/auth`, `/api/v1/users`, `/api/v1/jobs`.
- Authentication: bcrypt password hashing, JWT bearer tokens, `get_current_user` dependency.
- Service layer (`backend/app/services`) separating business rules from HTTP concerns.
- Request/response schemas (`backend/app/schemas`) with validation and no secret leakage.
- Root `/` and `/health` probes; `/health` reports database reachability without failing the probe.
- Unit tests for the security and service layers; integration tests for every v1 endpoint.
- `docs/10_API/Authentication.md` and `docs/10_API/Jobs.md` documenting the implemented contract.

### Changed
- `main.py` is now a thin composition root; the inline `/jobs` route moved into `app/api/v1/jobs.py`.
- Integration tests are enabled in the default pytest run (`asyncio_mode = auto`).
- Settings gained `jwt_expire_minutes`, `cors_origins`, `api_v1_prefix`, `app_name`, and HTTP host/port.

### Fixed
- Added missing runtime dependencies: `pgvector`, `PyYAML`, `PyJWT`, `passlib`, `bcrypt`, `email-validator`, `greenlet`.
- Resolved forward-reference lint errors in `app/models/user.py` and `app/models/job.py`.
- Formatted `backend/` with `black` and cleared all `ruff` errors, so the CI lint job now passes.

## [0.1.0] - Planning Phase
### Added
- README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT
- Defined project vision, objectives, and repository structure
- Initial multi-agent architecture design

## Upcoming
| Version | Focus |
|---|---|
| 0.2.0 | `docs/` — vision, research, personas, competitor analysis |
| 0.3.0 | System, database, API, and agent architecture |
| 0.4.0 | Backend foundation: auth, PostgreSQL, Docker, Redis |
| 0.5.0 | Job Discovery, JD Parser, Company Research agents |
| 0.6.0 | Resume, ATS, Cover Letter agents |
| 0.7.0 | Browser automation + human-approval application assistant |
| 0.8.0 | Dashboard, analytics, learning agent |
| 0.9.0 | Cloud deployment, Kubernetes, CI/CD, scaling |
| 1.0.0 | First stable release |

## Compatibility
| Version | Status |
|---|---|
| 0.x.x | Experimental |
| 1.x.x | Stable |
