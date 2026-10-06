# Security Review — v1

## Implemented controls

| Area | Control | Status |
|---|---|---|
| Authentication | JWT auth with production secret validation | Implemented |
| Auth abuse | Login/register rate limits | Implemented |
| Authorization | User-scoped access | Implemented |
| CORS | Explicit production origins | Implemented |
| HTTP headers | CSP, HSTS, frame protection, nosniff, Referrer-Policy, Permissions-Policy | Implemented |
| API docs | Disabled in production | Implemented |
| Secrets | Default production secrets rejected | Implemented |
| Static analysis | CodeQL workflow | Implemented |
| Browser automation | Human approval + dry-run boundary | Implemented |
| Upload integrity | SHA-256 verification before browser upload | Implemented |

## Residual risks

1. External TLS termination and secret management remain deployment concerns.
2. The metrics endpoint should be network-restricted in production.
3. Browser automation is ATS-specific; universal reliability is not claimed.
4. Human approval remains required before external submission.
5. Outcome analytics can be biased by discovery/review/approval selection.

Security principle: fail closed on production configuration, document external
side effects, and never turn a dry-run into an implicit real submission.
