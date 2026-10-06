"""
backend/app/core/metrics.py

Prometheus metrics for the application.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
)

# Celery task metrics
celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks executed",
    ["task_name", "status"],
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

# Authentication metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["endpoint", "result"],
)

# Job metrics
jobs_ingested_total = Counter(
    "jobs_ingested_total",
    "Total jobs ingested",
    ["source", "status"],
)

jobs_evaluated_total = Counter(
    "jobs_evaluated_total",
    "Total jobs evaluated",
    ["result"],
)

# Embedding metrics
embedding_generation_total = Counter(
    "embedding_generation_total",
    "Total embeddings generated",
    ["provider", "status"],
)

embedding_generation_duration_seconds = Histogram(
    "embedding_generation_duration_seconds",
    "Embedding generation duration in seconds",
    ["provider"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
)

embedding_dimensions = Gauge(
    "embedding_dimensions",
    "Embedding dimensions",
    ["provider"],
)

# Semantic search metrics
semantic_search_total = Counter(
    "semantic_search_total",
    "Total semantic searches performed",
    ["status", "has_filters"],
)

semantic_search_duration_seconds = Histogram(
    "semantic_search_duration_seconds",
    "Semantic search duration in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get endpoint pattern (remove IDs for cardinality control)
        endpoint = request.url.path
        for prefix in ["/api/v1/jobs/", "/api/v1/users/"]:
            if endpoint.startswith(prefix):
                # Replace IDs with placeholder
                parts = endpoint.split("/")
                for i, part in enumerate(parts):
                    if part.isdigit():
                        parts[i] = "{id}"
                endpoint = "/".join(parts)
                break
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)
        
        return response


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )