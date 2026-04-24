"""Dim-change edits for 14 families: modify ONE hardcoded value in orig code.

Each spec: family, orig file, search string, replace string, instruction.
Much simpler than re-rendering features: orig and gt differ only in 1 number.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bench.edit_gen.topup_edits import exec_cq

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_dim"


SPECS = [
    # connector_faceplate — length 123.2 → 150
    ("connector_faceplate", "connector_faceplate_hard_r0_orig.py",
     ".box(123.2,", ".box(150.0,",
     "Change the faceplate length from 123.2 mm to 150 mm."),
    # cotter_pin — long_leg cylinder 10.0 → 14.0
    ("cotter_pin", "cotter_pin_easy_r0_orig.py",
     "cylinder(10.0, 1.25)", "cylinder(14.0, 1.25)",
     "Change the pin leg length from 10 mm to 14 mm."),
    # fan_shroud — fan_radius 76.2 → 50 (changes hole/plate ratio)
    ("fan_shroud", "fan_shroud_easy_r0_orig.py",
     ".circle(76.2)", ".circle(50.0)",
     "Change the fan hole radius from 76.2 mm to 50 mm."),
    # i_beam — flange_width 64.0 → 100
    ("i_beam", "i_beam_hard_r0_orig.py",
     "flange_width = 64.0", "flange_width = 100.0_UNUSED",
     "Change the flange width from 64 mm to 100 mm."),
    # j_hook — hook_inner_D 30.0 → 50
    ("j_hook", "j_hook_easy_r0_orig.py",
     "hook_inner_D = 30.0", "hook_inner_D = 50.0_UNUSED",
     "Change the hook inner diameter from 30 mm to 50 mm."),
    # pipe_elbow — outer_radius 21.1 → 30
    ("pipe_elbow", "pipe_elbow_easy_r0_orig.py",
     ".circle(21.1)", ".circle(30.0)",
     "Change the outer radius from 21.1 mm to 30 mm."),
    # pull_handle — bar_diameter 10.2 → 14 (finds circle(5.1) = d/2)
    ("pull_handle", "pull_handle_easy_r0_orig.py",
     ".cylinder(32.9, 5.1)", ".cylinder(32.9, 7.0)",
     "Change the bar diameter from 10.2 mm to 14 mm."),
    # rect_frame — outer_length 60.0 → 80
    ("rect_frame", "rect_frame_easy_r0_orig.py",
     ".rect(60.0, 100.0)", ".rect(80.0, 100.0)",
     "Change the frame outer length from 60 mm to 80 mm."),
    # spacer_ring — outer_diameter 10.0 → 14 (radius 5 → 7)
    ("spacer_ring", "spacer_ring_easy_r0_orig.py",
     "cylinder(0.5, 5.0)", "cylinder(0.5, 7.0)",
     "Change the spacer outer diameter from 10 mm to 14 mm."),
    # taper_pin — d_large 4.4 → 8 (changes taper ratio)
    ("taper_pin", "taper_pin_easy_r0_orig.py",
     "4.4", "8.0",
     "Change the large-end diameter from 4.4 mm to 8 mm."),
    # turnbuckle — boss_d 22.0 → 40 (changes boss/body ratio)
    ("turnbuckle", "turnbuckle_easy_r0_orig.py",
     "22.0", "40.0",
     "Change the boss diameter from 22 mm to 40 mm."),
    # u_channel — length 300.0 → 400
    ("u_channel", "u_channel_easy_r0_orig.py",
     ".box(33.0, 300.0, 30.0)", ".box(33.0, 400.0, 30.0)",
     "Change the channel length from 300 mm to 400 mm."),
    # u_channel GT channel cut length also needs to match
    # but we leave wall cut as-is intentionally — user wants ONE param change
    # vented_panel — slot_width 6.8 → 14 (wider vents)
    ("vented_panel", "vented_panel_hard_r0_orig.py",
     "6.8", "14.0",
     "Change the vent slot width from 6.8 mm to 14 mm."),
    # venturi_tube — throat_diameter 117.4 → 70 (tighter throat)
    ("venturi_tube", "venturi_tube_easy_r0_orig.py",
     "117.4", "70.0",
     "Change the throat diameter from 117.4 mm to 70 mm."),
]


def process(spec) -> dict:
    family, orig_file, search, replace, instruction = spec
    orig_path = BENCH / "codes" / orig_file
    orig_text = orig_path.read_text()
    if search not in orig_text:
        return {"family": family, "status": "fail_search_missing",
                "search": search[:40]}
    gt_text = orig_text.replace(search, replace, 1)  # first occurrence
    if gt_text == orig_text:
        return {"family": family, "status": "fail_no_change"}
    rid = f"topup_dim_{family}"
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)
    orig_out = codes_dir / f"{rid}_orig.py"
    gt_out = codes_dir / f"{rid}_gt.py"
    orig_step = steps_dir / f"{rid}_orig.step"
    gt_step = steps_dir / f"{rid}_gt.step"
    orig_out.write_text(orig_text)
    gt_out.write_text(gt_text)
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    if orig_step_src.exists():
        orig_step.write_bytes(orig_step_src.read_bytes())
    else:
        ok, err = exec_cq(orig_text, orig_step, timeout=30)
        if not ok:
            return {"family": family, "record_id": rid,
                    "status": "fail_orig_exec", "err": err}
    ok, err = exec_cq(gt_text, gt_step, timeout=30)
    if not ok:
        return {"family": family, "record_id": rid,
                "status": "fail_gt_exec", "err": err}
    from bench.metrics import compute_iou
    iou, _ = compute_iou(str(orig_step), str(gt_step))
    return {
        "record_id": rid,
        "family": family,
        "edit_type": "dim",
        "difficulty": "easy",
        "instruction": instruction,
        "iou": iou,
        "orig_code_path": f"codes/{rid}_orig.py",
        "gt_code_path": f"codes/{rid}_gt.py",
        "orig_step_path": f"steps/{rid}_orig.step",
        "gt_step_path": f"steps/{rid}_gt.step",
        "status": "ok" if iou is not None and iou < 0.99 else "iou_too_high",
    }


def main():
    kept = []
    for s in SPECS:
        r = process(s)
        iou = r.get("iou")
        iou_s = f"{iou:.3f}" if isinstance(iou, float) else "?"
        print(f"{s[0]}: status={r['status']} IoU={iou_s}  inst: {s[-1]}")
        if r["status"] == "ok":
            kept.append(r)
        else:
            print(f"  err: {r.get('err', '')[:120]}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in kept)
    )
    with (OUT / "manifest.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["num", "record_id", "family", "edit_type", "difficulty",
                    "iou", "instruction"])
        for i, r in enumerate(kept, 1):
            w.writerow([i, r["record_id"], r["family"], r["edit_type"],
                        r["difficulty"],
                        f"{r.get('iou'):.4f}" if isinstance(r.get('iou'),
                                                            float) else "",
                        r["instruction"]])
    print(f"\nkept {len(kept)} dim records")


if __name__ == "__main__":
    main()
