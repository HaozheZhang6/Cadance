"""Upload edit benchmark (UA-19) to HF.

Reads data/data_generation/bench_edit/pairs.jsonl + codes/ + steps/,
packs orig/gt code (text) and STEP (bytes) per row, pushes to --repo.

Usage:
    uv run python bench/edit_gen/upload_edit_hf.py \
        --repo Hula0401/cad_synth_bench_edit

Eval reads rows via datasets.load_dataset, writes STEP bytes to tmp,
runs IoU(gen, gt) vs IoU(orig, gt) → norm_improve.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = ROOT / "data/data_generation/bench_edit"


def build_rows() -> list[dict]:
    jsonl = BENCH_DIR / "pairs.jsonl"
    if not jsonl.exists():
        raise SystemExit(f"pairs.jsonl not found: {jsonl}")

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
                    "difficulty": r["difficulty"],
                    "axis": r["axis"],
                    "level": r["level"],
                    "pct_delta": r["pct_delta"],
                    "orig_value": r["orig_value"],
                    "target_value": r["target_value"],
                    "unit": r["unit"],
                    "human_name": r["human_name"],
                    "instruction": r["instruction"],
                    "orig_code": orig_code.read_text(),
                    "gt_code": gt_code.read_text(),
                    "orig_step": orig_step.read_bytes(),
                    "gt_step": gt_step.read_bytes(),
                    "orig_params": json.dumps(r["orig_params"]),
                    "target_params": json.dumps(r["target_params"]),
                    "iou_orig_gt": r["iou_orig_gt"],
                    "split": "test_iid",
                }
            )
    if skipped:
        print(f"skipped {skipped} rows with missing files")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Hula0401/cad_synth_bench_edit")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN not set")

    rows = build_rows()
    if not rows:
        raise SystemExit("No rows built")
    print(f"built {len(rows)} rows")

    from datasets import Dataset, DatasetDict

    ds = Dataset.from_list(rows)
    dd = DatasetDict({"test_iid": ds})
    print(f"pushing to {args.repo} ...")
    dd.push_to_hub(
        args.repo,
        token=token,
        commit_message=f"edit bench: {len(rows)} pairs (L1+L2, {len(set(r['family'] for r in rows))} families)",
    )
    print(f"done → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
