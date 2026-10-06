"""
backend/app/api/v1/router.py

Aggregates every v1 router into a single mountable APIRouter.

Adding a new resource means adding one line here, so ``main.py`` stays a thin
composition root.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.candidate_kb import router as candidate_kb_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.semantic_search import router as semantic_search_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(jobs_router)
api_router.include_router(evaluation_router)
api_router.include_router(semantic_search_router)
api_router.include_router(candidate_kb_router)
