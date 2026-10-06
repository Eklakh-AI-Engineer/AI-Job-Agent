"""
backend/app/core/logging.py

Structured logging configuration with request ID correlation.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict

import structlog
from structlog.types import EventDict, WrappedLogger


# Context variable to store request ID across async calls
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())[:8]


def add_request_id(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request ID to log entries if available."""
    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_timestamp(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log entries."""
    from datetime import datetime, timezone
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        json_logs: If True, output JSON logs; otherwise, human-readable console format
    """
    # Standard library logging config
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_timestamp,
        add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggingMiddleware:
    """ASGI middleware to add request ID to each request."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate or extract request ID
        request_id = generate_request_id()
        headers = scope.get("headers", [])
        
        # Check for existing request ID in headers
        for key, value in headers:
            if key.decode().lower() == "x-request-id":
                request_id = value.decode()
                break
        
        # Set request ID in context
        token = request_id_var.set(request_id)
        
        # Add request ID to response headers
        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)
        
        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_var.reset(token)