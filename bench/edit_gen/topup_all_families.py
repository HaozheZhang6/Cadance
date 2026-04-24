"""UA-20 topup — batch-generate 2 feature ops per family for all 106 families.

For each family:
  - Find orig code file in bench_edit/codes/ (prefer easy_r0, fall back to hard)
  - Read its STEP bbox
  - Generate 2 specs: axial hole (Z-cut) + radial hole (X-cut), sized at
    radius = 0.15 × min bbox dim (min 1.5 mm, max 30 mm)
  - Exec gt, IoU gate (< 0.99), collect

Output → data/data_generation/bench_edit/topup_all/
  codes/, steps/, preview.png (one big mosaic), manifest.csv, records.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cadquery as cq
from OCP.STEPControl import STEPControl_Reader

from bench.edit_gen.edit_axes import EDIT_AXES
from bench.edit_gen.topup_edits import (
    build_preview_mosaic as _build_mosaic_orig,
    exec_cq,
    splice_gt_code,
)

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_all"


def load_bbox(step_path: Path) -> tuple[float, float, float]:
    r = STEPControl_Reader()
    r.ReadFile(str(step_path))
    r.TransferRoots()
    bb = cq.Shape(r.OneShape()).BoundingBox()
    return bb.xlen, bb.ylen, bb.zlen


def pick_orig(family: str) -> Path | None:
    codes = BENCH / "codes"
    steps = BENCH / "steps"
    cands = [
        codes / f"{family}_easy_r0_orig.py",
        codes / f"{family}_hard_r0_orig.py",
    ]
    cands.extend(sorted(codes.glob(f"{family}_gid*_orig.py")))
    for c in cands:
        if c.exists() and (steps / (c.stem + ".step")).exists():
            return c
    return None


def gen_specs_for_family(family: str) -> list[dict]:
    orig_path = pick_orig(family)
    if orig_path is None:
        return []
    orig_step = BENCH / "steps" / (orig_path.stem + ".step")
    try:
        xl, yl, zl = load_bbox(orig_step)
    except Exception:
        return []
    if min(xl, yl, zl) < 2.0:
        return []

    # Axial (Z) hole: radius = 0.15 × min(xl, yl), clamped
    r_axial = max(1.5, min(30.0, 0.15 * min(xl, yl)))
    # Radial (X) hole: radius = 0.15 × min(yl, zl), clamped
    r_radial = max(1.5, min(30.0, 0.15 * min(yl, zl)))
    # Cylinder length: 3× major axis
    len_axial = max(50.0, 3.0 * zl)
    len_radial = max(50.0, 3.0 * xl)

    specs = [
        {
            "record_id": f"topup_{family}_auto_axial_hole",
            "family": family,
            "orig": orig_path.name,
            "edit_type": "add_hole",
            "difficulty": "easy",
            "instruction": (
                f"Drill a {2*r_axial:.0f} mm diameter through-hole "
                f"along the Z axis of the part."
            ),
            "op_code": (
                "result = result.cut("
                f"cq.Workplane('XY').cylinder({len_axial:.1f}, {r_axial:.2f}))"
            ),
        },
        {
            "record_id": f"topup_{family}_auto_radial_hole",
            "family": family,
            "orig": orig_path.name,
            "edit_type": "add_hole",
            "difficulty": "medium",
            "instruction": (
                f"Drill a {2*r_radial:.0f} mm diameter cross-hole "
                f"through the part along the X axis."
            ),
            "op_code": (
                "result = result.cut("
                f"cq.Workplane('YZ').cylinder({len_radial:.1f}, {r_radial:.2f}))"
            ),
        },
    ]
    return specs


def process_spec(spec: dict) -> dict:
    orig_path = BENCH / "codes" / spec["orig"]
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)

    rid = spec["record_id"]
    orig_out_code = codes_dir / f"{rid}_orig.py"
    gt_out_code = codes_dir / f"{rid}_gt.py"
    orig_out_step = steps_dir / f"{rid}_orig.step"
    gt_out_step = steps_dir / f"{rid}_gt.step"

    orig_out_code.write_text(orig_text)
    if orig_step_src.exists():
        orig_out_step.write_bytes(orig_step_src.read_bytes())
    else:
        ok, err = exec_cq(orig_text, orig_out_step)
        if not ok:
            return {**spec, "status": "fail_orig_exec", "err": err}

    try:
        gt_text = splice_gt_code(orig_text, spec["op_code"])
    except Exception as e:
        return {**spec, "status": "fail_splice", "err": str(e)}
    gt_out_code.write_text(gt_text)

    ok, err = exec_cq(gt_text, gt_out_step)
    if not ok:
        return {**spec, "status": "fail_gt_exec", "err": err}

    try:
        from bench.metrics import compute_iou
        iou, iou_err = compute_iou(str(orig_out_step), str(gt_out_step))
    except Exception as e:
        iou, iou_err = None, str(e)[:200]

    status = "ok"
    if iou is None:
        status = "fail_iou"
    elif iou >= 0.99:
        status = "fail_iou_too_high"
    elif iou < 0.3:
        status = "fail_iou_too_low"

    return {
        **spec,
        "status": status,
        "orig_code_path": str(orig_out_code.relative_to(OUT)),
        "gt_code_path": str(gt_out_code.relative_to(OUT)),
        "orig_step_path": str(orig_out_step.relative_to(OUT)),
        "gt_step_path": str(gt_out_step.relative_to(OUT)),
        "iou": iou,
        "iou_err": iou_err,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="family name filter")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    fams = sorted(EDIT_AXES.keys())
    if args.only:
        fams = [f for f in fams if args.only in f]

    all_specs = []
    for f in fams:
        all_specs.extend(gen_specs_for_family(f))
    print(f"generated {len(all_specs)} specs across {len(fams)} families")

    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for i, spec in enumerate(all_specs):
        print(f"[{i+1:3d}/{len(all_specs)}] {spec['record_id']} ... ",
              end="", flush=True)
        rec = process_spec(spec)
        iou = rec.get("iou")
        iou_s = f"IoU={iou:.3f}" if isinstance(iou, float) else "IoU=?"
        print(f"{rec['status']} {iou_s}")
        records.append(rec)

    # Write jsonl
    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records)
    )

    # Stats
    ok = [r for r in records if r["status"] == "ok"]
    too_high = [r for r in records if r["status"] == "fail_iou_too_high"]
    too_low = [r for r in records if r["status"] == "fail_iou_too_low"]
    exec_fail = [r for r in records if r["status"] == "fail_gt_exec"]
    splice_fail = [r for r in records if r["status"] == "fail_splice"]
    print(f"\n  ok: {len(ok)}   iou>0.99: {len(too_high)}   "
          f"iou<0.3: {len(too_low)}   gt_exec_fail: {len(exec_fail)}   "
          f"splice_fail: {len(splice_fail)}")

    # Coverage: families with ≥1 OK
    fam_ok = {r["family"] for r in ok}
    fam_two_ok: dict[str, int] = {}
    for r in ok:
        fam_two_ok[r["family"]] = fam_two_ok.get(r["family"], 0) + 1
    two_plus = {f for f, n in fam_two_ok.items() if n >= 2}
    print(f"  families ≥1 ok: {len(fam_ok)}/{len(fams)}  "
          f"≥2 ok: {len(two_plus)}/{len(fams)}")

    # CSV (all rows, numbered only for OK)
    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "num", "record_id", "family", "edit_type", "difficulty",
            "iou", "status", "instruction"
        ])
        ok_idx = 0
        for r in records:
            if r["status"] == "ok":
                ok_idx += 1
                num = str(ok_idx)
            else:
                num = ""
            w.writerow([
                num, r["record_id"], r["family"], r["edit_type"],
                r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float) else "",
                r["status"], r["instruction"],
            ])
    print(f"\nwrote {csv_path}")

    if not args.no_preview and ok:
        # Reuse the mosaic builder from topup_edits; point it at OUT
        import bench.edit_gen.topup_edits as te
        te.OUT = OUT
        te.build_preview_mosaic(records, OUT / "preview.png")


if __name__ == "__main__":
    main()
