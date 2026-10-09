import json

from scripts.ranking_regression_gate import main


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_gate_blocks_synthetic_baseline_by_default(tmp_path, monkeypatch, capsys):
    baseline = tmp_path / "baseline.json"
    latest = tmp_path / "latest.json"
    policy = tmp_path / "policy.json"
    base = {
        "benchmark": "golden_job_ranking_v1",
        "production_authoritative": False,
        "final_workbook_sha256": "a" * 64,
        "metrics": {
            "precision_at_5": 0.5,
            "recall_at_5": 0.8,
            "ndcg_at_5": 0.7,
            "mrr": 0.6,
        },
    }
    write_json(baseline, base)
    write_json(latest, base)
    write_json(policy, {
        "precision_at_5": 0.02,
        "recall_at_5": 0.02,
        "ndcg_at_5": 0.02,
        "mrr": 0.02,
    })
    monkeypatch.setattr(
        "sys.argv",
        ["ranking_regression_gate.py", "--baseline", str(baseline), "--latest", str(latest), "--policy", str(policy)],
    )
    assert main() == 2
    assert "not marked production_authoritative=true" in capsys.readouterr().out


def test_gate_allows_explicit_synthetic_plumbing_only(tmp_path, monkeypatch, capsys):
    baseline = tmp_path / "baseline.json"
    latest = tmp_path / "latest.json"
    base = {
        "benchmark": "golden_job_ranking_v1",
        "production_authoritative": False,
        "final_workbook_sha256": "b" * 64,
        "metrics": {
            "precision_at_5": 0.5,
            "recall_at_5": 0.8,
            "ndcg_at_5": 0.7,
            "mrr": 0.6,
        },
    }
    write_json(baseline, base)
    write_json(latest, base)
    monkeypatch.setattr(
        "sys.argv",
        ["ranking_regression_gate.py", "--baseline", str(baseline), "--latest", str(latest), "--allow-non-production-baseline"],
    )
    assert main() == 0
    assert "not a production ranking-quality gate" in capsys.readouterr().out


def test_gate_requires_matching_production_version_and_fingerprint(tmp_path, monkeypatch):
    baseline = tmp_path / "baseline.json"
    latest = tmp_path / "latest.json"
    metrics = {
        "precision_at_5": 0.5,
        "recall_at_5": 0.8,
        "ndcg_at_5": 0.7,
        "mrr": 0.6,
    }
    base = {
        "benchmark": "golden_job_ranking_v1",
        "production_authoritative": True,
        "dataset_sha256": "c" * 64,
        "ranking_version": "hybrid-v1",
        "metrics": metrics,
    }
    write_json(baseline, base)
    latest_doc = dict(base)
    latest_doc["ranking_version"] = "hybrid-v2"
    write_json(latest, latest_doc)
    monkeypatch.setattr(
        "sys.argv",
        ["ranking_regression_gate.py", "--baseline", str(baseline), "--latest", str(latest)],
    )
    assert main() == 2
