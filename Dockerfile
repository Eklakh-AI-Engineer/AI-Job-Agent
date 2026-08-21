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

# ---- Playwright browsers (for the automation worker image) ----
FROM deps AS automation
RUN pip install playwright && playwright install --with-deps chromium
COPY backend/ /app/backend/
WORKDIR /app/backend
CMD ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=INFO"]

# ---- API runtime ----
FROM deps AS api
COPY backend/ /app/backend/
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
