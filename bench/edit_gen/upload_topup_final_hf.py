"""Upload topup_final to HuggingFace as cad_bench_edit v2.

Source: data/data_generation/bench_edit/topup_final/records.jsonl
Target: BenchCAD/cad_bench_edit (replaces existing).

Each record fields: record_id, family, edit_type, difficulty, instruction,
iou (orig→gt), source, orig_code, gt_code, orig_step (bytes), gt_step (bytes).

Skips records with missing files.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "data" / "data_generation" / "bench_edit" / "topup_final"


def build_rows() -> list[dict]:
    jsonl = FINAL / "records.jsonl"
    rows: list[dict] = []
    skipped = 0
    for line in jsonl.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        orig_code = FINAL / r["orig_code_path"]
        gt_code = FINAL / r["gt_code_path"]
        orig_step = FINAL / r["orig_step_path"]
        gt_step = FINAL / r["gt_step_path"]
        if not all(p.exists() for p in (orig_code, gt_code, orig_step, gt_step)):
            skipped += 1
            continue
        rows.append({
            "record_id": r["record_id"],
            "family": r["family"],
            "edit_type": r["edit_type"],
            "difficulty": r.get("difficulty", ""),
            "instruction": r["instruction"],
            "iou": float(r["iou"]) if r.get("iou") is not None else 0.0,
            "source": r.get("source", ""),
            "orig_code": orig_code.read_text(),
            "gt_code": gt_code.read_text(),
            "orig_step": orig_step.read_bytes(),
            "gt_step": gt_step.read_bytes(),
        })
    if skipped:
        print(f"skipped {skipped} records with missing files")
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
    type_cnt: dict[str, int] = {}
    for r in rows:
        type_cnt[r["edit_type"]] = type_cnt.get(r["edit_type"], 0) + 1
    print(f"built {len(rows)} rows, {n_fam} families")
    for t, n in sorted(type_cnt.items(), key=lambda x: -x[1]):
        print(f"  {t:20s} {n}")

    from datasets import Dataset, DatasetDict

    ds = Dataset.from_list(rows)
    dd = DatasetDict({"test": ds})
    print(f"\npushing to {args.repo} ...")
    dd.push_to_hub(
        args.repo,
        token=token,
        commit_message=f"edit bench v2: {len(rows)} records ({n_fam} fam)",
    )
    print(f"done → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
