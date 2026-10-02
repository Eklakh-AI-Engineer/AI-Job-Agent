from typing import Optional
from datetime import datetime, timezone
from backend.jobs.models import Job


def normalize(raw: dict, source_name: str) -> Job:
    def strip_and_title(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        return str(val).strip().title()

    def strip_val(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        return str(val).strip()

    def normalize_url(val: Optional[str]) -> Optional[str]:
        val = strip_val(val)
        if not val:
            return val
        if not val.startswith("http://") and not val.startswith("https://"):
            return "https://" + val
        return val

    title = strip_and_title(raw.get("title"))
    company = strip_and_title(raw.get("company"))
    location = strip_val(raw.get("location"))
    job_url = normalize_url(raw.get("url")) or ""
    application_url = normalize_url(raw.get("apply"))

    return Job(
        source=source_name,
        source_job_id=str(raw.get("source_id", "")),
        company=company,
        title=title,
        location=location,
        work_mode=strip_val(raw.get("mode")),
        job_url=job_url,
        application_url=application_url,
        discovered_at=datetime.now(timezone.utc),
        raw_source_reference=raw,
    )
