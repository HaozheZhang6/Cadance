"""UA-20 — Finalize pairs_curated.jsonl from 4 plans:
  - curate_final_plan.json (dim edits, L1+L2, keyed by family)
  - curate_supplementary_plan.json (extra dim edits for single-edit families,
    keyed by family__axis; entry must include "family" field)
  - curate_additive_plan.json (add_hole/chamfer/fillet)
  - curate_multi_plan.json (multi-param edits)

Dim emits L1 (absolute value) + L2 (percent).
Additive emits L1 only (add + absolute value).
Multi-param emits L1 (two absolute values) + L2 (two percents).

Usage:
    python -m bench.edit_gen.curate_finalize
    python -m bench.edit_gen.curate_finalize --exclude-hard
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "data_generation" / "bench_edit"
PLAN_DIM = BASE / "curate_final_plan.json"
PLAN_SUPP = BASE / "curate_supplementary_plan.json"
PLAN_ADD = BASE / "curate_additive_plan.json"
PLAN_MULTI = BASE / "curate_multi_plan.json"
OUT = BASE / "pairs_curated.jsonl"


def render_number(v: float) -> str:
    r = round(v, 4)
    return (f"{r:.4f}".rstrip("0").rstrip(".")) or "0"


def human_for(p: str) -> str:
    return p.replace("_", " ")


def emit_dim_records(plan: dict, exclude_hard: bool, exclude_iou_broken: bool):
    """L1+L2 per entry. Family read from entry['family'] if present, else from key."""
    records = []
    dropped = {"hard": 0, "iou_broken": 0}
    for key, e in sorted(plan.items()):
        fam = e.get("family", key)
        if exclude_hard and e["dl_est"] > 6:
            dropped["hard"] += 1
            continue
        if exclude_iou_broken and float(e["iou"]) == 0.0:
            dropped["iou_broken"] += 1
            continue
        ov = float(e["orig_value"])
        tv = float(e["target_value"])
        pct = int(e["pct_delta"])
        axis = e["axis"]
        human = human_for(axis)
        target_str = render_number(tv)
        sign = "+" if pct > 0 else ""
        for lvl, text in [
            ("L1", f"Set the {human} to {target_str} mm."),
            ("L2", f"Change the {human} by {sign}{pct}%."),
        ]:
            rid = f"curated_{fam}_{axis}_{lvl}"
            records.append(
                {
                    "record_id": rid,
                    "family": fam,
                    "edit_type": "dim",
                    "level": lvl,
                    "axis": axis,
                    "pct_delta": pct,
                    "orig_value": ov,
                    "target_value": tv,
                    "unit": "mm",
                    "human_name": human,
                    "instruction": text,
                    "difficulty": e.get("difficulty", "easy"),
                    "original_code_path": e["orig_code_path"],
                    "gt_code_path": e["gt_code_path"],
                    "orig_step_path": e["orig_step_path"],
                    "gt_step_path": e["gt_step_path"],
                    "iou_orig_gt": round(float(e["iou"]), 4),
                    "dl_est": int(e["dl_est"]),
                    "source": e["source"],
                }
            )
    return records, dropped


def emit_additive_records(plan: dict):
    """L1 only per entry. Supports add_* and remove_* op_types."""
    records = []
    for _name, e in sorted(plan.items()):
        fam = e["family"]
        op_type = e["op_type"]
        rid = f"curated_{fam}_{op_type}_L1"
        orig_val = e.get("orig_value")
        # add_* ops default orig=0; remove_* ops should provide it in plan.
        if orig_val is None:
            orig_val = 0.0
        default_unit = "count" if op_type.startswith("remove_") else "mm"
        records.append(
            {
                "record_id": rid,
                "family": fam,
                "edit_type": op_type,
                "level": "L1",
                "axis": e["axis"],
                "pct_delta": 0,
                "orig_value": float(orig_val),
                "target_value": float(e["target_value"]),
                "unit": e.get("unit", default_unit),
                "human_name": e["axis"],
                "instruction": e["instruction"],
                "difficulty": e.get("difficulty", "medium"),
                "original_code_path": e["orig_code_path"],
                "gt_code_path": e["gt_code_path"],
                "orig_step_path": e["orig_step_path"],
                "gt_step_path": e["gt_step_path"],
                "iou_orig_gt": round(float(e["iou"]), 4),
                "iou_weak": bool(e.get("iou_weak", False)),
                "dl_est": int(e["dl_est"]),
                "source": e["source"],
            }
        )
    return records


def emit_multi_records(plan: dict):
    """L1+L2 per family — L1 sets absolute values for both axes,
    L2 gives percent deltas."""
    records = []
    for _name, e in sorted(plan.items()):
        fam = e["family"]
        axes = e["axes"]
        ax1, ax2 = axes
        # L1: absolute value for each
        t1 = render_number(ax1["target"])
        t2 = render_number(ax2["target"])
        l1_text = (
            f"Set the {human_for(ax1['axis'])} to {t1} mm and "
            f"the {human_for(ax2['axis'])} to {t2} mm."
        )
        sign1 = "+" if ax1["pct"] > 0 else ""
        sign2 = "+" if ax2["pct"] > 0 else ""
        l2_text = (
            f"Change the {human_for(ax1['axis'])} by {sign1}{ax1['pct']}% and "
            f"the {human_for(ax2['axis'])} by {sign2}{ax2['pct']}%."
        )
        for lvl, text in [("L1", l1_text), ("L2", l2_text)]:
            rid = f"curated_{fam}_multi_{lvl}"
            records.append(
                {
                    "record_id": rid,
                    "family": fam,
                    "edit_type": "multi_param",
                    "level": lvl,
                    "axis": f"{ax1['axis']}+{ax2['axis']}",
                    "pct_deltas": e["pct_deltas"],
                    "axes_detail": axes,
                    "instruction": text,
                    "difficulty": e.get("difficulty", "medium"),
                    "original_code_path": e["orig_code_path"],
                    "gt_code_path": e["gt_code_path"],
                    "orig_step_path": e["orig_step_path"],
                    "gt_step_path": e["gt_step_path"],
                    "iou_orig_gt": round(float(e["iou"]), 4),
                    "dl_est": int(e["dl_est"]),
                    "source": e["source"],
                }
            )
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude-hard", action="store_true")
    ap.add_argument("--exclude-iou-broken", action="store_true")
    args = ap.parse_args()

    all_records = []

    dim_plan = json.loads(PLAN_DIM.read_text())
    dim_records, dropped = emit_dim_records(
        dim_plan, args.exclude_hard, args.exclude_iou_broken
    )
    all_records.extend(dim_records)
    print(f"dim: {len(dim_plan)} families → {len(dim_records)} records (L1+L2)")
    if args.exclude_hard or args.exclude_iou_broken:
        print(f"  dropped: {dropped}")

    if PLAN_SUPP.exists():
        supp_plan = json.loads(PLAN_SUPP.read_text())
        supp_records, supp_dropped = emit_dim_records(
            supp_plan, args.exclude_hard, args.exclude_iou_broken
        )
        all_records.extend(supp_records)
        print(f"dim-supp: {len(supp_plan)} → {len(supp_records)} records (L1+L2)")

    if PLAN_ADD.exists():
        add_plan = json.loads(PLAN_ADD.read_text())
        add_records = emit_additive_records(add_plan)
        all_records.extend(add_records)
        print(f"additive: {len(add_plan)} → {len(add_records)} records")

    if PLAN_MULTI.exists():
        multi_plan = json.loads(PLAN_MULTI.read_text())
        multi_records = emit_multi_records(multi_plan)
        all_records.extend(multi_records)
        print(f"multi: {len(multi_plan)} → {len(multi_records)} records")

    with OUT.open("w") as fh:
        for r in all_records:
            fh.write(json.dumps(r) + "\n")
    print(f"\nwrote {OUT} — {len(all_records)} total records")


if __name__ == "__main__":
    main()
