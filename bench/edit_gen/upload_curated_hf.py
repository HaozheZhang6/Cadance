"""Upload curated edit benchmark (UA-20) to HF.

Reads pairs_curated.jsonl + codes/ + steps/, pushes to --repo.
Handles 3 edit_types: dim / multi_param / add_* (hole/chamfer/fillet).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = ROOT / "data/data_generation/bench_edit"


def build_rows() -> list[dict]:
    jsonl = BENCH_DIR / "pairs_curated.jsonl"
    if not jsonl.exists():
        raise SystemExit(f"pairs_curated.jsonl not found: {jsonl}")

    rows: list[dict] = []
    skipped = 0
    with jsonl.open() as f:
        for line in f:
            r = json.loads(line)
            orig_code = BENCH_DIR / r["original_code_path"]
            gt_code = BENCH_DIR / r["gt_code_path"]
            orig_step = BENCH_DIR / r["orig_step_path"]
            gt_step = BENCH_DIR / r["gt_step_path"]
            if not all(p.exists() for p in (orig_code, gt_code, orig_step, gt_step)):
                skipped += 1
                continue
            rows.append(
                {
                    "record_id": r["record_id"],
                    "family": r["family"],
                    "edit_type": r["edit_type"],
                    "difficulty": r["difficulty"],
                    "level": r["level"],
                    "axis": r.get("axis") or "",
                    "pct_delta": float(r.get("pct_delta") or 0.0),
                    "orig_value": float(r.get("orig_value") or 0.0),
                    "target_value": float(r.get("target_value") or 0.0),
                    "unit": r.get("unit") or "",
                    "human_name": r.get("human_name") or "",
                    "instruction": r["instruction"],
                    "orig_code": orig_code.read_text(),
                    "gt_code": gt_code.read_text(),
                    "orig_step": orig_step.read_bytes(),
                    "gt_step": gt_step.read_bytes(),
                    "iou_orig_gt": float(r["iou_orig_gt"]),
                    "dl_est": int(r["dl_est"]),
                    "source": r["source"],
                    "axes_detail": json.dumps(r.get("axes_detail") or []),
                    "pct_deltas": json.dumps(r.get("pct_deltas") or []),
                    "split": "test_iid",
                }
            )
    if skipped:
        print(f"skipped {skipped} rows with missing files")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="BenchCAD/cad_bench_edit")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass
    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    if not token:
        raise SystemExit("BenchCAD_HF_TOKEN / HF_TOKEN not set")

    rows = build_rows()
    if not rows:
        raise SystemExit("No rows built")

    n_fam = len({r["family"] for r in rows})
    edit_dist = {}
    for r in rows:
        edit_dist[r["edit_type"]] = edit_dist.get(r["edit_type"], 0) + 1
    print(f"built {len(rows)} rows, {n_fam} families, edit_type={edit_dist}")

    from datasets import Dataset, DatasetDict

    ds = Dataset.from_list(rows)
    dd = DatasetDict({"test": ds})
    print(f"pushing to {args.repo} ...")
    dd.push_to_hub(
        args.repo,
        token=token,
        commit_message=f"curated edit bench: {len(rows)} records ({n_fam} fam)",
    )
    print(f"done → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
