"""Deterministic calibration of hybrid ranking weights from human labels."""
from __future__ import annotations
import argparse, json
from pathlib import Path

FEATURES = ("semantic","technical","role","experience","education","preference","evidence")
DEFAULT_WEIGHTS = {"semantic":0.25,"technical":0.30,"role":0.15,"experience":0.10,"education":0.05,"preference":0.10,"evidence":0.05}

def normalize_weights(weights):
    clipped = {k:max(0.0,float(weights.get(k,0.0))) for k in FEATURES}
    total = sum(clipped.values())
    if total <= 0: raise ValueError("weights must contain positive mass")
    return {k:v/total for k,v in clipped.items()}

def mse(rows, weights):
    error=0.0
    for row in rows:
        score=sum(float(row["features"][k])*weights[k] for k in FEATURES)/100.0
        target=float(row["relevance"])/4.0
        error += (score-target)**2
    return error/max(len(rows),1)

def calibrate(rows, steps=20, grid=0.05):
    weights=normalize_weights(DEFAULT_WEIGHTS)
    for _ in range(steps):
        improved=False
        for feature in FEATURES:
            best=weights; best_loss=mse(rows,weights)
            for i in range(21):
                candidate=dict(weights); candidate[feature]=i*grid
                candidate=normalize_weights(candidate)
                loss=mse(rows,candidate)
                if loss < best_loss-1e-12:
                    best,best_loss=candidate,loss; improved=True
            weights=best
        if not improved: break
    return weights

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    rows=json.loads(args.input.read_text(encoding="utf-8"))
    if len(rows)<20: raise SystemExit("Calibration requires at least 20 human-labeled rows")
    weights=calibrate(rows)
    args.output.write_text(json.dumps({"version":"hybrid-calibrated-v1","weights":weights},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
