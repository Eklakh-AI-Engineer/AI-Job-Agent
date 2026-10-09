from openpyxl import Workbook

from scripts.evaluate_human_benchmark import main


def test_human_benchmark_evaluator_writes_scoreboard(tmp_path, monkeypatch):
    workbook = tmp_path / "benchmark.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Evaluation ID", "Job ID", "Match Score", "Human Label"])
    ws.append(["EVAL-Q1-1", "J1", 95, "Exact Match"])
    ws.append(["EVAL-Q1-2", "J2", 70, "Related Match"])
    wb.save(workbook)

    out = tmp_path / "results"
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate_human_benchmark.py", str(workbook), "--output-dir", str(out)],
    )
    assert main() == 0
    assert (out / "AI_Predictions_v1.jsonl").exists()
    assert (out / "Evaluation_Results_v1.json").exists()
    scoreboard = (out / "MASTER_SCOREBOARD.md").read_text(encoding="utf-8")
    assert "Accuracy" in scoreboard
    assert "ndcg_at_5" in scoreboard


def test_adjudicated_final_gold_label_takes_precedence(tmp_path, monkeypatch):
    workbook = tmp_path / "adjudicated.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append([
        "Evaluation ID",
        "Job ID",
        "Match Score",
        "Human Label",
        "Final Gold Label",
        "Final Gold Score",
    ])
    ws.append(["Q-001-A", "J1", 90, "Strong Match", "No Match", 0])
    ws.append(["Q-001-B", "J2", 80, "No Match", "Strong Match", 4])
    wb.save(workbook)

    out = tmp_path / "adjudicated-results"
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate_human_benchmark.py", str(workbook), "--output-dir", str(out)],
    )
    assert main() == 0

    import json

    evaluation = json.loads((out / "Evaluation_Results_v1.json").read_text(encoding="utf-8"))
    predictions = [
        json.loads(line)
        for line in (out / "AI_Predictions_v1.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["human_label"] for row in predictions] == [0, 4]
    assert evaluation["status"]["human_verified"] is True
    assert evaluation["status"]["frozen"] is False
    assert evaluation["status"]["production_authoritative"] is False
    assert evaluation["dataset"]["human_label_column_selected"] == "Final Gold Label"
