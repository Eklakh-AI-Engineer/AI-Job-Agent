"""
Root conftest — shared pytest configuration and import bootstrap.

The backend is packaged so that ``backend/`` is the import root at runtime
(the container runs ``uvicorn app.main:app`` with ``/app/backend`` as the
working directory). Tests, however, execute from the repository root, so both
the repository root and ``backend/`` must be importable here:

- repo root  → ``import backend.jobs.models`` (used by the Phase 2/3 unit tests)
- backend/   → ``import app.main``             (used by the integration tests)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
