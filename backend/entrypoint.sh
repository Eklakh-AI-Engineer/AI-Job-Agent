#!/bin/sh
# Container entrypoint — applies any pending Alembic migrations before
# starting the API. Failures here are intentional: a broken migration must
# not silently produce a half-deployed service.
set -e

echo "[entrypoint] applying database migrations…"
alembic upgrade head

echo "[entrypoint] starting: $@"
exec "$@"
