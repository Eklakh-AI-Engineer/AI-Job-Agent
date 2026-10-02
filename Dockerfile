# ---- Base ----
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Dependencies ----
FROM base AS deps
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# ---- API runtime ----
FROM deps AS api
# ``backend/`` is the parent of ``app/`` at runtime, so packages that cross
# reference each other (``backend.evaluation`` ↔ ``backend.jobs``) resolve
# without relative-import gymnastics. ``/app/backend`` is also on PYTHONPATH
# so ``app.*`` imports work without changing the WORKDIR.
ENV PYTHONPATH=/app:/app/backend
COPY backend/ /app/backend/
# Copy and enable the entrypoint script that applies migrations on boot.
RUN chmod +x /app/backend/entrypoint.sh
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl -f http://localhost:8000/health || exit 1
ENTRYPOINT ["/app/backend/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- Playwright browsers (for the automation worker image) ----
FROM deps AS automation
RUN pip install playwright && playwright install --with-deps chromium
ENV PYTHONPATH=/app:/app/backend
COPY backend/ /app/backend/
RUN chmod +x /app/backend/entrypoint.sh
WORKDIR /app/backend
ENTRYPOINT ["/app/backend/entrypoint.sh"]
CMD ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=INFO"]
