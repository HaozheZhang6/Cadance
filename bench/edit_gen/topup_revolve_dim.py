"""Dim-topup for 13 families with revolve/lineTo/polyline-based orig.

For each, edit a specific lineTo/cylinder/extrude/threePointArc numeric literal
that represents a meaningful dim (radius, height, shelf width, etc.).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from bench.edit_gen.topup_edits import exec_cq

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
FINAL = BENCH / "topup_final"


# (family, orig_file, list of (search, replace, instruction))
SPECS = [
    # bellows — a revolved profile with bellows waves. Change outer radius at
    # 22.9 (first wave) → 30 (thicker bellows).
    ("bellows", "bellows_easy_r0_orig.py", [
        ("(22.9, 0.0)", "(30.0, 0.0)",
         "Increase the bellows outer radius from 22.9 to 30."),
        ("convolution_height = 10.4", "convolution_height = 14.0",
         "N/A"),  # comment-only
    ]),
    # bucket — revolved. Change bottom outer radius 48.4 → 60.
    ("bucket", "bucket_easy_r0_orig.py", [
        ("(48.4, 0.0)", "(60.0, 0.0)",
         "Increase the bucket bottom outer radius from 48.4 to 60."),
        ("(56.1, 80.9)", "(70.0, 80.9)",
         "Increase the bucket top outer radius from 56.1 to 70."),
        ("(44.0, 5.9)", "(36.0, 5.9)",
         "Decrease the bucket inner bottom radius from 44 to 36 (thicker wall)."),
    ]),
    # dome_cap — the orig is buggy (revolve truncation). Use our user fix.
    # Skip here; user_dome_cap in manual already done.
    # lathe_turned_part — revolved. Change 29.7 → 38 (bigger disc).
    ("lathe_turned_part", "lathe_turned_part_easy_r0_orig.py", [
        ("(29.7, 0.0)", "(38.0, 0.0)",
         "Increase the outer disc radius from 29.7 to 38."),
        ("(11.95, 13.1)", "(11.95, 18.0)",
         "Move the step up from Z=13.1 to Z=18."),
        ("(11.95, 24.4)", "(11.95, 32.0)",
         "Increase the top-step height from 24.4 to 32."),
    ]),
    # nozzle — revolve along X. lineTo(70.1, 7.0) = outlet profile endpoint.
    ("nozzle", "nozzle_easy_r0_orig.py", [
        ("(70.1, 7.0)", "(90.0, 7.0)",
         "Increase the nozzle length from 70.1 to 90."),
        ("(0.0, 20.3)", "(0.0, 26.0)",
         "Increase the inlet radius from 20.3 to 26."),
        ("(70.1, 4.9)", "(70.1, 3.0)",
         "Narrow the outlet radius from 4.9 to 3."),
    ]),
    # venturi_tube — revolve along Y. Change main bore radius.
    ("venturi_tube", "venturi_tube_easy_r0_orig.py", [
        # Inspect actual lineTo first — run separately
    ]),
    # bevel_gear — loft of 2 polylines. Dim by changing face_width/extrude.
    ("bevel_gear", "bevel_gear_easy_r0_orig.py", [
        (".hole(8.4)", ".hole(12.0)",
         "Widen the bore from 8.4 to 12."),
        (".hole(8.4)", ".hole(16.0)",
         "Widen the bore from 8.4 to 16."),
    ]),
    # circlip — thin polyline ring. Change thickness (extrude 1.2).
    ("circlip", "circlip_easy_r0_orig.py", [
        (".extrude(1.2)", ".extrude(2.0)",
         "Increase the ring thickness from 1.2 to 2."),
        (".extrude(1.2)", ".extrude(3.0)",
         "Increase the ring thickness from 1.2 to 3."),
    ]),
    # clevis_pin — simple cylinder 100×2.5. Change both dims.
    ("clevis_pin", "clevis_pin_easy_r0_orig.py", [
        (".cylinder(100.0, 2.5)", ".cylinder(80.0, 2.5)",
         "Shorten the pin length from 100 to 80."),
        (".cylinder(100.0, 2.5)", ".cylinder(100.0, 4.0)",
         "Thicken the pin radius from 2.5 to 4."),
        (".chamfer(0.5)", ".chamfer(1.0)",
         "Increase the end chamfer from 0.5 to 1."),
    ]),
    # grommet — revolved polyline. Change OD 4.75 → 6.
    ("grommet", "grommet_easy_r0_orig.py", [
        ("(4.75, 0.0)", "(6.0, 0.0)",
         "Increase the grommet outer radius from 4.75 to 6."),
        ("(4.75, 1.6)", "(6.0, 1.6)",
         "Increase the grommet outer radius at flange from 4.75 to 6."),
    ]),
    # i_beam — extrude-based. Change total_height (120.0 → 160).
    ("i_beam", "i_beam_hard_r0_orig.py", [
        ("(0.0, 120.0)", "(0.0, 160.0)",
         "Increase the I-beam total height from 120 to 160."),
        ("(32.0, 6.3)", "(40.0, 6.3)",
         "Widen the flange half-width from 32 to 40."),
    ]),
    # piston — revolved polyline. Change top radius 28.9.
    ("piston", "piston_easy_r0_orig.py", [
        ("(28.9, 0.0)", "(36.0, 0.0)",
         "Increase the piston outer radius from 28.9 to 36."),
        ("(28.9, 67.1)", "(28.9, 90.0)",
         "Increase the piston length from 67.1 to 90."),
    ]),
    # taper_pin — polyline. Change big-end radius 2.2.
    ("taper_pin", "taper_pin_easy_r0_orig.py", [
        ("(2.2, 70.0)", "(3.5, 70.0)",
         "Increase the big-end radius from 2.2 to 3.5."),
        ("(2.2, 70.0)", "(1.0, 70.0)",
         "Decrease the big-end radius from 2.2 to 1."),
    ]),
]


def process(fam, orig_file, subs, recs):
    orig_path = BENCH / "codes" / orig_file
    if not orig_path.exists():
        print(f"  {fam}: orig missing")
        return []
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    codes_dir = FINAL / "codes"
    steps_dir = FINAL / "steps"
    kept = []
    for i, (search, replace, inst) in enumerate(subs):
        if search not in orig_text or search == replace or inst.startswith("N/A"):
            continue
        gt_text = orig_text.replace(search, replace, 1)
        if gt_text == orig_text:
            continue
        rid = f"user_{fam}_dim{i+1}"
        orig_py = codes_dir/f"{rid}_orig.py"
        gt_py = codes_dir/f"{rid}_gt.py"
        orig_step = steps_dir/f"{rid}_orig.step"
        gt_step = steps_dir/f"{rid}_gt.step"
        orig_py.write_text(orig_text)
        gt_py.write_text(gt_text)
        if orig_step_src.exists():
            shutil.copy(orig_step_src, orig_step)
        else:
            ok, err = exec_cq(orig_text, orig_step, timeout=30)
            if not ok: continue
        ok, err = exec_cq(gt_text, gt_step, timeout=30)
        if not ok:
            print(f"  {fam} dim{i+1}: gt exec fail: {err[:80]}")
            orig_py.unlink(); gt_py.unlink()
            if gt_step.exists(): gt_step.unlink()
            continue
        from bench.metrics import compute_iou
        iou, _ = compute_iou(str(orig_step), str(gt_step))
        if iou is None or iou >= 0.99 or iou < 0.1:
            print(f"  {fam} dim{i+1}: IoU={iou:.3f} rejected")
            orig_py.unlink(); gt_py.unlink()
            if gt_step.exists(): gt_step.unlink()
            continue
        print(f"  {fam} dim{i+1}: IoU={iou:.3f} OK")
        kept.append({
            "record_id": rid, "family": fam, "edit_type": "dim",
            "difficulty": "easy", "instruction": inst, "iou": iou,
            "source": "user_dim",
            "orig_code_path": f"codes/{rid}_orig.py",
            "gt_code_path": f"codes/{rid}_gt.py",
            "orig_step_path": f"steps/{rid}_orig.step",
            "gt_step_path": f"steps/{rid}_gt.step",
            "status": "ok",
        })
    return kept


def main():
    recs = [json.loads(l) for l in (FINAL/"records.jsonl").read_text().splitlines() if l]
    for fam, orig_file, subs in SPECS:
        got = process(fam, orig_file, subs, recs)
        recs.extend(got)
    diff_rank = {"easy":0,"medium":1,"hard":2}
    recs.sort(key=lambda r: (r["family"], diff_rank.get(r.get("difficulty","medium"),9), r["record_id"]))
    (FINAL/"records.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
    # stats
    fam_cnt = {}
    for r in recs: fam_cnt[r["family"]] = fam_cnt.get(r["family"],0)+1
    from bench.edit_gen.edit_axes import EDIT_AXES
    still = [f for f in EDIT_AXES if fam_cnt.get(f,0) < 3]
    print(f"\ntotal: {len(recs)}  ≥3: {sum(1 for v in fam_cnt.values() if v>=3)}/106")
    print(f"still <3: {still}")


if __name__ == "__main__":
    main()
