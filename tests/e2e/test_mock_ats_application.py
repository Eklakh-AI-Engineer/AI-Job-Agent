"""Controlled ATS integration test.

Exercises the real Playwright form filler against a local HTTP server. No
external ATS and no real applicant data are involved.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.agents.application_bot import ApplicantData, PlaywrightFormFiller, SubmissionRequest


class MockATSHandler(BaseHTTPRequestHandler):
    submissions = 0

    def do_GET(self):  # noqa: N802
        body = b"""<!doctype html>
<html><body>
<form action="/" method="post">
<input id="first_name" name="first_name">
<input id="last_name" name="last_name">
<input id="email" name="email" type="email">
<input id="phone" name="phone" type="tel">
<input id="job_application_location" name="location">
<input id="resume" name="resume" type="file">
<input id="cover_letter" name="cover_letter" type="file">
<input name="urls[LinkedIn]">
<input name="urls[Website]">
<button id="submit_app" type="submit">Submit application</button>
</form>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        MockATSHandler.submissions += 1
        body = b"<html><body><h1>Application received</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@pytest.fixture
def mock_ats():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockATSHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    thread.join()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mock_ats_dry_run_never_submits(mock_ats, tmp_path: Path):
    MockATSHandler.submissions = 0
    resume = tmp_path / "resume.pdf"
    cover = tmp_path / "cover.pdf"
    resume.write_bytes(b"%PDF-mock-resume")
    cover.write_bytes(b"%PDF-mock-cover")

    applicant = ApplicantData(
        first_name="Test",
        last_name="Applicant",
        full_name="Test Applicant",
        email="test@example.invalid",
        location="Test City",
        resume_path=str(resume),
        cover_letter_path=str(cover),
    )
    result = await PlaywrightFormFiller(headless=True).run(
        SubmissionRequest(
            apply_url=mock_ats,
            applicant=applicant,
            dry_run=True,
            capture_evidence=False,
        )
    )

    assert result.success is True
    assert result.dry_run is True
    assert "resume" in result.fields_filled
    assert "cover_letter" in result.fields_filled
    assert MockATSHandler.submissions == 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mock_ats_real_submit_records_one_submission(mock_ats, tmp_path: Path):
    MockATSHandler.submissions = 0
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-mock-resume")

    applicant = ApplicantData(
        first_name="Test",
        last_name="Applicant",
        full_name="Test Applicant",
        email="test@example.invalid",
        resume_path=str(resume),
    )
    result = await PlaywrightFormFiller(headless=True).run(
        SubmissionRequest(
            apply_url=mock_ats,
            applicant=applicant,
            dry_run=False,
            capture_evidence=False,
        )
    )

    assert result.success is True
    assert result.dry_run is False
    assert MockATSHandler.submissions == 1
