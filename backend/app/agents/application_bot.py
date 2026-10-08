"""
backend/app/agents/application_bot.py

Playwright-based application form filler.

Design goals:
- **Testable**: the browser work lives behind :class:`ApplicationFormFiller`,
  so orchestration can be unit-tested with a fake and no real browser.
- **Human-gated**: ``dry_run`` defaults to True; the bot never clicks submit
  unless explicitly told to.
- **ATS-aware**: selectors come from :mod:`app.agents.ats_config`.

The Playwright import is lazy so this module (and its consumers) can be
imported in environments without a browser installed.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from app.agents.ats_config import ATSConfig, resolve_ats
from app.core.ssrf import validate_public_url
from app.core.upload_security import validate_upload

logger = logging.getLogger(__name__)


@dataclass
class ApplicantData:
    """The public applicant fields used to pre-fill an application form."""

    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    website: str = ""
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None


@dataclass
class SubmissionRequest:
    """A request to pre-fill (and optionally submit) an application."""

    apply_url: str
    applicant: ApplicantData
    dry_run: bool = True
    capture_evidence: bool = True
    evidence_dir: str = "data/evidence"
    timeout_ms: int = 30000
    ats: Optional[ATSConfig] = None

    def __post_init__(self):
        if self.ats is None:
            self.ats = resolve_ats(self.apply_url)


@dataclass
class SubmissionResult:
    """Outcome of a pre-fill/submit attempt."""

    success: bool
    dry_run: bool
    ats: str
    apply_url: str
    fields_filled: Dict[str, str] = field(default_factory=dict)
    evidence_paths: List[str] = field(default_factory=list)
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "ats": self.ats,
            "apply_url": self.apply_url,
            "fields_filled": self.fields_filled,
            "evidence_paths": self.evidence_paths,
            "message": self.message,
            "error": self.error,
        }


class ApplicationFormFiller(Protocol):
    """Protocol implemented by the real bot and by test fakes."""

    async def run(self, request: SubmissionRequest) -> SubmissionResult:
        ...


def _is_placeholder(value: str) -> bool:
    return value is None or value == ""


class PlaywrightFormFiller:
    """
    Real browser form filler using Playwright.

    Only ``run`` is public. The Playwright API is used lazily.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def _fill_first(self, page, selectors: List[str], value: str) -> Optional[str]:
        """Fill the first selector that resolves. Returns the selector used."""
        if _is_placeholder(value):
            return None
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element is None:
                    continue
                await element.fill(value)
                return selector
            except Exception:  # noqa: BLE001 - selector may not match the page
                continue
        return None

    async def _upload_first(self, page, selectors: List[str], path: Optional[str]) -> Optional[str]:
        if not path or not os.path.isfile(path):
            return None
        try:
            safe_path = validate_upload(path)
        except Exception as exc:
            logger.warning("Rejected upload %s: %s", path, exc)
            return None
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element is None:
                    continue
                await element.set_input_files(str(safe_path))
                return selector
            except Exception:  # noqa: BLE001
                continue
        return None

    async def _capture(self, page, evidence_dir: str, ats: str) -> List[str]:
        os.makedirs(evidence_dir, exist_ok=True)
        path = os.path.join(evidence_dir, f"{ats}_{int(time.time())}.png")
        try:
            await page.screenshot(path=path, full_page=True)
            return [path]
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Screenshot capture failed: {exc}")
            return []

    async def run(self, request: SubmissionRequest) -> SubmissionResult:
        try:
            from playwright.async_api import async_playwright  # lazy import
        except ImportError as exc:  # pragma: no cover - optional dependency
            return SubmissionResult(
                success=False,
                dry_run=request.dry_run,
                ats=request.ats.name,
                apply_url=request.apply_url,
                error=f"playwright not installed: {exc}",
            )

        allow_loopback = os.getenv("APP_ENV", "development").casefold() in {"development", "test"}
        validate_public_url(request.apply_url, allow_loopback=allow_loopback)
        ats = request.ats
        applicant = request.applicant
        fields_filled: Dict[str, str] = {}
        evidence: List[str] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
                context = await browser.new_context()
                page = await context.new_page()
                try:
                    await page.goto(request.apply_url, wait_until="domcontentloaded",
                                    timeout=request.timeout_ms)

                    # Wait for the form to appear. Public Lever job pages expose
                    # the application form behind an Apply link; resolve that page
                    # before probing selectors. This remains dry-run safe because
                    # no submit control is clicked here.
                    form_visible = False
                    for selector in ats.form_ready:
                        try:
                            await page.wait_for_selector(selector, timeout=2500)
                            form_visible = True
                            break
                        except Exception:  # noqa: BLE001
                            continue

                    if not form_visible:
                        apply_link = page.get_by_role("link", name="apply for this job")
                        if await apply_link.count():
                            await apply_link.first.click()
                            await page.wait_for_load_state("domcontentloaded")
                            for selector in ats.form_ready:
                                try:
                                    await page.wait_for_selector(selector, timeout=7000)
                                    form_visible = True
                                    break
                                except Exception:  # noqa: BLE001
                                    continue

                    if not form_visible:
                        apply_button = page.get_by_role("button", name="apply")
                        if await apply_button.count():
                            await apply_button.first.click()
                            await page.wait_for_load_state("domcontentloaded")
                            for selector in ats.form_ready:
                                try:
                                    await page.wait_for_selector(selector, timeout=7000)
                                    form_visible = True
                                    break
                                except Exception:  # noqa: BLE001
                                    continue

                    if not form_visible:
                        raise RuntimeError(
                            f"ATS application form did not load for {request.apply_url}"
                        )

                    # Fill text fields
                    simple_fields = {
                        "first_name": (ats.first_name, applicant.first_name),
                        "last_name": (ats.last_name, applicant.last_name),
                        "full_name": (ats.full_name, applicant.full_name),
                        "email": (ats.email, applicant.email),
                        "phone": (ats.phone, applicant.phone),
                        "location": (ats.location, applicant.location),
                        "linkedin": (ats.linkedin, applicant.linkedin),
                        "website": (ats.website, applicant.website),
                    }
                    for field_name, (selectors, value) in simple_fields.items():
                        used = await self._fill_first(page, selectors, value)
                        if used:
                            fields_filled[field_name] = used

                    # Upload documents
                    if applicant.resume_path:
                        used = await self._upload_first(page, ats.resume_upload, applicant.resume_path)
                        if used:
                            fields_filled["resume"] = used
                    if applicant.cover_letter_path:
                        used = await self._upload_first(
                            page, ats.cover_letter_upload, applicant.cover_letter_path
                        )
                        if used:
                            fields_filled["cover_letter"] = used

                    if request.capture_evidence:
                        evidence = await self._capture(page, request.evidence_dir, ats.name)

                    if request.dry_run:
                        return SubmissionResult(
                            success=True,
                            dry_run=True,
                            ats=ats.name,
                            apply_url=request.apply_url,
                            fields_filled=fields_filled,
                            evidence_paths=evidence,
                            message="Dry run: form pre-filled, not submitted.",
                        )

                    # Real submission
                    submitted = False
                    for selector in ats.submit_button:
                        try:
                            btn = await page.query_selector(selector)
                            if btn is None:
                                continue
                            await btn.click()
                            submitted = True
                            break
                        except Exception:  # noqa: BLE001
                            continue

                    if not submitted:
                        return SubmissionResult(
                            success=False,
                            dry_run=False,
                            ats=ats.name,
                            apply_url=request.apply_url,
                            fields_filled=fields_filled,
                            evidence_paths=evidence,
                            error="Submit button not found",
                        )

                    return SubmissionResult(
                        success=True,
                        dry_run=False,
                        ats=ats.name,
                        apply_url=request.apply_url,
                        fields_filled=fields_filled,
                        evidence_paths=evidence,
                        message="Application submitted.",
                    )
                finally:
                    await context.close()
                    await browser.close()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Application bot failed")
            return SubmissionResult(
                success=False,
                dry_run=request.dry_run,
                ats=ats.name,
                apply_url=request.apply_url,
                fields_filled=fields_filled,
                evidence_paths=evidence,
                error=str(exc),
            )


def get_default_form_filler() -> ApplicationFormFiller:
    """Return the default (Playwright) form filler."""
    from app.core.config import get_settings

    settings = get_settings()
    return PlaywrightFormFiller(headless=settings.playwright_headless)
