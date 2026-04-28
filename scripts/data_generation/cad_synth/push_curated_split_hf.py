"""Push two HF datasets:

1. BenchCAD/cad_bench_subset_clean — our curated subset MINUS the stems used
   as substitutes for cad_diverse_800's missing-image stems.
2. BenchCAD/cad_diverse_substituted — the ~205 cad_diverse stems missing in
   BenchCAD, paired with substitute (family, diff, plane)-matched rows
   from BenchCAD; substitute stems renamed `dvsub_<diverse_stem>` to avoid
   future name conflict.

Both contain: stem, family, difficulty, base_plane, ops_used, gt_code,
composite_png, **standard** (ISO/DIN/EN/ASME from registry).

Usage:
  uv run python3 scripts/data_generation/cad_synth/push_curated_split_hf.py \
      --repo1 BenchCAD/cad_bench_subset_clean \
      --repo2 BenchCAD/cad_diverse_substituted
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "data" / "data_generation"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def png_to_bytes(png) -> bytes | None:
    """Normalize cad_bench composite_png (which loads as PIL.Image) → PNG bytes."""
    if png is None:
        return None
    if isinstance(png, bytes):
        return png
    if isinstance(png, dict) and "bytes" in png:
        return png["bytes"]
    # PIL.Image
    try:
        import io

        buf = io.BytesIO()
        png.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"  png_to_bytes failed: {e}", file=sys.stderr)
        return None


def standard_of(fam: str) -> str:
    try:
        from scripts.data_generation.cad_synth.pipeline.registry import get_family

        return getattr(get_family(fam), "standard", "N/A") or "N/A"
    except Exception:
        return "N/A"


def base_row(r: dict) -> dict:
    return {
        "stem": r["stem"],
        "family": r["family"],
        "difficulty": r["difficulty"],
        "base_plane": r.get("base_plane", "XY"),
        "feature_count": int(r.get("feature_count", 0) or 0),
        "feature_tags": r.get("feature_tags", "{}"),
        "ops_used": r.get("ops_used", "[]"),
        "iso_tags": r.get("iso_tags", "{}"),
        "gt_code": r.get("gt_code", ""),
        "composite_png": png_to_bytes(r.get("composite_png")),
        "standard": standard_of(r["family"]),
    }


def write_shards_and_upload(
    rows,
    out_dir: Path,
    repo: str,
    token: str,
    shard_size: int = 2000,
    private: bool = False,
):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi

    out_dir.mkdir(parents=True, exist_ok=True)
    # Clean any old shards in out_dir
    for p in out_dir.glob("data-*.parquet"):
        p.unlink()

    n = len(rows)
    n_shards = (n + shard_size - 1) // shard_size
    for i in range(n_shards):
        chunk = rows[i * shard_size : (i + 1) * shard_size]
        path = out_dir / f"data-{i:05d}-of-{n_shards:05d}.parquet"
        pq.write_table(pa.Table.from_pylist(chunk), path, compression="zstd")
        print(f"  shard {i}: {len(chunk)} rows → {path.name}")

    api = HfApi(token=token)
    api.create_repo(repo, repo_type="dataset", exist_ok=True, private=private)
    api.upload_folder(
        folder_path=str(out_dir),
        repo_id=repo,
        repo_type="dataset",
        path_in_repo="data",
        allow_patterns="*.parquet",
    )
    print(f"  ✓ Pushed {n} rows → https://huggingface.co/datasets/{repo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo1", default="BenchCAD/cad_curated_main")
    ap.add_argument("--repo2", default="BenchCAD/cad_curated_subs")
    ap.add_argument("--subset-json", default=str(DATA / "bench_subset_1200.json"))
    ap.add_argument("--shard-dir1", default=str(DATA / "_parquet_shards_d1"))
    ap.add_argument("--shard-dir2", default=str(DATA / "_parquet_shards_d2"))
    ap.add_argument("--shard-size", type=int, default=2000)
    ap.add_argument("--skip1", action="store_true", help="skip dataset 1 push (resume)")
    ap.add_argument("--skip2", action="store_true", help="skip dataset 2 push")
    args = ap.parse_args()

    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    if not token:
        raise SystemExit("BenchCAD_HF_TOKEN / HF_TOKEN not set")

    from datasets import load_dataset

    print("Loading BenchCAD/cad_bench ...")
    bench = load_dataset("BenchCAD/cad_bench", split="test")
    bench_idx = {r["stem"]: i for i, r in enumerate(bench)}
    print(f"  {len(bench)} bench rows")

    print("Loading qixiaoqi/cad_diverse_800 ...")
    diverse = load_dataset("qixiaoqi/cad_diverse_800", split="train")
    diverse_idx = {r["stem"]: i for i, r in enumerate(diverse)}
    diverse_stems = sorted(diverse_idx.keys())
    print(f"  {len(diverse)} diverse rows · {len(diverse_stems)} unique stems")

    # ── Build family-diff-plane index for substitution ──
    bench_fdp = defaultdict(list)
    for i in range(len(bench)):
        r = bench[i]
        bench_fdp[(r["family"], r["difficulty"], r.get("base_plane", "XY"))].append(
            r["stem"]
        )
    for k in bench_fdp:
        bench_fdp[k].sort()

    # ── Match missing diverse stems to substitutes ──
    substitutions = {}
    used_subs = set()
    for s in diverse_stems:
        if s in bench_idx:
            continue
        r = diverse[diverse_idx[s]]
        key = (r["family"], r["difficulty"], r.get("base_plane", "XY"))
        cands = [c for c in bench_fdp.get(key, []) if c not in used_subs]
        if cands:
            substitutions[s] = cands[0]
            used_subs.add(cands[0])
    print(
        f"  substitutes matched: {len(substitutions)} / "
        f"{sum(1 for s in diverse_stems if s not in bench_idx)} missing"
    )

    # ── Dataset 1: our subset MINUS the bench stems used as substitutes ──
    subset = json.loads(Path(args.subset_json).read_text())
    subset_stems = subset["stems"]
    ds1_stems = [s for s in subset_stems if s not in used_subs]
    ds1_rows = []
    for s in ds1_stems:
        if s not in bench_idx:
            continue
        ds1_rows.append(base_row(bench[bench_idx[s]]))
    print(
        f"\nDataset 1 (our − subs): {len(ds1_rows)} rows "
        f"(was {len(subset_stems)}, removed {len(subset_stems) - len(ds1_rows)} "
        f"used-as-substitute)"
    )

    # ── Dataset 2: cad_diverse missing stems → substitute data, renamed ──
    ds2_rows = []
    for diverse_stem, bench_stem in substitutions.items():
        br = bench[bench_idx[bench_stem]]
        # Pull diverse-side metadata so we keep the diverse-original family/diff/plane.
        dr = diverse[diverse_idx[diverse_stem]]
        new_stem = f"dvsub_{diverse_stem}"
        ds2_rows.append(
            {
                "stem": new_stem,
                "original_diverse_stem": diverse_stem,
                "substitute_bench_stem": bench_stem,
                "family": br["family"],
                "difficulty": br["difficulty"],
                "base_plane": br.get("base_plane", "XY"),
                "feature_count": int(br.get("feature_count", 0) or 0),
                "feature_tags": br.get("feature_tags", "{}"),
                "ops_used": br.get("ops_used", "[]"),
                "iso_tags": br.get("iso_tags", "{}"),
                "gt_code": br.get("gt_code", ""),
                "composite_png": png_to_bytes(br.get("composite_png")),
                "standard": standard_of(br["family"]),
                # Provenance fields from diverse side (in case they differ).
                "diverse_family": dr.get("family"),
                "diverse_difficulty": dr.get("difficulty"),
                "diverse_base_plane": dr.get("base_plane", "XY"),
            }
        )
    print(f"Dataset 2 (diverse missing + substituted): {len(ds2_rows)} rows")

    # ── Push both ──
    if not args.skip1:
        print(f"\n=== Push 1: {args.repo1} ===")
        write_shards_and_upload(
            ds1_rows, Path(args.shard_dir1), args.repo1, token, args.shard_size
        )
    else:
        print("\n[skip1] Dataset 1 push skipped")
    if not args.skip2:
        print(f"\n=== Push 2: {args.repo2} ===")
        write_shards_and_upload(
            ds2_rows, Path(args.shard_dir2), args.repo2, token, args.shard_size
        )
    else:
        print("\n[skip2] Dataset 2 push skipped")

    # ── Save substitution map for traceability ──
    map_path = DATA / "diverse_substitution_map.json"
    map_path.write_text(
        json.dumps(
            {
                "primary": "qixiaoqi/cad_diverse_800",
                "substitute_source": "BenchCAD/cad_bench",
                "n_substituted": len(substitutions),
                "rename_pattern": "dvsub_<diverse_stem>",
                "mapping": substitutions,  # diverse_stem -> bench_stem chosen as substitute
            },
            indent=2,
            default=str,
        )
    )
    print(f"\nSubstitution map: {map_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
