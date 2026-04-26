"""Push 100k simple_ops dataset to HuggingFace as a single parquet split.

Source: data/data_generation/simple_ops_100k/{code,step,meta}/

Each row:
  stem | family | difficulty | diff_label | code | ops_json | params_json |
  feature_tags_json | bbox_x | bbox_y | bbox_z | base_plane | step_bytes

Default target: BenchCAD/cad_simple_ops_100k

Usage:
  uv run python3 scripts/data_generation/cad_synth/push_simple_ops_hf.py \
      --repo BenchCAD/cad_simple_ops_100k
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "data_generation" / "simple_ops_100k"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def collect_rows(include_step: bool = True, max_rows: int | None = None):
    """Walk meta/*.json, gather (code + step + meta) into row dicts."""
    meta_files = sorted((DATA / "meta").glob("*.json"))
    if max_rows:
        meta_files = meta_files[:max_rows]
    print(f"Found {len(meta_files)} meta files")

    rows = []
    skipped = 0
    for mf in meta_files:
        stem = mf.stem
        code_path = DATA / "code" / f"{stem}.py"
        step_path = DATA / "step" / f"{stem}.step"
        if not (code_path.exists() and step_path.exists()):
            skipped += 1
            continue
        try:
            m = json.loads(mf.read_text())
            code = code_path.read_text()
            row = {
                "stem": stem,
                "family": m.get("family", ""),
                "difficulty": m.get("difficulty", ""),
                "diff_label": m.get("diff_label", ""),
                "code": code,
                "ops_json": json.dumps(m.get("ops", []), default=str),
                "params_json": json.dumps(m.get("params", {}), default=str),
                "feature_tags_json": json.dumps(m.get("feature_tags", {}), default=str),
                "bbox_x": float(m.get("bbox", [0, 0, 0])[0]),
                "bbox_y": float(m.get("bbox", [0, 0, 0])[1]),
                "bbox_z": float(m.get("bbox", [0, 0, 0])[2]),
                "base_plane": m.get("base_plane", "XY"),
                "n_ops": len(m.get("ops", [])),
            }
            if include_step:
                row["step_bytes"] = step_path.read_bytes()
            rows.append(row)
        except Exception as e:
            print(f"  skip {stem}: {e}")
            skipped += 1
    print(f"Built {len(rows)} rows (skipped {skipped})")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="BenchCAD/cad_simple_ops_100k")
    ap.add_argument("--no-step", action="store_true",
                    help="omit STEP bytes — code-only push (smaller, faster)")
    ap.add_argument("--max-rows", type=int, default=None,
                    help="cap rows (for smoke testing)")
    ap.add_argument("--private", action="store_true", default=False)
    args = ap.parse_args()

    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    if not token:
        raise SystemExit("BenchCAD_HF_TOKEN / HF_TOKEN not set in env or .env")

    rows = collect_rows(include_step=not args.no_step, max_rows=args.max_rows)
    if not rows:
        raise SystemExit("No rows collected")

    print(f"\nUploading to {args.repo} ...")
    from datasets import Dataset
    from huggingface_hub import HfApi

    ds = Dataset.from_list(rows)
    print(f"Dataset:\n{ds}")

    # Ensure repo exists.
    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="dataset", exist_ok=True, private=args.private)

    ds.push_to_hub(args.repo, token=token, split="train")
    print(f"\n✓ Pushed {len(rows)} rows → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    sys.exit(main() or 0)
