"""UA-20 Phase 3b — extended palette for families left short after boss-drop.

After dropping add_boss from topup_diverse, 74 families need additional ops:
  - 49 have only 1 non-boss op
  - 12 relied entirely on boss (now have 0)
  - 13 failed Phase 2 entirely

This script reads topup_diverse/records.jsonl, strips add_boss, finds families
with <2 ops, then tries an extended palette of targeted ops NOT yet tried:
  - top_circle_fillet / top_circle_chamfer (revolved shapes)
  - offset_axial_hole (different position than existing center hole)
  - end_face_chamfer (small, for thin parts)
  - offset_radial_hole
  - cross_hole_Y (perpendicular to both axial and radial)

Writes to topup_phase3b/.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cadquery as cq
from OCP.STEPControl import STEPControl_Reader

from bench.edit_gen.edit_axes import EDIT_AXES
from bench.edit_gen.topup_edits import exec_cq, splice_gt_code

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
PHASE2 = BENCH / "topup_diverse"
OUT = BENCH / "topup_phase3b"


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


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def build_extended_palette(
    family: str, orig: str, xl: float, yl: float, zl: float,
    exclude_types: set
) -> list[dict]:
    min_xy = min(xl, yl)
    min_yz = min(yl, zl)
    thin = min(xl, yl, zl) < 8.0

    # Targeted ops
    circle_r = clamp(0.05 * min_xy, 0.3 if thin else 1.0, 4.0)
    top_circle_cham = clamp(0.06 * min_xy, 0.2 if thin else 0.8, 3.0)
    end_cham = clamp(0.03 * min_xy, 0.2 if thin else 0.5, 1.5)
    ox = 0.22 * xl
    oy = 0.22 * yl
    off_hole_r = clamp(0.08 * min_xy, 0.8 if thin else 1.5, 8.0)
    hole_L = max(60.0, 3.0 * max(xl, yl, zl))
    axial_r = clamp(0.14 * min_xy, 1.0 if thin else 2.0, 12.0)
    radial_r = clamp(0.11 * min_yz, 1.0 if thin else 2.0, 10.0)
    y_r = clamp(0.11 * min(xl, zl), 1.0 if thin else 2.0, 10.0)

    base = {"family": family, "orig": orig}
    all_ops = [
        {**base, "op_name": "top_circle_fillet",
         "edit_type": "add_fillet", "difficulty": "easy",
         "instruction": f"Fillet the top circular edges by {circle_r:.1f} mm.",
         "op_code": (f"result = result.edges('%CIRCLE and >Z')"
                     f".fillet({circle_r:.2f})")},
        {**base, "op_name": "top_circle_chamfer",
         "edit_type": "add_chamfer", "difficulty": "easy",
         "instruction": (f"Chamfer the top circular edges by "
                         f"{top_circle_cham:.1f} mm."),
         "op_code": (f"result = result.edges('%CIRCLE and >Z')"
                     f".chamfer({top_circle_cham:.2f})")},
        {**base, "op_name": "bottom_circle_fillet",
         "edit_type": "add_fillet", "difficulty": "easy",
         "instruction": f"Fillet the bottom circular edges by {circle_r:.1f} mm.",
         "op_code": (f"result = result.edges('%CIRCLE and <Z')"
                     f".fillet({circle_r:.2f})")},
        {**base, "op_name": "bottom_circle_chamfer",
         "edit_type": "add_chamfer", "difficulty": "easy",
         "instruction": (f"Chamfer the bottom circular edges by "
                         f"{end_cham:.1f} mm."),
         "op_code": (f"result = result.edges('%CIRCLE and <Z')"
                     f".chamfer({end_cham:.2f})")},
        {**base, "op_name": "all_circle_chamfer",
         "edit_type": "add_chamfer", "difficulty": "medium",
         "instruction": f"Chamfer all circular edges by {end_cham:.1f} mm.",
         "op_code": f"result = result.edges('%CIRCLE').chamfer({end_cham:.2f})"},
        {**base, "op_name": "offset_axial_hole",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*off_hole_r:.0f} mm diameter hole "
                         f"along Z at offset ({ox:.0f}, {oy:.0f})."),
         "op_code": (f"result = result.cut(cq.Workplane('XY')"
                     f".transformed(offset=cq.Vector({ox:.2f},{oy:.2f},0))"
                     f".cylinder({hole_L:.1f},{off_hole_r:.2f}))")},
        {**base, "op_name": "axial_hole",
         "edit_type": "add_hole", "difficulty": "easy",
         "instruction": (f"Drill a {2*axial_r:.0f} mm diameter "
                         f"through-hole along the Z axis."),
         "op_code": (f"result = result.cut(cq.Workplane('XY').cylinder("
                     f"{hole_L:.1f},{axial_r:.2f}))")},
        {**base, "op_name": "radial_hole_X",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*radial_r:.0f} mm diameter cross-hole "
                         f"along the X axis."),
         "op_code": (f"result = result.cut(cq.Workplane('YZ').cylinder("
                     f"{hole_L:.1f},{radial_r:.2f}))")},
        {**base, "op_name": "radial_hole_Y",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*y_r:.0f} mm diameter cross-hole "
                         f"along the Y axis."),
         "op_code": (f"result = result.cut(cq.Workplane('XZ').cylinder("
                     f"{hole_L:.1f},{y_r:.2f}))")},
    ]
    # Exclude types that family already has (prefer diversity)
    return [op for op in all_ops if op["edit_type"] not in exclude_types]


def process_spec(spec: dict, codes_dir: Path, steps_dir: Path) -> dict:
    orig_path = BENCH / "codes" / spec["orig"]
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")

    rid = f"topup_p3b_{spec['family']}_{spec['op_name']}"
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
            return {**spec, "record_id": rid, "status": "fail_orig_exec"}

    try:
        gt_text = splice_gt_code(orig_text, spec["op_code"])
    except Exception as e:
        return {**spec, "record_id": rid, "status": "fail_splice",
                "err": str(e)}
    gt_out_code.write_text(gt_text)

    ok, err = exec_cq(gt_text, gt_out_step, timeout=45)
    if not ok:
        return {**spec, "record_id": rid, "status": "fail_gt_exec"}

    try:
        from bench.metrics import compute_iou
        iou, _ = compute_iou(str(orig_out_step), str(gt_out_step))
    except Exception:
        iou = None

    if iou is None:
        status = "fail_iou"
    elif iou >= 0.99:
        status = "fail_iou_too_high"
    elif iou < 0.3:
        status = "fail_iou_too_low"
    else:
        status = "ok"

    return {
        **spec,
        "record_id": rid,
        "status": status,
        "orig_code_path": str(orig_out_code.relative_to(OUT)),
        "gt_code_path": str(gt_out_code.relative_to(OUT)),
        "orig_step_path": str(orig_out_step.relative_to(OUT)),
        "gt_step_path": str(gt_out_step.relative_to(OUT)),
        "iou": iou,
    }


def main():
    ap = argparse.ArgumentParser()
    args = ap.parse_args()

    # Load Phase-2 records, drop add_boss
    p2_recs = [
        json.loads(ln) for ln in
        (PHASE2 / "records.jsonl").read_text().splitlines() if ln
    ]
    kept_p2 = [r for r in p2_recs if r["edit_type"] != "add_boss"]
    p2_types_by_fam: dict[str, set] = {}
    for r in kept_p2:
        p2_types_by_fam.setdefault(r["family"], set()).add(r["edit_type"])

    # Families needing topup (<2 non-boss ops)
    all_fams = sorted(EDIT_AXES.keys())
    need = {}
    for f in all_fams:
        have = len(p2_types_by_fam.get(f, set()))
        if have < 2:
            need[f] = 2 - have
    print(f"families needing topup (<2 non-boss): {len(need)}")

    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    new_kept: list[dict] = []
    per_family_report: dict = {}
    fams = sorted(need.keys())
    for i, f in enumerate(fams):
        orig_path = pick_orig(f)
        if orig_path is None:
            per_family_report[f] = {"kept": 0, "reason": "no_orig"}
            continue
        orig_step = BENCH / "steps" / (orig_path.stem + ".step")
        try:
            xl, yl, zl = load_bbox(orig_step)
        except Exception:
            per_family_report[f] = {"kept": 0, "reason": "bbox_fail"}
            continue
        if min(xl, yl, zl) < 0.5:
            per_family_report[f] = {"kept": 0, "reason": "degenerate_bbox"}
            continue

        existing_types = p2_types_by_fam.get(f, set())
        palette = build_extended_palette(
            f, orig_path.name, xl, yl, zl, existing_types
        )
        fam_kept: list[dict] = []
        kept_types: set = set()
        target = need[f]

        # First: prefer new diverse type
        for spec in palette:
            if len(fam_kept) >= target:
                break
            if spec["edit_type"] in kept_types:
                continue
            rec = process_spec(spec, codes_dir, steps_dir)
            if rec["status"] == "ok":
                fam_kept.append(rec)
                kept_types.add(rec["edit_type"])

        # Fall back: any op works
        if len(fam_kept) < target:
            for spec in palette:
                if len(fam_kept) >= target:
                    break
                rid_try = f"topup_p3b_{spec['family']}_{spec['op_name']}"
                if any(r["record_id"] == rid_try for r in fam_kept):
                    continue
                rec = process_spec(spec, codes_dir, steps_dir)
                if rec["status"] == "ok":
                    fam_kept.append(rec)

        per_family_report[f] = {"kept": len(fam_kept),
                                "types": list(kept_types)}
        new_kept.extend(fam_kept)
        print(f"[{i+1:3d}/{len(fams)}] {f}: existing={list(existing_types)} "
              f"+new={len(fam_kept)} types={list(kept_types)}", flush=True)

    solved = sum(1 for f, r in per_family_report.items()
                 if r["kept"] >= need[f])
    print(f"\nPhase-3b: fams fully topped up = {solved}/{len(fams)}")
    print(f"new records: {len(new_kept)}")

    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in new_kept)
    )
    (OUT / "per_family_report.json").write_text(
        json.dumps(per_family_report, indent=2)
    )

    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "num", "record_id", "family", "edit_type", "difficulty",
            "iou", "instruction"
        ])
        for idx, r in enumerate(new_kept, 1):
            w.writerow([
                idx, r["record_id"], r["family"], r["edit_type"],
                r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float) else "",
                r["instruction"],
            ])
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
