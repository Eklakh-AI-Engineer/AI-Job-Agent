import json

from openpyxl import Workbook

from scripts.validate_job_mapping import main


def test_valid_job_mapping_writes_non_authoritative_manifest(tmp_path, monkeypatch):
    workbook = tmp_path / "benchmark.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Final Gold 500"
    ws.append(["Evaluation ID", "Job ID"])
    ws.append(["EVAL-001", "JOB-001"])
    ws.append(["EVAL-002", "JOB-002"])
    wb.save(workbook)

    export_hash = "a" * 64
    mapping = tmp_path / "mapping.csv"
    mapping.write_text(
        "benchmark_job_id,persisted_job_id,persisted_job_title,persisted_company,persisted_url,source_table,verified_at_utc,source_export_sha256\n"
        f"JOB-001,101,Backend Engineer,Example Co,https://example.com/jobs/101,job_postings,2026-10-09T10:00:00Z,{export_hash}\n"
        f"JOB-002,102,AI Engineer,Example Co,https://example.com/jobs/102,job_postings,2026-10-09T10:00:00Z,{export_hash}\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "mapping-manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_job_mapping.py",
            "--workbook", str(workbook),
            "--mapping", str(mapping),
            "--manifest", str(manifest),
        ],
    )

    assert main() == 0
    result = json.loads(manifest.read_text(encoding="utf-8"))
    assert result["unique_benchmark_jobs"] == 2
    assert result["unique_persisted_job_ids"] == 2
    assert result["production_authoritative"] is False
    assert result["status"] == "mapping_schema_validated_pending_independent_review"


def test_job_mapping_rejects_missing_benchmark_job(tmp_path, monkeypatch):
    workbook = tmp_path / "benchmark.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Final Gold 500"
    ws.append(["Job ID"])
    ws.append(["JOB-001"])
    ws.append(["JOB-002"])
    wb.save(workbook)

    mapping = tmp_path / "mapping.csv"
    mapping.write_text(
        "benchmark_job_id,persisted_job_id,persisted_job_title,persisted_company,persisted_url,source_table,verified_at_utc,source_export_sha256\n"
        + "JOB-001,101,Backend Engineer,Example Co,https://example.com/jobs/101,job_postings,2026-10-09T10:00:00Z,"
        + "a" * 64 + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_job_mapping.py",
            "--workbook", str(workbook),
            "--mapping", str(mapping),
            "--manifest", str(tmp_path / "mapping-manifest.json"),
        ],
    )

    try:
        main()
    except SystemExit as exc:
        assert "unmapped benchmark job IDs" in str(exc)
    else:
        raise AssertionError("incomplete mapping must fail")
