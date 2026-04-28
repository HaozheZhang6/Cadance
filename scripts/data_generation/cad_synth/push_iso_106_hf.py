"""Push ISO 100 family codegen dataset (~170k) to HuggingFace as parquet.

Source: data/data_generation/iso_106_codegen/{code,step,meta}/

Default target: BenchCAD/cad_iso_106

Skipped families (heavy geometry): sprocket / double_simplex_sprocket /
spur_gear / helical_gear / bevel_gear / worm_screw.

Usage:
  uv run python3 scripts/data_generation/cad_synth/push_iso_106_hf.py \
      --repo BenchCAD/cad_iso_106
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "data_generation" / "iso_106_codegen"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def _build_one_row(stem: str, include_step: bool):
    code_path = DATA / "code" / f"{stem}.py"
    step_path = DATA / "step" / f"{stem}.step"
    meta_path = DATA / "meta" / f"{stem}.json"
    if not (code_path.exists() and step_path.exists() and meta_path.exists()):
        return None
    m = json.loads(meta_path.read_text())
    bbox = (list(m.get("bbox") or []) + [0.0, 0.0, 0.0])[:3]
    row = {
        "stem": stem,
        "family": m.get("family", ""),
        "difficulty": m.get("difficulty", ""),
        "diff_label": m.get("diff_label", ""),
        "code": code_path.read_text(),
        "ops_json": json.dumps(m.get("ops", []), default=str),
        "params_json": json.dumps(m.get("params", {}), default=str),
        "feature_tags_json": json.dumps(m.get("feature_tags", {}), default=str),
        "bbox_x": float(bbox[0]),
        "bbox_y": float(bbox[1]),
        "bbox_z": float(bbox[2]),
        "base_plane": m.get("base_plane", "XY"),
        "n_ops": len(m.get("ops", [])),
    }
    if include_step:
        row["step_bytes"] = step_path.read_bytes()
    return row


def write_parquet_shards(
    out_dir: Path, include_step: bool, max_rows: int | None, shard_size: int = 5000
):
    """Stream rows in chunks of shard_size, write each as parquet — bounded memory."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_dir.mkdir(parents=True, exist_ok=True)
    meta_files = sorted((DATA / "meta").glob("*.json"))
    if max_rows:
        meta_files = meta_files[:max_rows]
    total_meta = len(meta_files)
    print(
        f"Found {total_meta} meta files; writing shards to {out_dir} (size={shard_size})"
    )

    total_rows = 0
    skipped = 0
    shard_idx = 0
    buf = []
    for i, mf in enumerate(meta_files):
        try:
            row = _build_one_row(mf.stem, include_step)
        except Exception as e:
            print(f"  skip {mf.stem}: {e}")
            row = None
        if row is None:
            skipped += 1
        else:
            buf.append(row)
        if len(buf) >= shard_size or (i == total_meta - 1 and buf):
            shard_path = out_dir / f"data-{shard_idx:05d}-of-XXXXX.parquet"
            tbl = pa.Table.from_pylist(buf)
            pq.write_table(tbl, shard_path, compression="zstd")
            total_rows += len(buf)
            print(
                f"  shard {shard_idx} ({len(buf)} rows) → {shard_path.name}, "
                f"total={total_rows}/{total_meta}, skipped={skipped}"
            )
            shard_idx += 1
            buf.clear()
            del tbl

    # Rename with final shard count.
    n_shards = shard_idx
    for p in out_dir.glob("data-*-of-XXXXX.parquet"):
        new_name = p.name.replace("of-XXXXX", f"of-{n_shards:05d}")
        p.rename(out_dir / new_name)
    print(f"Wrote {n_shards} shards, {total_rows} rows total (skipped {skipped})")
    return n_shards, total_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="BenchCAD/cad_iso_106")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--shard-size", type=int, default=5000)
    ap.add_argument("--shard-dir", default=str(DATA / "_parquet_shards"))
    ap.add_argument(
        "--skip-write",
        action="store_true",
        help="reuse existing shard dir, only upload",
    )
    ap.add_argument("--private", action="store_true", default=False)
    args = ap.parse_args()

    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    if not token:
        raise SystemExit("BenchCAD_HF_TOKEN / HF_TOKEN not set")

    out_dir = Path(args.shard_dir)
    if not args.skip_write:
        write_parquet_shards(
            out_dir,
            include_step=not args.no_step,
            max_rows=args.max_rows,
            shard_size=args.shard_size,
        )

    print(f"\nUploading shards from {out_dir} → {args.repo} ...")
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="dataset", exist_ok=True, private=args.private)
    api.upload_folder(
        folder_path=str(out_dir),
        repo_id=args.repo,
        repo_type="dataset",
        path_in_repo="data",
        allow_patterns="*.parquet",
    )
    print(f"\n✓ Pushed → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    sys.exit(main() or 0)
