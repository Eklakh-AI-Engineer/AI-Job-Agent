# AI Job Agent Security

## Current security boundary

The backend includes authentication/authorization, environment-based secrets, rate limiting and audit events. Production configuration is deliberately stricter than local development.

## Core controls

- authenticated API access and authorization checks;
- password hashing and bearer-token handling;
- production secret validation;
- strict production CORS configuration;
- authentication endpoint rate limiting;
- database migration discipline;
- least-privilege external-service credentials;
- SSRF validation before server-side HTTP/browser navigation;
- loopback URL exceptions only in explicit non-production environments;
- PDF/DOCX upload extension, size, signature and symlink validation;
- CodeQL plus Python and frontend dependency vulnerability scanning in CI.

## Untrusted job-board content

Job descriptions and external pages are treated as untrusted input.
Extraction should preserve source evidence and must not silently turn arbitrary JD instructions into privileged system instructions. Prompt-injection testing is a separate release gate and must be run against realistic malicious fixtures.

## Browser automation boundary

External job-application submission is higher risk than recommendation or drafting.

```text
Generate / prepare
      |
      v
User review
      |
      v
Explicit approval
      |
      v
Controlled ATS browser workflow
      |
      v
External submission
```

Browser navigation must pass the SSRF policy before the page is opened. Production must never enable the local/loopback exception.

## Third-party services

Job-board and ATS integrations must respect applicable platform terms and authentication requirements.
Credentials, API keys, cookies, browser session data and tokens must never be committed.

This document is an engineering boundary, not a security certification.
