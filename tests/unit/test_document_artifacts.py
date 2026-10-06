from pathlib import Path

from app.services.document_artifacts import build_artifacts
from app.services.document_storage import LocalFilesystemStorage, build_document_key


def test_build_artifacts_produces_valid_pdf_and_docx():
    artifacts = build_artifacts(
        "Ada Lovelace\n\nSUMMARY\nPython engineer\n\nSKILLS\nPython, PyTorch",
        doc_type="resume",
        user_id=1,
        job_id=2,
        version=1,
    )

    assert set(artifacts) == {"pdf", "docx"}
    assert artifacts["pdf"]["filename"].endswith(".pdf")
    assert artifacts["docx"]["filename"].endswith(".docx")
    assert artifacts["pdf"]["bytes"].startswith(b"%PDF")
    assert artifacts["docx"]["bytes"].startswith(b"PK")
    assert len(artifacts["pdf"]["sha256"]) == 64
    assert len(artifacts["docx"]["sha256"]) == 64


async def test_binary_storage_round_trip(tmp_path: Path):
    storage = LocalFilesystemStorage(str(tmp_path))
    key = build_document_key(1, 2, "resume", 1, "pdf")
    payload = b"%PDF-test"

    await storage.put_bytes(key, payload, "application/pdf")
    assert await storage.get_bytes(key) == payload
    assert (tmp_path / key).read_bytes() == payload
