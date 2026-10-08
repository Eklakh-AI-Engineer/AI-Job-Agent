"""Vercel entrypoint for the AI Job Agent FastAPI backend.

The application itself remains in backend/app. This thin adapter keeps the
existing backend architecture intact while exposing it as a Vercel Python
Function.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.main import app  # noqa: E402

handler = app
