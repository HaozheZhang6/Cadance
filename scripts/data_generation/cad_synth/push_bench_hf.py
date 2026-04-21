"""Push bench dataset to HuggingFace as Parquet (fast, images embedded).

Usage:
    HF_TOKEN=... uv run python3 scripts/data_generation/cad_synth/push_bench_hf.py \
        --run bench_1k_apr14 --repo Hula0401/test_bench
"""

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "data_generation" / "generated_data" / "fusion360"

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


def build_rows(run_name: str) -> list[dict]:
    meta_files = sorted(DATA.glob(f"*/verified_{run_name}/meta.json"))
    print(f"Found {len(meta_files)} samples")
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
            }
        )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="bench_1k_apr14")
    ap.add_argument("--repo", default="Hula0401/test_bench")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN not set")

    from datasets import Dataset, DatasetDict, Features, Value, Image, Sequence
    import io
    from PIL import Image as PILImage

    rows = build_rows(args.run)
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
    print(f"Pushing to {args.repo} ...")
    ds.push_to_hub(
        args.repo,
        token=token,
        commit_message="bench_1k_apr14: 994 synth CAD bench samples",
    )
    print(f"Done! https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
