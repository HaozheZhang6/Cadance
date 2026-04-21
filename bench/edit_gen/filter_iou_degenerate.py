"""Post-filter existing bench_edit dataset: drop pairs where IoU(orig, gt) > threshold.

These pairs are "edit-invisible" — the perturbation leaves the normalized bbox
voxelization unchanged, so the IoU metric cannot detect whether the model made
the edit. Better to drop than to pollute aggregate scores.

After filtering:
- Rewrite pairs.jsonl (keep only surviving records)
- Delete orphaned gt_code/gt_step files (orig files kept only if some axis
  survives for that root)
- Report families with 0 surviving records → user should add new axes

Usage:
    python -m bench.edit_gen.filter_iou_degenerate
    python -m bench.edit_gen.filter_iou_degenerate --threshold 0.99 --dry-run
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from bench.metrics import compute_iou

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCH = ROOT / "data" / "data_generation" / "bench_edit"


def filter_dataset(bench_dir: Path, threshold: float, dry_run: bool) -> dict:
    pairs_path = bench_dir / "pairs.jsonl"
    records = [
        json.loads(ln) for ln in pairs_path.read_text().splitlines() if ln.strip()
    ]

    # Unique (orig_step_path, gt_step_path) — L1 and L2 share the same pair
    unique_pairs: dict[tuple[str, str], dict] = {}
    for r in records:
        key = (r["orig_step_path"], r["gt_step_path"])
        unique_pairs.setdefault(key, r)

    print(f"Total records: {len(records)}  unique pairs: {len(unique_pairs)}")
    print(f"Computing IoU(orig, gt) for each unique pair (threshold={threshold})...")

    pair_iou: dict[tuple[str, str], float] = {}
    drop_keys: set[tuple[str, str]] = set()
    for i, (key, r) in enumerate(unique_pairs.items()):
        orig_p = bench_dir / r["orig_step_path"]
        gt_p = bench_dir / r["gt_step_path"]
        iou, err = compute_iou(str(orig_p), str(gt_p))
        pair_iou[key] = iou
        if iou > threshold:
            drop_keys.add(key)
        if (i + 1) % 50 == 0:
            print(
                f"  [{i+1:4d}/{len(unique_pairs)}] drop so far: "
                f"{len(drop_keys)}  last_iou={iou:.4f}"
            )

    # Split records; annotate kept records with cached iou_orig_gt so future
    # scoring runs don't need to recompute.
    kept, dropped = [], []
    for r in records:
        k = (r["orig_step_path"], r["gt_step_path"])
        if k in drop_keys:
            dropped.append(r)
        else:
            r["iou_orig_gt"] = round(pair_iou[k], 4)
            kept.append(r)

    # Per-family stats (count surviving records by family)
    fam_kept = defaultdict(int)
    fam_dropped = defaultdict(int)
    for r in kept:
        fam_kept[r["family"]] += 1
    for r in dropped:
        fam_dropped[r["family"]] += 1

    empty_families = sorted(
        fam for fam, n in fam_dropped.items() if fam_kept.get(fam, 0) == 0
    )

    summary = {
        "threshold": threshold,
        "records_before": len(records),
        "records_after": len(kept),
        "records_dropped": len(dropped),
        "unique_pairs_dropped": len(drop_keys),
        "unique_pairs_total": len(unique_pairs),
        "empty_families": empty_families,
        "empty_family_count": len(empty_families),
    }

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2))

    # Low-coverage families (1-3 records left)
    low_cov = sorted((fam, n) for fam, n in fam_kept.items() if 0 < n <= 3)
    if low_cov:
        print("\nLow-coverage families (≤3 surviving records):")
        for fam, n in low_cov:
            print(f"  {fam}: {n}")

    if dry_run:
        print("\n[dry-run] no files modified")
        return summary

    # Persist: rewrite pairs.jsonl, backup old one
    backup = pairs_path.with_suffix(".jsonl.prefilter_bak")
    pairs_path.rename(backup)
    with pairs_path.open("w") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")

    # Delete orphaned gt_code and gt_step files.
    # orig_* are shared across axes of the same root; keep only if the root has
    # any surviving record.
    kept_orig_paths = {r["orig_step_path"] for r in kept} | {
        r["original_code_path"] for r in kept
    }
    gt_paths_to_delete: set[str] = set()
    orig_paths_touched: set[str] = set()
    for r in dropped:
        gt_paths_to_delete.add(r["gt_code_path"])
        gt_paths_to_delete.add(r["gt_step_path"])
        orig_paths_touched.add(r["orig_step_path"])
        orig_paths_touched.add(r["original_code_path"])

    n_deleted = 0
    for rel in gt_paths_to_delete:
        p = bench_dir / rel
        if p.exists():
            p.unlink()
            n_deleted += 1
    # Delete orphaned orig files
    for rel in orig_paths_touched:
        if rel in kept_orig_paths:
            continue
        p = bench_dir / rel
        if p.exists():
            p.unlink()
            n_deleted += 1

    # Write filter report
    report = {
        **summary,
        "per_family_kept": dict(fam_kept),
        "per_family_dropped": dict(fam_dropped),
        "files_deleted": n_deleted,
        "pairs_backup": str(backup.relative_to(bench_dir)),
    }
    (bench_dir / "pair_filter_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nDeleted {n_deleted} orphaned files")
    print(f"Report: {bench_dir / 'pair_filter_report.json'}")
    print(f"Backup: {backup}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-dir", type=str, default=str(DEFAULT_BENCH))
    ap.add_argument("--threshold", type=float, default=0.99)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    filter_dataset(Path(args.bench_dir), args.threshold, args.dry_run)


if __name__ == "__main__":
    main()
