#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("dataset", type=Path)
    p.add_argument("--expected-groups", type=int, default=50)
    p.add_argument("--expected-candidates", type=int, default=5)
    p.add_argument("--manifest", type=Path, required=True)
    args=p.parse_args()
    raw=args.dataset.read_bytes()
    lines=[x for x in raw.decode("utf-8").splitlines() if x.strip()]
    if len(lines)!=args.expected_groups: raise SystemExit(f"expected {args.expected_groups} groups, found {len(lines)}")
    seen=set()
    for line in lines:
        case=json.loads(line); qid=case.get("query_id")
        if not qid or qid in seen: raise SystemExit("query_id values must be unique")
        seen.add(qid); candidates=case.get("candidates",[])
        if len(candidates)!=args.expected_candidates: raise SystemExit(f"{qid}: candidate count mismatch")
        for item in candidates:
            if not item.get("job_id"): raise SystemExit(f"{qid}: missing job_id")
            if not isinstance(item.get("relevance"),int) or not 0<=item["relevance"]<=4: raise SystemExit(f"{qid}: relevance must be integer 0..4")
    digest=hashlib.sha256(raw).hexdigest()
    manifest={"dataset":str(args.dataset),"sha256":digest,"query_groups":len(lines),"candidates_per_group":args.expected_candidates}
    args.manifest.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__": main()
