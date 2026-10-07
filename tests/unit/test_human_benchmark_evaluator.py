from openpyxl import Workbook

from scripts.evaluate_human_benchmark import main


def test_human_benchmark_evaluator_writes_scoreboard(tmp_path, monkeypatch):
    workbook = tmp_path / "benchmark.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Sample ID", "Query ID", "Job ID", "AI Score", "AI Label", "Human Label"])
    ws.append(["S1", "Q1", "J1", 95, "Exact Match", "Exact Match"])
    ws.append(["S2", "Q1", "J2", 70, "Related Match", "Related Match"])
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
