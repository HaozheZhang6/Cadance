"""Reliability of has_hole detection — appendix §D.3 reproducible eval.

Compares three methods on synth_parts.csv verified pool:
  A — AST regex on CadQuery code
  B — STEP B-rep (REVERSED cylindrical face, r ≥ 0.5 mm)
  C — A OR B  (production, see bench/metrics/feature_detect)

GT label = `feature_tags["has_hole"]` set declaratively by family make_program().

Usage:
    LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 \
        bench/research/hole_detection_eval.py --n 1000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bench.metrics import _step_has_hole, extract_features  # noqa: E402


def cm(pred, gt):
    tp = int(((pred) & (gt)).sum())
    fp = int(((pred) & (~gt)).sum())
    fn = int(((~pred) & (gt)).sum())
    tn = int(((~pred) & (~gt)).sum())
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return tp, fp, fn, tn, p, r, f1


def main() -> None:
    import pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/data_generation/synth_parts.csv")
    ap.add_argument("--n", type=int, default=1000, help="random sample size")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--out",
        default=None,
        help="output CSV path (default: bench/research/outputs/hole_method_c_<n>_<seed>.csv)",
    )
    ap.add_argument(
        "--examples", type=int, default=3, help="example stems printed per bucket"
    )
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df[
        (df.status == "accepted")
        & (df.code_exec_ok == True)  # noqa: E712
        & df.step_path.notna()
        & df.code_path.notna()
        & df.feature_tags.notna()
    ].copy()
    print(f"eligible pool: {len(df)} rows ({df.family.nunique()} families)")

    if args.n >= len(df):
        sampled = df.copy()
    else:
        sampled = df.sample(args.n, random_state=args.seed).reset_index(drop=True)
    print(f"sampled: {len(sampled)} (seed={args.seed})")

    rows = []
    t0 = time.time()
    for i in range(len(sampled)):
        s = sampled.iloc[i]
        if not (os.path.exists(s["step_path"]) and os.path.exists(s["code_path"])):
            continue
        try:
            tags = json.loads(s["feature_tags"])
            gt = bool(tags.get("has_hole", False))
        except Exception:
            continue
        code = open(s["code_path"]).read()
        ast = extract_features(code)["has_hole"]
        step = _step_has_hole(s["step_path"])
        rows.append(
            {
                "stem": s["stem"],
                "family": s["family"],
                "gt": gt,
                "ast": ast,
                "step": step,
                "c": (ast or step),
            }
        )
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(sampled)}  elapsed={time.time()-t0:.0f}s", flush=True)

    res = pd.DataFrame(rows)
    res = res.rename(columns={"gt": "GT", "ast": "AST", "step": "STEP", "c": "C"})

    out = args.out or str(
        ROOT
        / "bench"
        / "research"
        / "outputs"
        / f"hole_method_c_n{len(res)}_s{args.seed}.csv"
    )
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out, index=False)
    print(f"\nwrote {out} ({len(res)} rows, {time.time()-t0:.0f}s)\n")

    # ── Confusion matrices ────────────────────────────────────────────────────
    n = len(res)
    print(f"N={n}  GT+={int(res.GT.sum())}  GT-={int((~res.GT).sum())}")
    print(
        f"\n{'Method':<14}{'TP':>5}{'FP':>5}{'FN':>5}{'TN':>5}  {'Prec':>7}{'Rec':>7}{'F1':>7}"
    )
    for name, col in [("A AST", res.AST), ("B STEP", res.STEP), ("C A OR B", res.C)]:
        tp, fp, fn, tn, p, r, f1 = cm(col, res.GT)
        print(f"{name:<14}{tp:>5}{fp:>5}{fn:>5}{tn:>5}  {p:>7.3f}{r:>7.3f}{f1:>7.3f}")

    # ── Per-bucket breakdown ──────────────────────────────────────────────────
    buckets = [
        ("RESCUE  (AST=F, STEP=T, GT+)", (~res.AST) & res.STEP & res.GT),
        ("STILL-FN (both miss, GT+)", (~res.AST) & (~res.STEP) & res.GT),
        ("NEW STEP-FP (STEP+, GT-)", (~res.AST) & res.STEP & (~res.GT)),
        ("AST-FP kept (AST+, GT-)", res.AST & (~res.GT)),
    ]
    for label, mask in buckets:
        sub = res[mask]
        print(f"\n── {label} — total {len(sub)} ──")
        if not len(sub):
            continue
        per_family = sub.groupby("family").size().sort_values(ascending=False)
        print(per_family.head(15).to_string())
        # show example stems from up to N families
        seen = set()
        for _, row in sub.iterrows():
            if row.family in seen:
                continue
            seen.add(row.family)
            print(f"    e.g. {row.stem}")
            if len(seen) >= args.examples:
                break


if __name__ == "__main__":
    main()
