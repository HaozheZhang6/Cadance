"""UA-20 Phase 3 — targeted topup for families that failed Phase 2.

Phase 2 (`topup_diverse`) left:
  - 13 families with 0 kept edits (revolved / thin pins)
  - 19 families with only 1 kept edit

Phase 3 expands the palette with:
  - circular-edge fillet/chamfer (for revolved shapes that have no |Z edges)
  - end-face chamfer (top/bottom) with small radius
  - offset axial/radial holes (position variation)
  - partial/offset slots

Sizes are aggressively scaled for small parts (thin pins).

Already-kept records in topup_diverse/records.jsonl are preserved; Phase 3
appends new records for the missing ones into topup_phase3/.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cadquery as cq
from OCP.STEPControl import STEPControl_Reader

from bench.edit_gen.topup_edits import exec_cq, splice_gt_code

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
PHASE2 = BENCH / "topup_diverse"
OUT = BENCH / "topup_phase3"


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
    family: str, orig: str, xl: float, yl: float, zl: float
) -> list[dict]:
    """Expanded palette — tries more edge selectors + end-face ops."""
    min_xy = min(xl, yl)
    min_yz = min(yl, zl)
    # For thin parts (pins ~3mm), use small sizes
    thin = min(xl, yl, zl) < 8.0

    # Circular edge ops (for revolved shapes)
    circle_r = clamp(0.05 * min_xy, 0.3 if thin else 1.0, 4.0)
    top_circle_cham = clamp(0.06 * min_xy, 0.2 if thin else 0.8, 3.0)
    # End face chamfers (small, targeted)
    end_cham = clamp(0.03 * min_xy, 0.2 if thin else 0.5, 2.0)
    # Offset holes — position hole off-center so it still cuts material
    ox = 0.25 * xl
    oy = 0.25 * yl
    off_hole_r = clamp(0.1 * min_xy, 0.8 if thin else 1.5, 10.0)
    hole_L = max(60.0, 3.0 * max(xl, yl, zl))
    # Axial hole at position (big, centered) — sometimes works where palette v2 failed
    axial_r = clamp(0.15 * min_xy, 1.0 if thin else 2.0, 15.0)
    # Radial hole
    radial_r = clamp(0.12 * min_yz, 1.0 if thin else 2.0, 12.0)
    # Slot offset
    slot_L = clamp(0.3 * max(xl, yl), 8.0, 60.0)
    slot_W = clamp(0.12 * min_xy, 2.0, 10.0)
    slot_D = clamp(0.15 * zl, 1.5, 6.0)

    base = {"family": family, "orig": orig}
    palette = [
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
        {**base, "op_name": "all_circle_chamfer",
         "edit_type": "add_chamfer", "difficulty": "medium",
         "instruction": f"Chamfer all circular edges by {end_cham:.1f} mm.",
         "op_code": f"result = result.edges('%CIRCLE').chamfer({end_cham:.2f})"},
        {**base, "op_name": "offset_axial_hole",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*off_hole_r:.0f} mm diameter hole "
                         f"along Z at position ({ox:.0f}, {oy:.0f})."),
         "op_code": (f"result = result.cut(cq.Workplane('XY')"
                     f".transformed(offset=cq.Vector({ox:.2f},{oy:.2f},0))"
                     f".cylinder({hole_L:.1f},{off_hole_r:.2f}))")},
        {**base, "op_name": "axial_hole",
         "edit_type": "add_hole", "difficulty": "easy",
         "instruction": (f"Drill a {2*axial_r:.0f} mm diameter through-hole "
                         f"along the Z axis."),
         "op_code": (f"result = result.cut(cq.Workplane('XY').cylinder("
                     f"{hole_L:.1f},{axial_r:.2f}))")},
        {**base, "op_name": "radial_hole",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*radial_r:.0f} mm diameter cross-hole "
                         f"along the X axis."),
         "op_code": (f"result = result.cut(cq.Workplane('YZ').cylinder("
                     f"{hole_L:.1f},{radial_r:.2f}))")},
        {**base, "op_name": "perpendicular_hole",
         "edit_type": "add_hole", "difficulty": "medium",
         "instruction": (f"Drill a {2*radial_r:.0f} mm diameter hole "
                         f"along the Y axis."),
         "op_code": (f"result = result.cut(cq.Workplane('XZ').cylinder("
                     f"{hole_L:.1f},{radial_r:.2f}))")},
        {**base, "op_name": "offset_top_slot",
         "edit_type": "add_slot", "difficulty": "medium",
         "instruction": (f"Cut a {slot_L:.0f}×{slot_W:.0f} mm slot "
                         f"{slot_D:.0f} mm deep into the top face."),
         "op_code": (f"result = result.faces('>Z').workplane("
                     f"centerOption='CenterOfBoundBox').slot2D("
                     f"{slot_L:.2f},{slot_W:.2f}).cutBlind(-{slot_D:.2f})")},
    ]
    return palette


def process_spec(spec: dict, codes_dir: Path, steps_dir: Path) -> dict:
    orig_path = BENCH / "codes" / spec["orig"]
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")

    rid = f"topup_p3_{spec['family']}_{spec['op_name']}"
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
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    # Load Phase-2 per-family report → identify families needing topup
    rep = json.loads((PHASE2 / "per_family_report.json").read_text())
    # Phase-2 existing kept counts per family
    need_more = {f: 2 - r["kept"] for f, r in rep.items() if r["kept"] < 2}
    print(f"families needing topup: {len(need_more)}")

    # Phase-2 already-kept types per family (avoid duplicate types if possible)
    p2_kept = {}
    for rec in (json.loads(ln) for ln in
                (PHASE2 / "records.jsonl").read_text().splitlines() if ln):
        p2_kept.setdefault(rec["family"], set()).add(rec["edit_type"])

    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    kept: list[dict] = []
    per_family_report: dict = {}

    fams = sorted(need_more.keys())
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

        existing_types = p2_kept.get(f, set())
        target = need_more[f]
        palette = build_extended_palette(f, orig_path.name, xl, yl, zl)

        fam_kept: list[dict] = []
        kept_types: set = set()

        # First pass: diverse types (prefer types not in Phase-2)
        for spec in palette:
            if len(fam_kept) >= target:
                break
            if spec["edit_type"] in existing_types:
                continue
            if spec["edit_type"] in kept_types:
                continue
            rec = process_spec(spec, codes_dir, steps_dir)
            if rec["status"] == "ok":
                fam_kept.append(rec)
                kept_types.add(rec["edit_type"])

        # Second pass: allow any type if still short
        if len(fam_kept) < target:
            for spec in palette:
                if len(fam_kept) >= target:
                    break
                rid_try = f"topup_p3_{spec['family']}_{spec['op_name']}"
                if any(r["record_id"] == rid_try for r in fam_kept):
                    continue
                rec = process_spec(spec, codes_dir, steps_dir)
                if rec["status"] == "ok":
                    fam_kept.append(rec)

        per_family_report[f] = {"kept": len(fam_kept),
                                "types": list(kept_types)}
        kept.extend(fam_kept)
        print(f"[{i+1:3d}/{len(fams)}] {f}: P2={list(existing_types)} "
              f"P3+{len(fam_kept)} types={list(kept_types)}", flush=True)

    print(f"\nPhase-3 kept records: {len(kept)}")
    solved = sum(1 for f, r in per_family_report.items()
                 if r["kept"] >= need_more[f])
    print(f"families fully topped up: {solved}/{len(fams)}")

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
    print(f"wrote {csv_path}")

    if not args.no_preview and kept:
        import bench.edit_gen.topup_edits as te
        te.OUT = OUT
        te.build_preview_mosaic(kept, OUT / "preview.png")


if __name__ == "__main__":
    main()
