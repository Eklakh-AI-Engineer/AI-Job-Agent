# AI Job Agent Security

## Current security boundary

The current backend includes authentication and authorization as part of its API foundation. Secrets are supplied through environment/configuration rather than committed source.

## Core controls

The project should preserve:

- authenticated API access;
- authorization checks;
- password hashing;
- bearer-token handling;
- environment-based secrets;
- database migration discipline;
- least-privilege access to external services.

## Application automation boundary

External job-application submission is a higher-risk operation than recommendation or drafting.

The target architecture therefore requires:

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
External submission
```

The repository should not claim autonomous submission without these controls and corresponding verification.

## Third-party services

Job-board and ATS integrations must respect applicable platform terms and authentication requirements.

Credentials, API keys, cookies, browser session data, and tokens must never be committed.

This document is an engineering boundary, not a security certification.
