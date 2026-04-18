#!/usr/bin/env python
"""List all passing validation pairs (JSON + CadQuery) across all runs.

Aggregates results from all codex_validation run dirs, deduplicates by stem
(highest IoU wins), and prints a table + writes a JSONL manifest.

Usage:
  uv run python scripts/data_generation/list_verified_pairs.py
  uv run python scripts/data_generation/list_verified_pairs.py --out-dir data/verified
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = REPO_ROOT / "data/codex_validation"
JSON_DIR = REPO_ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"


def _collect_all_passing() -> list[dict]:
    """Scan all run_* dirs for passing results (iou_pass=True, ok=True)."""
    best: dict[str, dict] = {}  # stem → best result

    for run_dir in sorted(VALIDATION_DIR.glob("run_*")):
        report = run_dir / "validation_report.json"
        if not report.exists():
            continue
        data = json.loads(report.read_text())
        for r in data.get("results", []):
            if not (r.get("ok") and r.get("stage") == "done"):
                continue
            stem = r["stem"]
            iou = r.get("iou", 0.0)
            # keep highest IoU if seen in multiple runs
            if stem not in best or iou > best[stem].get("iou", 0.0):
                r["_run_dir"] = str(run_dir)
                best[stem] = r

    return sorted(best.values(), key=lambda x: x["stem"])


def _resolve_files(stem: str, run_dir: str) -> dict:
    rd = Path(run_dir)
    cq_path = rd / "cadquery" / f"{stem}.py"
    step_path = rd / "generated_step" / f"{stem}.step"

    # JSON: the reconstruction file uses base stem (without _NNNe suffix)
    # stem format: 100221_4d7b66c4_0003 → json base is 100221_4d7b66c4_0003.json
    json_path = JSON_DIR / f"{stem}.json"

    return {
        "cq_exists": cq_path.exists(),
        "step_exists": step_path.exists() and step_path.stat().st_size > 0,
        "json_exists": json_path.exists(),
        "cq_path": str(cq_path) if cq_path.exists() else None,
        "step_path": str(step_path) if (step_path.exists() and step_path.stat().st_size > 0) else None,
        "json_path": str(json_path) if json_path.exists() else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation-dir", type=Path, default=VALIDATION_DIR,
        help="Dir containing run_* subdirs",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Write manifest JSONL to this path",
    )
    args = parser.parse_args()

    passing = _collect_all_passing()
    if not passing:
        print("No passing pairs found.")
        return 0

    print(f"{'Stem':<45} {'IoU':>6}  CQ  STEP  JSON  Run")
    print("-" * 80)

    manifest = []
    for r in passing:
        stem = r["stem"]
        iou = r.get("iou", 0.0)
        files = _resolve_files(stem, r["_run_dir"])
        run_name = Path(r["_run_dir"]).name

        cq_ok = "✓" if files["cq_exists"] else "✗"
        st_ok = "✓" if files["step_exists"] else "✗"
        js_ok = "✓" if files["json_exists"] else "✗"
        print(f"{stem:<45} {iou:>6.4f}   {cq_ok}    {st_ok}     {js_ok}   {run_name}")

        manifest.append({
            "stem": stem,
            "iou": iou,
            "complexity": r.get("complexity"),
            "json_path": files["json_path"],
            "cq_path": files["cq_path"],
            "step_path": files["step_path"],
            "run": run_name,
        })

    print(f"\nTotal: {len(passing)} passing pairs")
    cq_count = sum(1 for m in manifest if m["cq_path"])
    step_count = sum(1 for m in manifest if m["step_path"])
    json_count = sum(1 for m in manifest if m["json_path"])
    print(f"  CadQuery .py files : {cq_count}/{len(passing)}")
    print(f"  Generated STEP     : {step_count}/{len(passing)}")
    print(f"  Fusion360 JSON     : {json_count}/{len(passing)}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            "\n".join(json.dumps(m) for m in manifest) + "\n", encoding="utf-8"
        )
        print(f"\nManifest written: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
