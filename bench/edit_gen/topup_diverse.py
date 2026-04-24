"""UA-20 topup v2 — per-family pick 2 diverse-type feature ops from a palette.

Palette (tried in priority order, non-hole first for diversity):
  1. add_fillet   — outer vertical edges
  2. add_chamfer  — outer vertical edges
  3. add_slot     — top face rect slot
  4. add_feature  — hex socket cut on top
  5. add_boss     — cylindrical boss extruded from top
  6. add_hole     — axial (Z) through-hole
  7. add_hole     — radial (X) cross-hole

For each family, try ops in order, keep those that:
  - build ok (gt exec returns ok)
  - 0.3 < IoU(orig, gt) < 0.99

Stop once 2 ops with **different edit_type** are kept.

Output → data/data_generation/bench_edit/topup_diverse/
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
OUT = BENCH / "topup_diverse"


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


def build_palette(
    family: str, orig: str, xl: float, yl: float, zl: float
) -> list[dict]:
    """7 candidate ops, sized by bbox. Same family prefix, different op names."""
    min_xy = min(xl, yl)
    min_yz = min(yl, zl)
    # Sizes — keep reasonable bounds so IoU change is noticeable but OCCT won't bork
    fillet_r = clamp(0.06 * min_xy, 1.0, 8.0)
    cham_d = clamp(0.05 * min_xy, 0.8, 6.0)
    top_cham_d = clamp(0.08 * zl, 1.0, 6.0)
    slot_L = clamp(0.4 * max(xl, yl), 10.0, 80.0)
    slot_W = clamp(0.15 * min_xy, 3.0, 15.0)
    slot_D = clamp(0.2 * zl, 2.0, 10.0)
    hex_D = clamp(0.2 * min_xy, 4.0, 15.0)
    hex_depth = clamp(0.25 * zl, 2.0, 8.0)
    boss_r = clamp(0.1 * min_xy, 2.0, 10.0)
    boss_h = clamp(0.2 * zl, 3.0, 15.0)
    axial_r = clamp(0.12 * min_xy, 1.5, 20.0)
    axial_L = max(60.0, 3.0 * zl)
    radial_r = clamp(0.12 * min_yz, 1.5, 20.0)
    radial_L = max(60.0, 3.0 * xl)

    base = {"family": family, "orig": orig}
    return [
        {**base, "op_name": "outer_fillet",
         "edit_type": "add_fillet", "difficulty": "easy",
         "instruction": f"Fillet the outer vertical edges by {fillet_r:.1f} mm.",
         "op_code": f"result = result.edges('|Z').fillet({fillet_r:.2f})"},
        {**base, "op_name": "outer_chamfer",
         "edit_type": "add_chamfer", "difficulty": "easy",
         "instruction": f"Chamfer the outer vertical edges by {cham_d:.1f} mm.",
         "op_code": f"result = result.edges('|Z').chamfer({cham_d:.2f})"},
        {**base, "op_name": "top_slot",
         "edit_type": "add_slot", "difficulty": "medium",
         "instruction": (f"Cut a {slot_L:.0f}×{slot_W:.0f} mm slot "
                         f"{slot_D:.0f} mm deep into the top face."),
         "op_code": (f"result = result.faces('>Z').workplane("
                     f"centerOption='CenterOfBoundBox').slot2D("
                     f"{slot_L:.2f},{slot_W:.2f}).cutBlind(-{slot_D:.2f})")},
        {**base, "op_name": "hex_socket",
         "edit_type": "add_feature", "difficulty": "medium",
         "instruction": (f"Cut a {hex_D:.0f} mm across-flats hex socket "
                         f"{hex_depth:.0f} mm deep on the top face."),
         "op_code": (f"result = result.faces('>Z').workplane("
                     f"centerOption='CenterOfBoundBox').polygon(6,"
                     f"{hex_D:.2f}).cutBlind(-{hex_depth:.2f})")},
        {**base, "op_name": "top_boss",
         "edit_type": "add_boss", "difficulty": "medium",
         "instruction": (f"Add a {2*boss_r:.0f} mm diameter boss "
                         f"{boss_h:.0f} mm tall on the top face."),
         "op_code": (f"result = result.union(result.faces('>Z').workplane("
                     f"centerOption='CenterOfBoundBox').circle({boss_r:.2f})"
                     f".extrude({boss_h:.2f}))")},
        {**base, "op_name": "axial_hole",
         "edit_type": "add_hole", "difficulty": "easy",
         "instruction": (f"Drill a {2*axial_r:.0f} mm diameter through-hole "
                         f"along the Z axis."),
         "op_code": (f"result = result.cut(cq.Workplane('XY').cylinder("
                     f"{axial_L:.1f},{axial_r:.2f}))")},
        {**base, "op_name": "radial_hole",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*radial_r:.0f} mm diameter cross-hole "
                         f"through the part along the X axis."),
         "op_code": (f"result = result.cut(cq.Workplane('YZ').cylinder("
                     f"{radial_L:.1f},{radial_r:.2f}))")},
    ]


def process_spec(spec: dict, codes_dir: Path, steps_dir: Path) -> dict:
    orig_path = BENCH / "codes" / spec["orig"]
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")

    rid = f"topup_{spec['family']}_{spec['op_name']}"
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
            return {**spec, "record_id": rid, "status": "fail_orig_exec",
                    "err": err}

    try:
        gt_text = splice_gt_code(orig_text, spec["op_code"])
    except Exception as e:
        return {**spec, "record_id": rid, "status": "fail_splice",
                "err": str(e)}
    gt_out_code.write_text(gt_text)

    ok, err = exec_cq(gt_text, gt_out_step, timeout=45)
    if not ok:
        return {**spec, "record_id": rid, "status": "fail_gt_exec",
                "err": err}

    try:
        from bench.metrics import compute_iou
        iou, iou_err = compute_iou(str(orig_out_step), str(gt_out_step))
    except Exception as e:
        iou, iou_err = None, str(e)[:200]

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
    ap.add_argument("--only", default=None, help="family name substring filter")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    fams = sorted(EDIT_AXES.keys())
    if args.only:
        fams = [f for f in fams if args.only in f]

    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    kept: list[dict] = []
    rejected: list[dict] = []
    per_family_report: dict = {}

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
        if min(xl, yl, zl) < 2.0:
            per_family_report[f] = {"kept": 0, "reason": "degenerate_bbox"}
            continue

        palette = build_palette(f, orig_path.name, xl, yl, zl)
        fam_kept: list[dict] = []
        kept_types: set = set()

        for spec in palette:
            if len(fam_kept) >= 2 and len(kept_types) >= 2:
                break
            # Skip if type already picked (want diversity)
            if spec["edit_type"] in kept_types:
                continue
            rec = process_spec(spec, codes_dir, steps_dir)
            if rec["status"] == "ok":
                fam_kept.append(rec)
                kept_types.add(rec["edit_type"])
            else:
                rejected.append(rec)

        # If fewer than 2, allow same-type duplicates from remaining palette
        if len(fam_kept) < 2:
            for spec in palette:
                if len(fam_kept) >= 2:
                    break
                rid_try = f"topup_{spec['family']}_{spec['op_name']}"
                if any(r["record_id"] == rid_try for r in fam_kept):
                    continue
                rec = process_spec(spec, codes_dir, steps_dir)
                if rec["status"] == "ok":
                    fam_kept.append(rec)
                else:
                    # already in rejected list
                    pass

        per_family_report[f] = {"kept": len(fam_kept),
                                "types": list(kept_types)}
        kept.extend(fam_kept)
        print(f"[{i+1:3d}/{len(fams)}] {f}: kept={len(fam_kept)} "
              f"types={list(kept_types)}", flush=True)

    # Stats
    fam_2plus = sum(1 for f, r in per_family_report.items() if r["kept"] >= 2)
    fam_1 = sum(1 for f, r in per_family_report.items() if r["kept"] == 1)
    fam_0 = sum(1 for f, r in per_family_report.items() if r["kept"] == 0)
    print(f"\nfamilies: ≥2 kept = {fam_2plus}, =1 kept = {fam_1}, "
          f"=0 kept = {fam_0}")
    print(f"total kept records: {len(kept)}")
    type_counts = {}
    for r in kept:
        type_counts[r["edit_type"]] = type_counts.get(r["edit_type"], 0) + 1
    print(f"type distribution: {type_counts}")

    # jsonl + csv
    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in kept)
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
        for idx, r in enumerate(kept, 1):
            w.writerow([
                idx, r["record_id"], r["family"], r["edit_type"],
                r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float) else "",
                r["instruction"],
            ])
    print(f"\nwrote {csv_path}")

    if not args.no_preview and kept:
        import bench.edit_gen.topup_edits as te
        te.OUT = OUT
        te.build_preview_mosaic(kept, OUT / "preview.png")


if __name__ == "__main__":
    main()
