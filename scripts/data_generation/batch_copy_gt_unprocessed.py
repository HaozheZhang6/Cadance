#!/usr/bin/env python3
"""Copy-GT for F360 stems not yet in parts.csv (unprocessed offsets 6000-8625).

These stems haven't had codex_validation run yet.
We add them directly as copy-GT entries with iou=1.0.

Usage:
  uv run python3 scripts/data_generation/batch_copy_gt_unprocessed.py [--dry-run]
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))
import db

GT_BASE = ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools"
JSON_DIR = ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"
OPS_JSON_BASE = ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"
RUN_DIR = ROOT / "data/data_generation/codex_validation/batch_copy_gt_f360"

COPY_GT_SCRIPT = """\
# copy_gt: direct copy of ground truth STEP (no LLM codegen)
import shutil, os
gt_path = os.path.normpath(os.path.join(os.path.dirname(__file__), {rel!r}))
shutil.copy(gt_path, "output.step")
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    import pandas as pd

    # Build GT index
    print("Building GT index...", flush=True)
    step_map: dict[str, list[str]] = defaultdict(list)
    for fname in os.listdir(GT_BASE):
        m = re.match(r"^(\d+_[0-9a-f]+_\d+)_(\d+)e\.step$", fname)
        if m:
            step_map[m.group(1)].append(fname)
    for k in step_map:
        step_map[k].sort()  # sort for determinism; use last (matches _build_index)

    # Get valid record order
    valid_records = []
    for jp in sorted(JSON_DIR.glob("*.json")):
        base = jp.stem
        if base in step_map:
            valid_records.append(base)

    print(f"Total valid F360 stems: {len(valid_records)}")

    # Already processed
    parts = pd.read_csv(ROOT / "data/data_generation/parts.csv")
    f360_runs = [
        "retry_v2", "retry_v3", "retry_v45", "retry_v6", "run_v2_n1000",
        "run_v2_n1000_glm46v", "run_v7_n1000", "run_v8_n1000",
        "run_v4_n1000_openai", "run_v3_n1000", "claude_manual_fix", "claude_fixed"
    ]
    f360_parts = parts[parts["run"].isin(f360_runs)]
    f360_base_stems = set(f360_parts["stem"].str.replace("_claude_fixed", "").tolist())

    unprocessed = [s for s in valid_records if s not in f360_base_stems]
    print(f"Unprocessed stems: {len(unprocessed)}")

    # Also check run_v9 checkpoint for already-processed stems
    v9_checkpoint = ROOT / "data/data_generation/codex_validation/run_v9_n1000/checkpoint.jsonl"
    v9_done = set()
    if v9_checkpoint.exists():
        with open(v9_checkpoint) as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    if d.get("stem"):
                        v9_done.add(d["stem"])
                except Exception:
                    pass
    print(f"Already done in run_v9: {len(v9_done)}")

    # Load current vp stems
    vp = pd.read_csv(ROOT / "data/data_generation/verified_parts.csv")
    vp_stems = set(vp["stem"].tolist())

    # Setup output dir
    (RUN_DIR / "generated_step").mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "cadquery").mkdir(parents=True, exist_ok=True)

    added = 0
    skipped = 0

    to_process = unprocessed
    if args.limit:
        to_process = to_process[: args.limit]

    for i, stem in enumerate(to_process):
        # Skip if already in vp
        copy_stem = stem + "_copy_gt"
        if copy_stem in vp_stems:
            skipped += 1
            continue

        # Skip if already processed by run_v9 (and passed)
        if stem in v9_done:
            skipped += 1
            continue

        # Pick GT file (last sorted = matches _build_index)
        candidates = step_map.get(stem, [])
        if not candidates:
            skipped += 1
            continue
        gt_fname = candidates[-1]
        gt_file = GT_BASE / gt_fname

        # Output paths
        gen_step_path = RUN_DIR / "generated_step" / f"{copy_stem}.step"
        cq_code_path = RUN_DIR / "cadquery" / f"{copy_stem}.py"
        ops_json_path = OPS_JSON_BASE / f"{stem}.json"

        if args.dry_run:
            if i < 5 or added % 500 == 0:
                print(f"  [DRY] {copy_stem}: gt={gt_fname}")
            added += 1
            continue

        # Copy GT
        shutil.copy(gt_file, gen_step_path)

        # Write CQ script
        rel = os.path.relpath(gt_file, cq_code_path.parent)
        cq_code_path.write_text(COPY_GT_SCRIPT.format(rel=rel))

        # Add to vp
        record = {
            "stem": copy_stem,
            "raw_step_path": str(gt_file.relative_to(ROOT)),
            "ops_json_path": str(ops_json_path.relative_to(ROOT)) if ops_json_path.exists() else "",
            "gen_step_path": str(gen_step_path.relative_to(ROOT)),
            "cq_code_path": str(cq_code_path.relative_to(ROOT)),
            "iou": 1.0,
            "verified": True,
            "views_raw_dir": "",
            "views_gen_dir": "",
            "source": "batch_copy_gt_f360",
            "note": "copy_gt: unprocessed F360 stem, direct copy of GT STEP",
            "visual_verdict": "SKIP",
            "visual_reason": "",
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        db.append_verified(record)
        vp_stems.add(copy_stem)

        added += 1
        if added % 100 == 0:
            print(f"  [{added}/{len(to_process)}] added={added}", flush=True)

    print(f"\nDone: added={added}, skipped={skipped}")

    if not args.dry_run and added > 0:
        print("Rebuilding CSVs...", flush=True)
        db.build_all_csvs()
        print("Done.")


if __name__ == "__main__":
    main()
