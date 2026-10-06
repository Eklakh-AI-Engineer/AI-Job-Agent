"""Unit coverage for real JD extraction helpers."""

from app.services.job_detail_extraction import clean_job_text, extraction_metadata


def test_clean_job_text_removes_empty_lines_and_normalizes_whitespace():
    raw = "  Responsibilities:\n\n  Build   APIs  \n\tOwn reliability.  "
    assert clean_job_text(raw) == "Responsibilities:\nBuild APIs\nOwn reliability."


def test_extraction_metadata_is_auditable():
    meta = extraction_metadata(
        status="success",
        url="https://example.com/jobs/123",
        selector=".job-description",
        description_length=321,
    )
    assert meta["status"] == "success"
    assert meta["detail_url"].endswith("/123")
    assert meta["method"] == "playwright_dom"
    assert meta["selector"] == ".job-description"
    assert meta["description_length"] == 321


def test_extraction_metadata_records_failure_reason():
    meta = extraction_metadata(
        status="failure",
        url="https://example.com/jobs/123",
        error="missing description",
    )
    assert meta["status"] == "failure"
    assert meta["error"] == "missing description"
