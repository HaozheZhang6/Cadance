"""Build bench_manifest.jsonl and upload bench dataset to HuggingFace.

Usage:
    uv run python3 scripts/data_generation/cad_synth/upload_bench_hf.py \
        --run bench_1k_apr14 \
        --repo Hula0401/test_bench \
        [--dry-run]
"""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "data_generation" / "generated_data" / "fusion360"

# 19 OOD families (held-out from train)
OOD_FAMILIES = {
    "bellows", "worm_screw", "torus_link", "impeller", "propeller",
    "chair", "table", "snap_clip",
    "waffle_plate", "wire_grid", "mesh_panel",
    "t_pipe_fitting", "pipe_elbow", "duct_elbow",
    "dome_cap", "capsule", "coil_spring", "bucket", "nozzle",
}


def assign_split(family: str, base_plane: str) -> str:
    if family in OOD_FAMILIES:
        return "test-ood-family"
    if base_plane in ("XZ", "YZ"):
        return "test-ood-plane"
    return "test-iid"


def build_manifest(run_name: str) -> list[dict]:
    pattern = f"*/verified_{run_name}/meta.json"
    meta_files = sorted(DATA.glob(pattern))
    print(f"Found {len(meta_files)} samples for run '{run_name}'")

    rows = []
    for mf in meta_files:
        m = json.loads(mf.read_text())
        stem = m["stem"]
        run_dir = mf.parent
        family = m["family"]
        base_plane = m["params"].get("base_plane", "XY")
        split = assign_split(family, base_plane)

        row = {
            "stem": stem,
            "family": family,
            "difficulty": m["difficulty"],
            "base_plane": base_plane,
            "split": split,
            "feature_tags": m["feature_tags"],
            "feature_count": sum(1 for v in m["feature_tags"].values() if v),
            "ops_used": m["ops_used"],
            "run_name": run_name,
            # relative paths from DATA root
            "gt_code_path": str(run_dir.relative_to(ROOT) / "code.py"),
            "gt_step_path": str(run_dir.relative_to(ROOT) / "gen.step"),
            "composite_png": str(run_dir.relative_to(ROOT) / "views" / "composite.png"),
            "views_dir": str(run_dir.relative_to(ROOT) / "views"),
        }
        rows.append(row)

    return rows


def stage_dataset(rows: list[dict], stage_dir: Path) -> None:
    """Copy all files into stage_dir/{split}/{stem}/ layout."""
    stage_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        stem = row["stem"]
        split = row["split"]
        dest = stage_dir / "data" / split / stem
        dest.mkdir(parents=True, exist_ok=True)

        run_dir = ROOT / row["gt_code_path"].replace("/code.py", "")

        # Copy key files
        for fname in ["code.py", "gen.step", "meta.json",
                      "render_0.png", "render_1.png", "render_2.png", "render_3.png"]:
            src = run_dir / fname
            if src.exists():
                shutil.copy2(src, dest / fname)

        # Copy views/composite.png
        views_src = run_dir / "views"
        if views_src.exists():
            views_dest = dest / "views"
            if views_dest.exists():
                shutil.rmtree(views_dest)
            shutil.copytree(views_src, views_dest)

    # Write manifest
    manifest_path = stage_dir / "bench_manifest.jsonl"
    with open(manifest_path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"Staged {len(rows)} samples → {stage_dir}")
    print(f"Manifest → {manifest_path}")

    # Stats
    from collections import Counter
    splits = Counter(r["split"] for r in rows)
    fams = Counter(r["family"] for r in rows)
    diffs = Counter(r["difficulty"] for r in rows)
    planes = Counter(r["base_plane"] for r in rows)
    print(f"\nSplits: {dict(splits)}")
    print(f"Difficulties: {dict(diffs)}")
    print(f"Planes: {dict(planes)}")
    print(f"Families: {len(fams)}")


def upload_to_hf(stage_dir: Path, repo_id: str, token: str) -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=token)

    # Create repo if not exists
    try:
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        print(f"Repo ready: {repo_id}")
    except Exception as e:
        print(f"Repo create warning: {e}")

    print(f"Uploading {stage_dir} → {repo_id} ...")
    api.upload_folder(
        folder_path=str(stage_dir),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="bench_1k_apr14: 1k synth bench samples",
        ignore_patterns=["*.pyc", "__pycache__"],
    )
    print(f"Done! https://huggingface.co/datasets/{repo_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="bench_1k_apr14")
    ap.add_argument("--repo", default="Hula0401/test_bench")
    ap.add_argument("--stage-dir", default="/workspace/tmp/bench_hf_stage")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--manifest-only", action="store_true", help="only build manifest, skip upload")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token and not args.dry_run and not args.manifest_only:
        raise SystemExit("HF_TOKEN not set")

    rows = build_manifest(args.run)
    if not rows:
        raise SystemExit(f"No samples found for run '{args.run}'")

    stage_dir = Path(args.stage_dir)
    stage_dataset(rows, stage_dir)

    if args.dry_run or args.manifest_only:
        print("[dry-run / manifest-only] skipping upload")
        return

    upload_to_hf(stage_dir, args.repo, token)


if __name__ == "__main__":
    main()
