"""
Batch re-render all verified STEP files with bbox normalization.

For every row in verified_parts.csv that has raw_step_path or gen_step_path,
renders composite.png (2×2 normalized multi-view) into:
  data/data_generation/views/<stem>/        (GT)
  data/data_generation/views_gen/<stem>/    (gen)

Updates views_raw_dir / views_gen_dir columns in verified_parts.csv.

Usage:
  python batch_render_normalized.py [--limit N] [--offset N] [--gt-only]
  python batch_render_normalized.py --limit 50 --gt-only
"""

import argparse
import sys
import os
import time
import traceback
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))

VERIFIED_CSV = ROOT / "data/data_generation/verified_parts.csv"
VIEWS_DIR = ROOT / "data/data_generation/views"
VIEWS_GEN_DIR = ROOT / "data/data_generation/views_gen"
IMG_SIZE = 128


def render_one(step_path: str, out_dir: Path, prefix: str = "") -> bool:
    """Render composite.png + view_N.png into out_dir. Returns True on success."""
    from render_normalized_views import render_step_normalized
    try:
        render_step_normalized(step_path, str(out_dir), size=IMG_SIZE, prefix=prefix)
        return True
    except Exception as e:
        print(f"    RENDER ERROR: {e}", flush=True)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--gt-only", action="store_true",
                    help="Only render GT (raw_step_path), skip gen")
    ap.add_argument("--gen-only", action="store_true",
                    help="Only render gen (gen_step_path), skip GT")
    ap.add_argument("--missing-only", action="store_true",
                    help="Skip rows that already have composite.png")
    ap.add_argument("--size", type=int, default=IMG_SIZE)
    args = ap.parse_args()

    df = pd.read_csv(VERIFIED_CSV)
    rows = df.copy()
    if args.offset:
        rows = rows.iloc[args.offset:]
    if args.limit:
        rows = rows.iloc[:args.limit]

    total = len(rows)
    gt_ok = gen_ok = gt_skip = gen_skip = errors = 0
    changed = []  # (idx, col, value)

    for i, (orig_idx, r) in enumerate(rows.iterrows(), 1):
        stem = r["stem"]
        print(f"[{i}/{total}] {stem}", flush=True)

        # ── GT render ──────────────────────────────────────────────────────
        if not args.gen_only:
            raw_step = str(r.get("raw_step_path", ""))
            if raw_step and os.path.isfile(ROOT / raw_step):
                out_dir = VIEWS_DIR / stem
                composite = out_dir / "composite.png"
                if args.missing_only and composite.exists():
                    gt_skip += 1
                else:
                    t0 = time.time()
                    ok = render_one(str(ROOT / raw_step), out_dir, prefix="")
                    elapsed = time.time() - t0
                    if ok:
                        gt_ok += 1
                        print(f"    GT  ok ({elapsed:.1f}s) → {composite}", flush=True)
                        # Update views_raw_dir if blank
                        rel = str(out_dir.relative_to(ROOT))
                        if str(r.get("views_raw_dir", "")) != rel:
                            changed.append((orig_idx, "views_raw_dir", rel))
                    else:
                        errors += 1
            else:
                gt_skip += 1

        # ── Gen render ─────────────────────────────────────────────────────
        if not args.gt_only:
            gen_step = str(r.get("gen_step_path", ""))
            if gen_step and os.path.isfile(ROOT / gen_step):
                out_dir = VIEWS_GEN_DIR / stem
                composite = out_dir / "composite.png"
                if args.missing_only and composite.exists():
                    gen_skip += 1
                else:
                    t0 = time.time()
                    ok = render_one(str(ROOT / gen_step), out_dir, prefix="")
                    elapsed = time.time() - t0
                    if ok:
                        gen_ok += 1
                        rel = str(out_dir.relative_to(ROOT))
                        if str(r.get("views_gen_dir", "")) != rel:
                            changed.append((orig_idx, "views_gen_dir", rel))
                    else:
                        errors += 1
            else:
                gen_skip += 1

    # ── Persist CSV updates ────────────────────────────────────────────────
    if changed:
        df_fresh = pd.read_csv(VERIFIED_CSV)
        for idx, col, val in changed:
            df_fresh.at[idx, col] = val
        df_fresh.to_csv(VERIFIED_CSV, index=False)
        print(f"\nUpdated {len(changed)} CSV cells.")

    print(f"\nDone: GT {gt_ok} ok / {gt_skip} skip | "
          f"Gen {gen_ok} ok / {gen_skip} skip | {errors} errors")


if __name__ == "__main__":
    main()
