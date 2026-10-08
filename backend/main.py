"""Vercel entrypoint for the FastAPI backend.

The canonical application remains in app.main so local Docker/Kubernetes
and Vercel deployments share the same application composition root.
"""
from app.main import app

handler = app
