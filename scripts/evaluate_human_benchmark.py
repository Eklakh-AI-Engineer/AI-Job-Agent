#!/usr/bin/env python3
"""Evaluate the human-labeled Excel benchmark and build the master scoreboard."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ALIASES = {
    "sample_id": ("sampleid", "caseid", "rowid", "id"),
    "query_id": ("queryid", "evaluationid"),
    "job_id": ("jobid", "candidateid"),
    "query": ("querytext", "searchquery", "userquery"),
    "ai_label": ("ailabel", "aimatchlabel", "predictedlabel", "modellabel"),
    "ai_score": ("aiscore", "aimatchscore", "matchscore", "predictedscore"),
    "human_label": ("humanlabel", "humanrelevance", "humanmatchlabel", "goldlabel", "finalchosenlabel"),
    "human_score": ("humanscore", "humanrelevancescore", "humanmatchscore"),
    "ai_recommendation": ("airecommendation", "predictedrecommendation"),
    "human_recommendation": ("humanrecommendation", "goldrecommendation"),
}

LABELS = {
    "exact": 4, "exactmatch": 4, "direct": 3, "directmatch": 3,
    "highpriority": 3, "apply": 3,
    "match": 3,
    "related": 2, "relatedmatch": 2, "partial": 2, "partialmatch": 2,
    "review": 2, "reasonable": 2, "strong": 4, "strongmatch": 4, "weakmatch": 2,
    "borderline": 1, "nomatch": 0, "notrelevant": 0, "negative": 0, "reject": 0, "lowfit": 0,
    "uncertain": 0, "unknown": 0,
}

def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())

def pick(headers: list[str], key: str) -> str | None:
    normalized = {norm(h): h for h in headers}
    # Prefer adjudicated gold over the original first-pass human annotation.
    preferred = {
        "human_label": ("finalgoldlabel", "finalchosenlabel", "adjudicatedlabel", "humanlabel", "humanrelevance", "humanmatchlabel", "goldlabel"),
        "human_score": ("finalgoldscore", "finalchosenscore", "humanscore", "humanrelevancescore", "humanmatchscore"),
    }
    for alias in preferred.get(key, ()):
        if alias in normalized:
            return normalized[alias]
    if key in normalized:
        return normalized[key]
    for alias in ALIASES.get(key, ()):
        if alias in normalized:
            return normalized[alias]
    return None

def as_label(value: Any) -> int:
    if value is None or str(value).strip() == "":
        raise ValueError("empty label")
    try:
        number = float(value)
        if number.is_integer() and 0 <= number <= 4:
            return int(number)
    except (TypeError, ValueError):
        pass
    key = norm(value)
    if key in LABELS:
        return LABELS[key]
    for token, label in LABELS.items():
        if token in key:
            return label
    raise ValueError(f"unsupported label: {value!r}")

def canonical_query_id(value: Any) -> str:
    """Normalize an encoded evaluation identifier into a query group when possible."""
    text = str(value or "").strip()
    match = re.search(r"(?:^|[-_ ])(?:query|q)[-_ ]*(\d+)(?:[-_ ]|$)", text, re.I)
    if match:
        return f"Q-{int(match.group(1)):03d}"
    return text

def as_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0

def macro_prf(y_true: list[int], y_pred: list[int]) -> tuple[float, float, float]:
    classes = sorted(set(y_true) | set(y_pred))
    values = []
    for cls in classes:
        tp = sum(a == cls and p == cls for a, p in zip(y_true, y_pred))
        fp = sum(a != cls and p == cls for a, p in zip(y_true, y_pred))
        fn = sum(a == cls and p != cls for a, p in zip(y_true, y_pred))
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall)
        values.append((precision, recall, f1))
    return tuple(sum(v[i] for v in values) / len(values) for i in range(3))

def kappa(y_true: list[int], y_pred: list[int], weighted: bool = False) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    if not labels:
        return 0.0
    n = len(y_true)
    true_counts = Counter(y_true)
    pred_counts = Counter(y_pred)
    span = max(labels) - min(labels) or 1
    observed = 0.0
    expected = 0.0
    for a, p in zip(y_true, y_pred):
        d = abs(a - p) / span
        observed += d * d if weighted else float(a != p)
    for a in labels:
        for p in labels:
            d = abs(a - p) / span
            weight = d * d if weighted else float(a != p)
            expected += (true_counts[a] / n) * (pred_counts[p] / n) * weight
    return 1.0 - safe_div(observed / n, expected)

def ndcg(values: list[int], k: int) -> float:
    def dcg(xs: list[int]) -> float:
        return sum((2 ** x - 1) / math.log2(i + 2) for i, x in enumerate(xs))
    return safe_div(dcg(values[:k]), dcg(sorted(values, reverse=True)[:k]))

def ranking_metrics(groups: dict[str, list[dict[str, Any]]], k: int = 5) -> dict[str, float]:
    rows = []
    for group in groups.values():
        if len(group) < 2:
            continue
        ranked = sorted(
            enumerate(group),
            key=lambda pair: (
                pair[1]["ai_score"] is None,
                -(pair[1]["ai_score"] if pair[1]["ai_score"] is not None else pair[1]["ai_label"]),
                pair[0],
            ),
        )
        relevance = [item["human_label"] for _, item in ranked]
        total = sum(x > 1 for x in relevance)
        top = relevance[:k]
        rr = 0.0
        for rank, value in enumerate(relevance, 1):
            if value > 1:
                rr = 1.0 / rank
                break
        rows.append({
            "precision_at_5": safe_div(sum(x > 1 for x in top), k),
            "recall_at_5": safe_div(sum(x > 1 for x in top), total),
            "ndcg_at_5": ndcg(relevance, k),
            "mrr": rr,
        })
    if not rows:
        return {}
    return {key: round(sum(r[key] for r in rows) / len(rows), 4) for key in rows[0]}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evaluation/results_v1"))
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()

    if not args.workbook.exists():
        raise SystemExit(f"Workbook not found: {args.workbook}")

    raw = args.workbook.read_bytes()
    workbook_sha = hashlib.sha256(raw).hexdigest()
    wb = load_workbook(args.workbook, read_only=True, data_only=True)
    ws = wb["Benchmark Data"] if "Benchmark Data" in wb.sheetnames else wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise SystemExit("Workbook is empty")

    headers = [str(x or "").strip() for x in rows[0]]
    columns = {key: pick(headers, key) for key in ALIASES}
    missing = [key for key in ("query_id", "job_id", "human_label") if not columns[key]]
    if not columns["ai_label"] and not columns["ai_score"]:
        missing.append("ai_label_or_ai_score")
    if missing:
        raise SystemExit(
            "Required benchmark columns missing: "
            + ", ".join(missing)
            + "\nDetected headers: "
            + ", ".join(headers)
        )

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for excel_row, values in enumerate(rows[1:], start=2):
        if not any(v is not None and str(v).strip() for v in values):
            continue
        raw_record = {h: values[i] if i < len(values) else None for i, h in enumerate(headers)}
        try:
            human_label = as_label(raw_record[columns["human_label"]])
            ai_label = (
                as_label(raw_record[columns["ai_label"]])
                if columns["ai_label"] and raw_record[columns["ai_label"]] not in (None, "")
                else int(round(as_float(raw_record[columns["ai_score"]]) / 100 * 3))
            )
            ai_score = as_float(raw_record[columns["ai_score"]]) if columns["ai_score"] else None
            job_id = str(raw_record[columns["job_id"]]).strip()
            query_id = canonical_query_id(raw_record[columns["query_id"]])
            if str(query_id).upper().startswith("EVAL-"):
                query_id = job_id
            if not query_id or not job_id:
                raise ValueError("query_id and job_id are required")
        except (TypeError, ValueError) as exc:
            errors.append(f"row {excel_row}: {exc}")
            continue

        records.append({
            "sample_id": (
                str(raw_record[columns["sample_id"]]).strip()
                if columns["sample_id"] and raw_record[columns["sample_id"]] not in (None, "")
                else f"ROW-{excel_row}"
            ),
            "query_id": query_id,
            "job_id": job_id,
            "query": str(raw_record[columns["query"]]).strip() if columns["query"] else None,
            "ai_label": ai_label,
            "ai_score": ai_score,
            "human_label": human_label,
            "human_score": as_float(raw_record[columns["human_score"]]) if columns["human_score"] else None,
            "ai_recommendation": raw_record[columns["ai_recommendation"]] if columns["ai_recommendation"] else None,
            "human_recommendation": raw_record[columns["human_recommendation"]] if columns["human_recommendation"] else None,
            "source_row": excel_row,
        })

    if errors:
        raise SystemExit("Benchmark parsing failed:\n" + "\n".join(errors[:20]))

    if any(r["human_label"] not in {0, 1, 2, 3, 4} for r in records):
        raise SystemExit("Human labels must use canonical ordinal values 0-4.")

    y_true = [r["human_label"] for r in records]
    y_pred = [r["ai_label"] for r in records]
    precision, recall, f1 = macro_prf(y_true, y_pred)
    binary_true = [x > 1 for x in y_true]
    binary_pred = [x > 1 for x in y_pred]
    tp = sum(p and a for p, a in zip(binary_pred, binary_true))
    fp = sum(p and not a for p, a in zip(binary_pred, binary_true))
    fn = sum(not p and a for p, a in zip(binary_pred, binary_true))
    tn = sum(not p and not a for p, a in zip(binary_pred, binary_true))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["query_id"]].append(record)

    selected_human_label_header = columns["human_label"] or ""
    has_final_gold = norm(selected_human_label_header) == "finalgoldlabel"
    frozen_final_gold = (
        has_final_gold
        and workbook_sha == "ce65bdb07b9724b9851ac91da578a5bce86a0d01715b226cd2ebecd0d737273e"
    )
    evaluation = {
        "dataset": {
            "workbook": str(args.workbook),
            "sha256": workbook_sha,
            "rows_evaluated": len(records),
            "query_groups": len(groups),
            "human_labels_present": True,
            "human_label_column_selected": selected_human_label_header,
        },
        "classification": {
            "accuracy": round(safe_div(sum(a == p for a, p in zip(y_true, y_pred)), len(records)), 4),
            "macro_precision": round(precision, 4),
            "macro_recall": round(recall, 4),
            "macro_f1": round(f1, 4),
            "confusion_matrix_binary_relevant": {
                "tn": tn, "fp": fp, "fn": fn, "tp": tp, "threshold": 2
            },
        },
        "agreement": {
            "exact_agreement": round(safe_div(sum(a == p for a, p in zip(y_true, y_pred)), len(records)), 4),
            "within_one_label": round(safe_div(sum(abs(a - p) <= 1 for a, p in zip(y_true, y_pred)), len(records)), 4),
            "cohen_kappa": round(kappa(y_true, y_pred), 4),
            "weighted_kappa_quadratic": round(kappa(y_true, y_pred, weighted=True), 4),
        },
        "ranking": ranking_metrics(groups),
        "status": {
            "human_verified": has_final_gold,
            "frozen": frozen_final_gold,
            "real_persisted_jobs": False,
            "production_authoritative": False,
            "validated": False,
            "promotion_note": (
                "Human-gold labels are selected, but production promotion is blocked until real persisted-job mapping and runtime-ranker baseline evidence exist."
                if has_final_gold
                else "This workbook does not contain the adjudicated Final Gold Label column; the evaluator fell back to first-pass labels. Use the frozen Human_Gold_Final_v1 artifact before claiming human-verified benchmark results."
            ),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "AI_Predictions_v1.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records),
        encoding="utf-8",
    )
    (args.output_dir / "Evaluation_Results_v1.json").write_text(
        json.dumps(evaluation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    status = "human_verified_frozen_synthetic_pending_job_mapping" if frozen_final_gold else "human_verified_not_frozen" if has_final_gold else "first_pass_labels_only_not_adjudicated"
    scoreboard = [
        "# Master Scoreboard v1",
        "",
        f"Status: {status}",
        "",
        "## Dataset",
        f"- Rows evaluated: {len(records)}",
        f"- Query groups: {len(groups)}",
        f"- Workbook SHA-256: {workbook_sha}",
        f"- Human-label column selected: {selected_human_label_header}",
        f'- Human-gold verified: {evaluation["status"]["human_verified"]}',
        f'- Frozen final artifact: {evaluation["status"]["frozen"]}',
        f'- Production authoritative: {evaluation["status"]["production_authoritative"]}',
        "",
        "## Matching / Classification",
        f"- Accuracy: {evaluation['classification']['accuracy']:.4f}",
        f"- Macro Precision: {precision:.4f}",
        f"- Macro Recall: {recall:.4f}",
        f"- Macro F1: {f1:.4f}",
        "",
        "## Human Agreement",
        f"- Exact agreement: {evaluation['agreement']['exact_agreement']:.4f}",
        f"- ±1 label agreement: {evaluation['agreement']['within_one_label']:.4f}",
        f"- Cohen's kappa: {evaluation['agreement']['cohen_kappa']:.4f}",
        f"- Quadratic weighted kappa: {evaluation['agreement']['weighted_kappa_quadratic']:.4f}",
        "",
        "## Ranking",
    ]
    if evaluation["ranking"]:
        scoreboard.extend(f"- {k}: {v:.4f}" for k, v in evaluation["ranking"].items())
    else:
        scoreboard.append("- Ranking metrics unavailable: fewer than two candidates per query.")
    scoreboard.extend([
        "",
        "## Promotion gate",
        "- Use Final Gold Label (not first-pass Human Label) when available.",
        "- Human labels must be independently reviewed and the final workbook hash must match the freeze manifest.",
        "- The benchmark must be frozen and its SHA-256 recorded.",
        "- Job IDs must map to real persisted/discovered jobs before production validation.",
        "- Do not describe provisional results as production quality.",
        "",
    ])
    (args.output_dir / "MASTER_SCOREBOARD.md").write_text("\n".join(scoreboard), encoding="utf-8")
    print(json.dumps(evaluation, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
