# Observability & Production Hardening

## Signals

Prometheus metrics cover HTTP request count/status/latency, database latency,
Celery task count/status/duration, authentication attempts, job ingestion and
evaluation, embedding generation/dimensions, and semantic-search latency.

Requests receive an X-Request-ID. Production logging uses JSON output.

## Operational targets

These are release targets, not current measured claims:

- API availability >= 99.5%
- p95 synchronous API latency < 500 ms
- p95 semantic search < 1 s
- Celery failure rate < 2%
- Supported-source JD extraction success > 95%

Actual release evidence must include an observation window.

## Hardening checklist

- [x] Production secrets fail closed.
- [x] Production CORS is explicit.
- [x] Production API docs are disabled.
- [x] Security headers are attached.
- [x] Request IDs are propagated.
- [x] Auth rate limits are enabled.
- [x] Core Prometheus signals exist.
- [ ] Restrict metrics at ingress/network layer.
- [ ] Add alert delivery and operator dashboard.
- [ ] Load-test the final deployment topology.
