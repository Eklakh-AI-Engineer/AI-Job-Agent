"""
backend/app/services/errors.py

Domain-level errors raised by the service layer.

Services raise these instead of HTTP exceptions so the business rules stay
independent of FastAPI. The API layer maps them to status codes, which keeps
"duplicate email" a 409 in one endpoint and a different code elsewhere if the
policy ever changes.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for all service-layer errors."""

    #: HTTP status code the API layer should use when this error is unhandled.
    status_code: int = 400


class UserAlreadyExistsError(ServiceError):
    """Raised when registering an email that is already in use."""

    status_code = 409


class UserNotFoundError(ServiceError):
    """Raised when a user id or email does not resolve to a user."""

    status_code = 404


class InactiveUserError(ServiceError):
    """Raised when authentication succeeds but the account is disabled."""

    status_code = 403


class AuthenticationError(ServiceError):
    """
    Raised when credentials are wrong.

    Deliberately generic: callers must not be able to distinguish "unknown
    email" from "wrong password", which would enable account enumeration.
    """

    status_code = 401


class JobAlreadyExistsError(ServiceError):
    """Raised when ingesting a job posting whose URL already exists."""

    status_code = 409


class JobNotFoundError(ServiceError):
    """Raised when a job posting id does not resolve."""

    status_code = 404
