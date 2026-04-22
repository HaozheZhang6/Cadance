"""Push bench dataset to HuggingFace as Parquet (fast, images embedded).

Default target: BenchCAD/cad_bench (config "main") — covers 3 tasks:
  code gen (composite→gt_code), QA-image (composite+qa_pairs),
  QA-code (gt_code+qa_pairs). Edit bench lives in same repo under config "edit".

Usage:
    uv run python3 scripts/data_generation/cad_synth/push_bench_hf.py \
        --run batch_20k_apr20 --repo BenchCAD/cad_bench --config main
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

OOD_FAMILIES = {
    "bellows",
    "worm_screw",
    "torus_link",
    "impeller",
    "propeller",
    "chair",
    "table",
    "snap_clip",
    "waffle_plate",
    "wire_grid",
    "mesh_panel",
    "t_pipe_fitting",
    "pipe_elbow",
    "duct_elbow",
    "dome_cap",
    "capsule",
    "coil_spring",
    "bucket",
    "nozzle",
}


def assign_split(family: str, base_plane: str) -> str:
    if family in OOD_FAMILIES:
        return "test-ood-family"
    if base_plane in ("XZ", "YZ"):
        return "test-ood-plane"
    return "test-iid"


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
        split = assign_split(family, base_plane)

        # Read composite image bytes
        comp_path = run_dir / "views" / "composite.png"
        img_bytes = comp_path.read_bytes() if comp_path.exists() else None

        # Read code
        code_path = run_dir / "code.py"
        code = code_path.read_text() if code_path.exists() else ""

        rows.append(
            {
                "stem": m["stem"],
                "family": family,
                "difficulty": m["difficulty"],
                "base_plane": base_plane,
                "split": split,
                "feature_tags": json.dumps(m["feature_tags"]),
                "feature_count": sum(1 for v in m["feature_tags"].values() if v),
                "ops_used": json.dumps(m["ops_used"]),
                "gt_code": code,
                "composite_png": img_bytes,  # raw bytes → datasets will handle as Image
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
        "--config",
        default="main",
        help='HF config (subset) name: "main" for code+QA, "edit" for edit bench',
    )
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
    # Convert bytes → PIL for datasets Image feature
    pil_rows = []
    for r in rows:
        row = dict(r)
        if row["composite_png"]:
            row["composite_png"] = PILImage.open(io.BytesIO(row["composite_png"]))
        pil_rows.append(row)

    # Split into subsets (HF split names must be word chars only)
    split_map = {
        "test-iid": "test_iid",
        "test-ood-family": "test_ood_family",
        "test-ood-plane": "test_ood_plane",
    }
    splits_data = {"test_iid": [], "test_ood_family": [], "test_ood_plane": []}
    for row in pil_rows:
        key = split_map[row["split"]]
        splits_data[key].append(row)

    # Build DatasetDict
    dd = {}
    for split_name, split_rows in splits_data.items():
        if split_rows:
            dd[split_name] = Dataset.from_list(split_rows).cast_column(
                "composite_png", Image()
            )
            print(f"  {split_name}: {len(split_rows)} samples")

    ds = DatasetDict(dd)
    n_total = sum(len(v) for v in splits_data.values())
    print(f"Pushing to {args.repo} (config={args.config}) ...")
    ds.push_to_hub(
        args.repo,
        config_name=args.config,
        token=token,
        commit_message=f"{args.run}: {n_total} rows ({args.config})",
    )
    print(f"Done! https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
