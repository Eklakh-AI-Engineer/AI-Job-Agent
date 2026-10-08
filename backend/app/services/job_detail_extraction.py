"""Detail-page job description extraction.

Discovery identifies listing URLs; this module extracts the actual posting body.
It deliberately fails when no meaningful description is found instead of
persisting a fabricated placeholder.
"""

from __future__ import annotations

import re
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

from app.core.ssrf import validate_public_url


DESCRIPTION_SELECTORS = (
    '[data-automation-id="jobPostingDescription"]',
    '[data-qa="job-description"]',
    '[data-qa="posting-description"]',
    ".posting-page .section-wrapper",
    ".job-description",
    ".jobDescription",
    "article",
    "main",
)


def clean_job_text(text: str) -> str:
    """Normalize browser-extracted text while preserving paragraph boundaries."""
    text = text.replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extraction_metadata(
    *,
    status: str,
    url: str,
    selector: Optional[str] = None,
    description_length: int = 0,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Build auditable extraction metadata for the source reference."""
    result: Dict[str, Any] = {
        "status": status,
        "detail_url": url,
        "method": "playwright_dom",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "description_length": description_length,
    }
    if selector:
        result["selector"] = selector
    if error:
        result["error"] = error
    return result


async def extract_job_detail(page: Page, url: str) -> Dict[str, Any]:
    """Extract a real job description from a canonical detail page."""
    allow_loopback = os.getenv("APP_ENV", "development").casefold() in {"development", "test"}
    validate_public_url(url, allow_loopback=allow_loopback)
    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    await page.wait_for_timeout(750)

    for selector in DESCRIPTION_SELECTORS:
        locator = page.locator(selector).first
        if await locator.count() == 0:
            continue
        try:
            text = clean_job_text(await locator.inner_text(timeout=5_000))
        except Exception:
            continue
        if len(text) >= 120:
            return {
                "job_description": text,
                "extraction": extraction_metadata(
                    status="success",
                    url=url,
                    selector=selector,
                    description_length=len(text),
                ),
            }

    try:
        text = clean_job_text(await page.locator("body").inner_text(timeout=5_000))
    except Exception as exc:
        raise ValueError(f"Could not read detail page body: {exc}") from exc

    if len(text) < 120:
        raise ValueError("Detail page did not contain a meaningful job description")

    return {
        "job_description": text,
        "extraction": extraction_metadata(
            status="success",
            url=url,
            selector="body",
            description_length=len(text),
        ),
    }
