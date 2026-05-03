"""Score existing N=30 model gens with canonical_ops essentials + feature F1.

Outputs:
  - per-model summary (essential pass %, feature F1, IoU)
  - cases where essential=fail but IoU≥0.3 (shortcut signal)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from canonical_ops import (  # noqa: E402
    ESSENTIAL_BY_FAMILY, essential_pass, feature_f1, find_ops, fmt_spec,
)

MODELS = [
    ("gpt-4o",                "results/img2cq/gpt-4o/results.jsonl"),
    ("gpt-5.3 (no reason.)",  "results/img2cq/gpt-5.3-chat-latest/results.jsonl"),
    ("gpt-5.3 (reason.=med)", "results/img2cq/gpt-5.3-thinking/results.jsonl"),
    ("gemini-2.5-flash",      "results/img2cq/gemini-2.5-flash/results.jsonl"),
]


def main():
    from datasets import load_dataset

    # GT codes — use cad_bench (test) which is what bench/eval.py samples from
    print("loading cad_bench gt_code lookup ...")
    gt_lookup = {}
    ds = load_dataset("BenchCAD/cad_bench", split="test").to_pandas()
    for _, r in ds.iterrows():
        gt_lookup[r["stem"]] = r["gt_code"]

    summary = []
    interesting = []

    for label, path in MODELS:
        rows = (
            pd.read_json(ROOT / path, lines=True)
            .tail(30)
            .to_dict(orient="records")
        )
        n = len(rows)
        ess_results = []   # True / False / None
        feat_f1s = []
        ious = []
        for r in rows:
            stem = r["stem"]
            family = r["family"]
            gen_ops = find_ops(r.get("gen_code", "") or "")
            gt_ops = find_ops(gt_lookup.get(stem, "") or "")
            ess = essential_pass(family, gen_ops)
            ff1 = feature_f1(gen_ops, gt_ops)
            iou = float(r.get("iou", 0.0))
            ess_results.append(ess)
            feat_f1s.append(ff1)
            ious.append(iou)
            # Interesting case: essential failed but IoU is decent
            if ess is False and iou >= 0.3:
                interesting.append((label, stem, family, gt_ops & set(ESSENTIAL_BY_FAMILY.get(family, [])), gen_ops, iou))

        n_ess_total = sum(1 for e in ess_results if e is not None)
        n_ess_pass = sum(1 for e in ess_results if e is True)
        n_na = sum(1 for e in ess_results if e is None)
        ess_pct = n_ess_pass / n_ess_total if n_ess_total else 0.0
        feat_mean = sum(feat_f1s) / n if n else 0.0
        iou_mean = sum(ious) / n if n else 0.0
        summary.append({
            "model": label,
            "n": n,
            "ess_pass_rate": ess_pct,
            "ess_passed": n_ess_pass,
            "ess_required": n_ess_total,
            "ess_na": n_na,
            "feature_f1": feat_mean,
            "iou": iou_mean,
        })

    print("\n=== Summary ===")
    print(f"{'model':<24} {'ess pass':>12} {'feat F1':>9} {'IoU':>8}")
    print("-" * 60)
    for s in summary:
        ess_str = f"{s['ess_passed']}/{s['ess_required']} ({s['ess_pass_rate']*100:.0f}%)"
        print(f"{s['model']:<24} {ess_str:>12} {s['feature_f1']:>9.3f} {s['iou']:>8.3f}")

    print("\n=== 'Shortcut' cases — essential=fail but IoU≥0.3 ===")
    print(f"{'model':<24} {'family':<22} {'iou':>5}  GT essential")
    print("-" * 100)
    for label, stem, fam, gt_e, gen, iou in interesting:
        spec = fmt_spec(ESSENTIAL_BY_FAMILY[fam])
        print(f"{label:<24} {fam:<22} {iou:>5.2f}  needs: {spec}")

    out = {"summary": summary, "shortcuts": [
        {"model": m, "stem": s, "family": f, "iou": i}
        for (m, s, f, _, _, i) in interesting
    ]}
    out_path = ROOT / "bench/research/outputs/run_2026_04_27/score_v4.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nsaved → {out_path}")


if __name__ == "__main__":
    main()
