from pathlib import Path

import pytest

from app.core.upload_security import UnsafeUpload, validate_upload


def test_accepts_pdf(tmp_path: Path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"%PDF-1.7 fake")
    assert validate_upload(str(path)) == path


def test_accepts_docx_signature(tmp_path: Path):
    path = tmp_path / "resume.docx"
    path.write_bytes(b"PK\x03\x04fake")
    assert validate_upload(str(path)) == path


def test_rejects_wrong_extension(tmp_path: Path):
    path = tmp_path / "resume.exe"
    path.write_bytes(b"MZfake")
    with pytest.raises(UnsafeUpload):
        validate_upload(str(path))


def test_rejects_signature_mismatch(tmp_path: Path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"not a pdf")
    with pytest.raises(UnsafeUpload):
        validate_upload(str(path))
