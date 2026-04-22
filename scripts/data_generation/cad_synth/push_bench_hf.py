"""Push bench dataset to HuggingFace as Parquet (fast, images embedded).

Default target: BenchCAD/cad_bench — covers 3 tasks with shared rows:
  code gen (composite→gt_code), QA-image (composite+qa_pairs),
  QA-code (gt_code+qa_pairs). Edit task has its own repo (cad_bench_edit).

Single `test` split — no iid/ood partition (base_plane and family are
available as metadata columns if you want to slice at eval time).

Usage:
    uv run python3 scripts/data_generation/cad_synth/push_bench_hf.py \
        --run batch_20k_apr20 --repo BenchCAD/cad_bench
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = ROOT / "data" / "data_generation" / "generated_data" / "fusion360"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def build_rows(
    run_name: str,
    revalidate_code: bool = True,
    workers: int = 8,
    dropped_log: Path | None = None,
) -> list[dict]:
    from scripts.data_generation.cad_synth._upload_filter import (
        accepted_stems,
        filter_rows,
    )

    meta_files = sorted(DATA.glob(f"*/verified_{run_name}/meta.json"))
    print(f"Found {len(meta_files)} samples (pre-filter)")

    stems_ok = accepted_stems(run_name)
    print(f"  accepted stems in CSV for run: {len(stems_ok)}")
    meta_files, drops = filter_rows(
        meta_files,
        stems_ok,
        revalidate_code=revalidate_code,
        workers=workers,
        dropped_log=dropped_log,
        pipeline_run=run_name,
    )
    print(f"After filter: {len(meta_files)} samples")
    if drops:
        print("  Dropped:")
        for reason, n in sorted(drops.items(), key=lambda x: -x[1]):
            print(f"    {reason}: {n}")

    rows = []
    for mf in meta_files:
        m = json.loads(mf.read_text())
        run_dir = mf.parent
        family = m["family"]
        base_plane = m["params"].get("base_plane", "XY")

        comp_path = run_dir / "views" / "composite.png"
        img_bytes = comp_path.read_bytes() if comp_path.exists() else None
        code_path = run_dir / "code.py"
        code = code_path.read_text() if code_path.exists() else ""

        rows.append(
            {
                "stem": m["stem"],
                "family": family,
                "difficulty": m["difficulty"],
                "base_plane": base_plane,
                "feature_tags": json.dumps(m["feature_tags"]),
                "feature_count": sum(1 for v in m["feature_tags"].values() if v),
                "ops_used": json.dumps(m["ops_used"]),
                "gt_code": code,
                "composite_png": img_bytes,  # bytes → datasets Image feature
                "qa_pairs": json.dumps(m.get("qa_pairs", [])),
                "iso_tags": json.dumps(m.get("iso_tags", {})),
            }
        )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="batch_20k_apr20")
    ap.add_argument("--repo", default="BenchCAD/cad_bench")
    ap.add_argument(
        "--no-revalidate-code",
        action="store_true",
        help="skip re-exec of code.py (faster, but may ship cases broken under current env)",
    )
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument(
        "--dropped-log",
        default="tmp/push_bench_dropped.csv",
        help="CSV path to log dropped stems + reasons",
    )
    args = ap.parse_args()

    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    if not token:
        raise SystemExit("BenchCAD_HF_TOKEN / HF_TOKEN not set")

    import io

    from datasets import Dataset, DatasetDict, Image
    from PIL import Image as PILImage

    rows = build_rows(
        args.run,
        revalidate_code=not args.no_revalidate_code,
        workers=args.workers,
        dropped_log=Path(args.dropped_log) if args.dropped_log else None,
    )
    if not rows:
        raise SystemExit("No rows found")

    print("Building dataset...")
    pil_rows = []
    for r in rows:
        row = dict(r)
        if row["composite_png"]:
            row["composite_png"] = PILImage.open(io.BytesIO(row["composite_png"]))
        pil_rows.append(row)

    ds = Dataset.from_list(pil_rows).cast_column("composite_png", Image())
    dd = DatasetDict({"test": ds})
    print(f"  test: {len(ds)} samples")
    print(f"Pushing to {args.repo} ...")
    dd.push_to_hub(
        args.repo,
        token=token,
        commit_message=f"{args.run}: {len(ds)} rows",
    )
    print(f"Done! https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
