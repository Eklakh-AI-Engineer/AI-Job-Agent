# AI Job Agent Documentation

## Current documentation

| Document | Purpose |
|---|---|
| [Architecture](ARCHITECTURE.md) | Implemented backend boundary and future platform architecture |
| [Development](DEVELOPMENT.md) | Local setup, Docker, tests, migrations |
| [Tech Stack](TECH_STACK.md) | Current technology vs planned technologies |
| [Roadmap](ROADMAP.md) | Current milestone and future phases |
| [Security](SECURITY.md) | Authentication, authorization, secrets, and automation boundaries |
| [API contracts](10_API/) | Detailed endpoint documentation |
| [Deferred components](deferred-components.md) | Explicitly deferred work |
| [Research](01_Research/) | Research and product background |
| [Architecture specs](02_Architecture/) | Detailed architecture specifications |
| [AI specs](03_AI/) | AI/agent design material |
| [Backend specs](04_Backend/) | Backend implementation specifications |
| [Testing](08_Testing/) | Test strategy and validation material |
| [Database](11_Database/) | Database documentation |

## Documentation rule

The top-level documents describe the **current repository state** and distinguish implemented behavior from planned architecture.

The numbered documentation directories contain deeper specifications and research. A specification is not evidence that its proposed component has already been implemented.

When documentation and runtime behavior disagree, implementation and tests are the source of truth; update the documentation rather than silently treating planned functionality as complete.
