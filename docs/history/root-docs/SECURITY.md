# Security Policy

## Supported Versions
| Version | Supported |
|---|---|
| `main` branch | ✅ |
| Latest stable release | ✅ |
| Older releases | ❌ |

## Reporting a Vulnerability
**Do not report security vulnerabilities through public GitHub Issues.**

Email: `security@yourdomain.com` (replace with the project's official contact once registered), or contact a maintainer privately via GitHub.

Include: description, reproduction steps, impact assessment, PoC, environment details, and logs if relevant.

| Action | Target Time |
|---|---|
| Acknowledge report | Within 72 hours |
| Initial investigation | Within 7 days |
| Status update | Every 14 days |

## Responsible Disclosure
Give maintainers reasonable time to investigate before public disclosure, avoid accessing data beyond what's needed to demonstrate the issue, and avoid destructive testing.

## Scope
Backend APIs, AI agents, browser automation, authentication, cloud infrastructure, databases, dashboard, Docker images, deployment configs, and CI/CD pipelines.

## AI-Specific Security
- **Prompt injection:** untrusted content (job descriptions, scraped pages) must always be treated as data, never as instructions.
- **Hallucination prevention:** the system must never invent experience, skills, degrees, or certifications.
- **Data isolation:** each user's resumes, applications, and credentials must remain isolated from other users.

## Secrets Management
Never commit API keys, passwords, tokens, or credentials. Use environment variables or a secret manager (AWS Secrets Manager, Vault, GitHub Secrets).

## Browser Automation Security
Encrypted session storage, no logging of sensitive form data, secure cookie storage, and no bypassing of CAPTCHAs or anti-abuse systems.

## Infrastructure
HTTPS/TLS everywhere, reverse proxy, firewall rules, rate limiting, encrypted storage, and regular backups in production.
