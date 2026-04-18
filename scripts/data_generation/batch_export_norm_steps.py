"""
Export normalized GT STEP files for all verified stems.

For each row in verified_parts.csv with gt_step_path:
  1. Load GT STEP
  2. Translate bbox center → origin, scale longest axis → 1.0  (bbox → [-0.5, 0.5]³)
  3. Export to generated_data/fusion360/<base_stem>/gt/gt_norm.step
  4. Write gt_norm_step_path column back to verified_parts.csv

Usage:
  uv run python3 batch_export_norm_steps.py [--limit N] [--offset N] [--missing-only]
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))

VERIFIED_CSV = ROOT / "data/data_generation/verified_parts.csv"
STEM_FS      = ROOT / "data/data_generation/generated_data/fusion360"


def _strip_suffix(stem: str) -> str:
    for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
        if stem.endswith(sfx):
            return stem[: -len(sfx)]
    return stem


def _normalize_and_export(raw_step: str, out_step: str) -> tuple[bool, str]:
    """Load STEP, bbox-normalize, export. Returns (ok, error)."""
    try:
        import cadquery as cq
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec

        shape = cq.importers.importStep(raw_step)
        bb = shape.val().BoundingBox()
        cx = (bb.xmin + bb.xmax) / 2
        cy = (bb.ymin + bb.ymax) / 2
        cz = (bb.zmin + bb.zmax) / 2
        longest = max(bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
        if longest < 1e-12:
            return False, "degenerate bbox"

        # translate center → origin, then scale longest axis → 1.0
        t = gp_Trsf()
        t.SetTranslation(gp_Vec(-cx, -cy, -cz))
        s = gp_Trsf()
        s.SetScale(gp_Pnt(0, 0, 0), 1.0 / longest)
        ts = gp_Trsf()
        ts.Multiply(s)
        ts.Multiply(t)  # ts = s * t  →  applied as: scale(translate(p))

        norm_shape = cq.Shape(
            BRepBuilderAPI_Transform(shape.val().wrapped, ts, True).Shape()
        )
        Path(out_step).parent.mkdir(parents=True, exist_ok=True)
        norm_shape.exportStep(out_step)
        if not os.path.isfile(out_step):
            return False, "no output file"
        return True, ""
    except Exception as e:
        return False, str(e)[:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit",        type=int, default=0)
    ap.add_argument("--offset",       type=int, default=0)
    ap.add_argument("--missing-only", action="store_true",
                    help="Skip stems that already have gt_norm_step_path")
    args = ap.parse_args()

    df = pd.read_csv(VERIFIED_CSV)
    rows = df.copy()

    if args.missing_only and "gt_norm_step_path" in df.columns:
        rows = rows[rows["gt_norm_step_path"].isna() | (rows["gt_norm_step_path"] == "")]

    if args.offset:
        rows = rows.iloc[args.offset:]
    if args.limit:
        rows = rows.iloc[:args.limit]

    total = len(rows)
    print(f"Processing {total} stems → stem-centric gt/gt_norm.step")

    ok = skip = fail = 0
    changed: list[tuple[int, str]] = []  # (orig_idx, rel_path)

    for i, (orig_idx, r) in enumerate(rows.iterrows(), 1):
        stem     = str(r["stem"])
        base     = _strip_suffix(stem)
        gt_step  = str(r.get("gt_step_path", ""))

        if not gt_step or not (ROOT / gt_step).is_file():
            skip += 1
            if i <= 5 or skip <= 3:
                print(f"  [{i}/{total}] SKIP {stem}: gt_step_path missing or not on disk")
            continue

        out_step = STEM_FS / base / "gt" / "gt_norm.step"
        success, err = _normalize_and_export(str(ROOT / gt_step), str(out_step))

        if success:
            ok += 1
            rel = str(out_step.relative_to(ROOT))
            changed.append((orig_idx, rel))
        else:
            fail += 1
            print(f"  [{i}/{total}] FAIL {stem}: {err}")

        if i % 200 == 0:
            print(f"[{i}/{total}] ok={ok} skip={skip} fail={fail}")

    if changed:
        df_fresh = pd.read_csv(VERIFIED_CSV)
        if "gt_norm_step_path" not in df_fresh.columns:
            df_fresh["gt_norm_step_path"] = ""
        for idx, val in changed:
            df_fresh.at[idx, "gt_norm_step_path"] = val
        df_fresh.to_csv(VERIFIED_CSV, index=False)
        print(f"\nUpdated {len(changed)} rows → gt_norm_step_path")

    print(f"\nDone: ok={ok} skip={skip} fail={fail} / {total}")


if __name__ == "__main__":
    main()
