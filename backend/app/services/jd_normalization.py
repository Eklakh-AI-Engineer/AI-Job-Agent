"""Canonical JD requirement normalization.

This module converts source-provided structured fields into a stable, auditable
representation before persistence. It deliberately does not infer requirements
from free-form prose: inferred values must be produced by a separately
versioned extractor and are marked as such.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


SKILL_ALIASES: dict[str, str] = {
    "py torch": "pytorch",
    "pytorch": "pytorch",
    "python 3": "python",
    "python3": "python",
    "js": "javascript",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "ts": "typescript",
    "tf": "tensorflow",
    "postgres": "postgresql",
    "postgres db": "postgresql",
    "postgresql db": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "aws cloud": "aws",
    "gcp cloud": "gcp",
    "azure cloud": "azure",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "gen ai": "generative ai",
    "genai": "generative ai",
    "llms": "llm",
    "large language models": "llm",
    "rag": "retrieval augmented generation",
    "rest api": "rest",
    "restful api": "rest",
}


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize_skill(value: Any) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    key = re.sub(r"\s+", " ", cleaned.casefold())
    return SKILL_ALIASES.get(key, key)


def normalize_skill_list(values: Any) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        skill = normalize_skill(value)
        if skill and skill not in seen:
            result.append(skill)
            seen.add(skill)
    return result


def parse_experience_range(value: Any) -> dict[str, float | str | None]:
    """Parse common experience expressions while preserving source wording."""
    source = _clean(value)
    if not source:
        return {"source": None, "min_years": None, "max_years": None, "status": "missing"}

    text = source.casefold()
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    min_years = max_years = None

    if len(numbers) >= 2 and re.search(r"\b(?:to|[-–])\b|\d\s*[-–]\s*\d", text):
        min_years, max_years = numbers[0], numbers[1]
    elif numbers:
        min_years = numbers[0]
        if "+" in text or re.search(r"\b(?:at least|minimum|min)\b", text):
            max_years = None
        else:
            max_years = numbers[0]

    status = "explicit" if min_years is not None else "unparsed"
    return {
        "source": source,
        "min_years": min_years,
        "max_years": max_years,
        "status": status,
    }


def normalize_education(value: Any) -> dict[str, Any]:
    source = _clean(value)
    if not source:
        return {"source": None, "level": None, "fields": [], "status": "missing"}

    text = source.casefold()
    level = None
    if re.search(r"\b(ph\.d|doctorate|doctoral)\b", text):
        level = "doctorate"
    elif re.search(r"\b(master|m\.tech|mtech|mba|ms|m\.s\.)\b", text):
        level = "master"
    elif re.search(r"\b(bachelor|b\.tech|btech|b\.e\.|be\b|b\.s\.|bs\b)\b", text):
        level = "bachelor"
    elif re.search(r"\b(associate|diploma)\b", text):
        level = "associate_or_diploma"

    fields: list[str] = []
    field_aliases = {
        "computer science": "computer science",
        "computer engineering": "computer engineering",
        "information technology": "information technology",
        "data science": "data science",
        "artificial intelligence": "artificial intelligence",
        "machine learning": "machine learning",
        "electrical engineering": "electrical engineering",
    }
    for needle, canonical in field_aliases.items():
        if needle in text:
            fields.append(canonical)

    return {
        "source": source,
        "level": level,
        "fields": fields,
        "status": "explicit" if level or fields else "unparsed",
    }


def normalize_date(value: Any) -> dict[str, str | None]:
    source = _clean(value)
    if not source:
        return {"source": None, "iso": None, "status": "missing"}

    candidate = source.replace("Z", "+00:00")
    parsed: datetime | date | None = None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", source):
        parsed = date.fromisoformat(source)
    else:
        for parser in (
            lambda s: datetime.fromisoformat(s),
            lambda s: date.fromisoformat(s),
        ):
            try:
                parsed = parser(candidate)
                break
            except ValueError:
                continue

    if parsed is None:
        # Conservative support for common YYYY/MM/DD and DD-MM-YYYY feeds.
        for fmt in ("%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(source, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return {"source": source, "iso": None, "status": "invalid"}

    if isinstance(parsed, date) and not isinstance(parsed, datetime):
        iso = parsed.isoformat()
    else:
        iso = parsed.isoformat()
    return {"source": source, "iso": iso, "status": "explicit"}


def normalize_job_requirements(raw: dict[str, Any]) -> dict[str, Any]:
    """Return normalized fields plus auditable provenance metadata."""
    required = normalize_skill_list(raw.get("required_skills"))
    preferred = normalize_skill_list(raw.get("preferred_skills"))
    experience = parse_experience_range(raw.get("experience_requirement"))
    education = normalize_education(raw.get("education_requirement"))
    posted = normalize_date(raw.get("posted_date"))
    closing = normalize_date(raw.get("closing_date"))

    fields: dict[str, dict[str, Any]] = {
        "required_skills": {
            "value": required,
            "source": raw.get("required_skills"),
            "status": "explicit" if required else "missing",
            "inferred": False,
        },
        "preferred_skills": {
            "value": preferred,
            "source": raw.get("preferred_skills"),
            "status": "explicit" if preferred else "missing",
            "inferred": False,
        },
        "experience": {**experience, "inferred": False},
        "education": {**education, "inferred": False},
        "posted_date": {**posted, "inferred": False},
        "closing_date": {**closing, "inferred": False},
    }

    return {
        "required_skills": required,
        "preferred_skills": preferred,
        "experience_requirement": _clean(raw.get("experience_requirement")),
        "education_requirement": _clean(raw.get("education_requirement")),
        "posted_date": posted["iso"] or _clean(raw.get("posted_date")),
        "closing_date": closing["iso"] or _clean(raw.get("closing_date")),
        "normalization": {
            "version": "jd-normalization-v1",
            "status": "normalized",
            "fields": fields,
        },
    }
