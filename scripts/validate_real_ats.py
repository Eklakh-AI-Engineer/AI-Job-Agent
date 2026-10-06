"""Validate ATS selector maps against real public application pages.

This script is intentionally dry-run only. It may navigate to public ATS
application pages and fill disposable values in-browser, but it never clicks
a submit button and never sends an application.

Usage:
  python scripts/validate_real_ats.py --url "https://boards.greenhouse.io/..."
  python scripts/validate_real_ats.py --url "https://jobs.lever.co/..."
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.application_bot import ApplicantData, PlaywrightFormFiller, SubmissionRequest
from app.agents.ats_config import resolve_ats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", action="append", required=True)
    return parser.parse_args()


async def validate(url: str) -> dict:
    ats = resolve_ats(url)
    with tempfile.TemporaryDirectory(prefix="ats-validation-") as tmp:
        resume = Path(tmp) / "validation-resume.pdf"
        resume.write_bytes(b"%PDF-1.4\n% dry-run validation artifact\n")
        applicant = ApplicantData(
            first_name="ATS",
            last_name="Validation",
            full_name="ATS Validation",
            email="ats-validation@example.invalid",
            phone="0000000000",
            location="Validation City",
            linkedin="https://example.invalid/linkedin",
            website="https://example.invalid",
            resume_path=str(resume),
        )
        result = await PlaywrightFormFiller(headless=True).run(
            SubmissionRequest(
                apply_url=url,
                applicant=applicant,
                dry_run=True,
                capture_evidence=False,
                timeout_ms=45000,
                ats=ats,
            )
        )
    return {
        "url": url,
        "ats": ats.name,
        "success": result.success,
        "dry_run": result.dry_run,
        "fields_filled": result.fields_filled,
        "error": result.error,
        "message": result.message,
    }


async def main() -> int:
    results = [await validate(url) for url in parse_args().url]
    for result in results:
        print(result)
    return 0 if all(r["success"] and r["dry_run"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
