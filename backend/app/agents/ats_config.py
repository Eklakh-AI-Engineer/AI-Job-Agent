"""
backend/app/agents/ats_config.py

Config-driven ATS selector maps for the application bot.

Each supported ATS (Applicant Tracking System) has different form markup.
Selectors are declared here as data, not code, so adding a new ATS does not
require touching the bot logic.

Selectors are intentionally listed as ordered fallbacks: the bot tries each
in turn and uses the first that resolves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class ATSConfig:
    """Selector configuration for one ATS provider."""

    name: str
    #: Host substrings that identify this ATS.
    host_patterns: List[str] = field(default_factory=list)
    #: Selectors used to detect the application form has loaded.
    form_ready: List[str] = field(default_factory=list)
    first_name: List[str] = field(default_factory=list)
    last_name: List[str] = field(default_factory=list)
    full_name: List[str] = field(default_factory=list)
    email: List[str] = field(default_factory=list)
    phone: List[str] = field(default_factory=list)
    location: List[str] = field(default_factory=list)
    resume_upload: List[str] = field(default_factory=list)
    cover_letter_upload: List[str] = field(default_factory=list)
    linkedin: List[str] = field(default_factory=list)
    website: List[str] = field(default_factory=list)
    submit_button: List[str] = field(default_factory=list)
    #: Human-readable notes about this provider's constraints.
    notes: str = ""


GREENHOUSE = ATSConfig(
    name="greenhouse",
    host_patterns=["greenhouse.io"],
    form_ready=[
        "#application_form",
        "form[action*='application']",
        "[data-testid='application-form']",
    ],
    first_name=["#first_name", "input[name='first_name']"],
    last_name=["#last_name", "input[name='last_name']"],
    email=["#email", "input[name='email']"],
    phone=["#phone", "input[name='phone']"],
    location=["#job_application_location", "input[name='location']"],
    resume_upload=[
        "input[type='file'][name='resume']",
        "#resume",
        "input[type='file']",
    ],
    cover_letter_upload=[
        "input[type='file'][name='cover_letter']",
        "#cover_letter",
    ],
    linkedin=["input[name='urls[LinkedIn]']", "input[name*='linkedin' i]"],
    website=["input[name='urls[Website]']", "input[name*='website' i]"],
    submit_button=[
        "#submit_app",
        "button[type='submit']",
        "input[type='submit']",
    ],
    notes="Greenhouse allows pre-fill and upload; final submission is user-gated.",
)

LEVER = ATSConfig(
    name="lever",
    host_patterns=["lever.co", "jobs.lever.co"],
    form_ready=[
        "form.application-form",
        "[data-qa='application-form']",
        "form",
    ],
    first_name=["input[name='name']"],
    full_name=["input[name='name']"],
    email=["input[name='email']"],
    phone=["input[name='phone']"],
    location=["input[name='location']"],
    resume_upload=[
        "input[type='file'][name='resume']",
        "input[type='file']",
    ],
    cover_letter_upload=["input[type='file'][name='cover_letter']"],
    linkedin=["input[name='urls[LinkedIn]']"],
    website=["input[name='urls[Portfolio]']", "input[name*='website' i]"],
    submit_button=["button[type='submit']", ".postings-btn"],
    notes="Lever often single-name field; splits name if a full_name selector is used.",
)

WORKDAY = ATSConfig(
    name="workday",
    host_patterns=["myworkdayjobs.com", "workday.com"],
    form_ready=[
        "[data-automation-id='applyFlowPage']",
        "[data-automation-id='applicationForm']",
    ],
    first_name=["input[data-automation-id='legalNameSection_firstName']"],
    last_name=["input[data-automation-id='legalNameSection_lastName']"],
    email=["input[data-automation-id='email']"],
    phone=["input[data-automation-id='phone-number']"],
    location=["input[data-automation-id='addressSection_city']"],
    resume_upload=[
        "input[data-automation-id='file-upload-input-ref']",
        "input[type='file']",
    ],
    cover_letter_upload=["input[data-automation-id='coverLetter']"],
    linkedin=["input[data-automation-id='linkedin']"],
    website=["input[data-automation-id='website']"],
    submit_button=[
        "button[data-automation-id='bottom-navigation-next-button']",
        "button[data-automation-id='submitButton']",
    ],
    notes=(
        "Workday is a multi-step, JS-driven flow. Automation is best-effort and "
        "should always fall back to a manual link."
    ),
)

GENERIC = ATSConfig(
    name="generic",
    host_patterns=[],  # matches anything as the fallback
    form_ready=["form"],
    first_name=["input[name*='first' i]", "input[id*='first' i]"],
    last_name=["input[name*='last' i]", "input[id*='last' i]"],
    full_name=["input[name*='name' i]", "input[id*='name' i]"],
    email=["input[type='email']", "input[name*='email' i]", "input[id*='email' i]"],
    phone=["input[type='tel']", "input[name*='phone' i]", "input[id*='phone' i]"],
    location=["input[name*='location' i]", "input[name*='city' i]"],
    resume_upload=["input[type='file'][name*='resume' i]", "input[type='file']"],
    cover_letter_upload=["input[type='file'][name*='cover' i]"],
    linkedin=["input[name*='linkedin' i]"],
    website=["input[name*='website' i]", "input[name*='portfolio' i]"],
    submit_button=["button[type='submit']", "input[type='submit']"],
    notes="Heuristic fallback for ATS providers without a dedicated config.",
)

# Ordered most-specific first; GENERIC is the fallback.
ATS_CONFIGS: List[ATSConfig] = [GREENHOUSE, LEVER, WORKDAY]


def resolve_ats(url: str) -> ATSConfig:
    """
    Resolve the ATS config for an application URL.

    Falls back to GENERIC when no host pattern matches.
    """
    if not url:
        return GENERIC
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:  # noqa: BLE001
        host = url.lower()
    for config in ATS_CONFIGS:
        if any(pattern in host for pattern in config.host_patterns):
            return config
    return GENERIC


def host_of(url: str) -> str:
    """Return the lowercased hostname of a URL (or '' on failure)."""
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:  # noqa: BLE001
        return ""
