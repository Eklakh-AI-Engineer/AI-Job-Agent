"""
backend/app/services/notification_service.py

Pluggable notification hooks for the human-approval workflow.

The default notifier logs to the application logger. Set
``NOTIFICATION_BACKEND=webhook`` and ``NOTIFICATION_WEBHOOK_URL`` to POST
notifications to a Slack/Teams/webhook endpoint instead. Failures are logged
and swallowed — a notification outage must never block the workflow.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def _send_webhook(url: str, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


async def notify(
    event: str,
    user_id: int,
    message: str,
    extra: Optional[dict] = None,
) -> None:
    """
    Send a notification for a workflow event.

    Never raises: notification failures are logged and ignored.
    """
    payload = {
        "event": event,
        "user_id": user_id,
        "message": message,
        "extra": extra or {},
    }

    backend = os.getenv("NOTIFICATION_BACKEND", "log").lower()
    try:
        if backend == "webhook":
            url = os.getenv("NOTIFICATION_WEBHOOK_URL")
            if not url:
                logger.warning("NOTIFICATION_WEBHOOK_URL not set; logging instead")
                logger.info(f"[notify] {payload}")
                return
            await _send_webhook(url, payload)
        else:
            logger.info(f"[notify] {payload}")
    except Exception as exc:  # noqa: BLE001 - notifications must not break flow
        logger.warning(f"Notification delivery failed ({event}): {exc}")


async def notify_pending_approval(
    user_id: int, application_id: int, job_title: str, company: str
) -> None:
    """Notify that an application is awaiting human approval."""
    await notify(
        event="application.pending_approval",
        user_id=user_id,
        message=(
            f"Application for '{job_title}' at {company} is ready for review "
            f"and approval."
        ),
        extra={"application_id": application_id, "job_title": job_title, "company": company},
    )


async def notify_submitted(user_id: int, application_id: int, job_title: str, company: str) -> None:
    """Notify that an application was submitted."""
    await notify(
        event="application.submitted",
        user_id=user_id,
        message=f"Application for '{job_title}' at {company} was submitted.",
        extra={"application_id": application_id},
    )


async def notify_rejected(user_id: int, application_id: int, reason: Optional[str]) -> None:
    """Notify that an application was rejected/skipped."""
    await notify(
        event="application.rejected",
        user_id=user_id,
        message=f"Application {application_id} was rejected.",
        extra={"application_id": application_id, "reason": reason},
    )