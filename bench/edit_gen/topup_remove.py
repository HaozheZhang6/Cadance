"""Reverse add_*_orig/gt pairs → remove_* edits.

For each family that has {fam}_add_*_orig.py + _gt.py + matching .step, create
a remove edit where new_orig = old_gt (has feature), new_gt = old_orig (base).
Instruction: "Remove the added [feature]."

Also hand-crafts remove edits for cotter_pin (drop one leg) and u_channel
(drop the inner cut) by editing orig code directly.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from bench.edit_gen.topup_edits import exec_cq, splice_gt_code

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_remove"

# 7 families with add_X pairs reversible
REVERSE_PAIRS = [
    ("connector_faceplate", "add_hole",
     "Remove the through-hole from the faceplate."),
    ("fan_shroud", "add_hole",
     "Remove the through-hole from the shroud."),
    ("i_beam", "add_hole",
     "Remove the through-hole from the beam web."),
    ("rect_frame", "add_hole",
     "Remove the through-hole from the frame."),
    ("spacer_ring", "add_hole",
     "Remove the through-hole from the ring."),
    ("turnbuckle", "add_chamfer",
     "Remove the chamfer from the turnbuckle edges."),
    ("vented_panel", "add_chamfer",
     "Remove the chamfer from the panel edges."),
]

# Hand-crafted removals (replace orig → gt has one op deleted)
# cotter_pin: 2 cylinders union → drop second → single cylinder
HANDCRAFTED = [
    {
        "family": "cotter_pin",
        "orig_file": "cotter_pin_easy_r0_orig.py",
        "remove_target": "\n    .union(\n        cq.Workplane(\"XY\")\n            "
                         ".transformed(offset=cq.Vector(1.25, 0, -5.0), "
                         "rotate=cq.Vector(0, 0, 0))\n            "
                         ".cylinder(10.0, 1.25)\n    )",
        "instruction": "Remove the second pin leg, leaving only one cylindrical leg.",
        "op_name": "remove_second_leg",
    },
    {
        "family": "u_channel",
        "orig_file": "u_channel_easy_r0_orig.py",
        # orig: box + faces(>Z).workplane.rect.cutBlind; remove the cutBlind block
        "remove_target": "\n    .faces(\">Z\").workplane()\n    "
                         ".rect(19.0, 300.0)\n    .cutBlind(-23.0)",
        "instruction": "Remove the inner channel cut, leaving a solid block.",
        "op_name": "remove_channel",
    },
]


def process_reverse(family: str, op: str, instruction: str,
                    codes_dir: Path, steps_dir: Path) -> dict:
    src_codes = BENCH / "codes"
    src_steps = BENCH / "steps"
    rid = f"topup_rm_{family}_remove_{op.split('_')[1]}"
    # new_orig = old_gt
    (codes_dir / f"{rid}_orig.py").write_text(
        (src_codes / f"{family}_{op}_gt.py").read_text()
    )
    # new_gt = old_orig
    (codes_dir / f"{rid}_gt.py").write_text(
        (src_codes / f"{family}_{op}_orig.py").read_text()
    )
    shutil.copy(src_steps / f"{family}_{op}_gt.step",
                steps_dir / f"{rid}_orig.step")
    shutil.copy(src_steps / f"{family}_{op}_orig.step",
                steps_dir / f"{rid}_gt.step")
    from bench.metrics import compute_iou
    iou, _ = compute_iou(str(steps_dir / f"{rid}_orig.step"),
                          str(steps_dir / f"{rid}_gt.step"))
    return {
        "record_id": rid,
        "family": family,
        "edit_type": f"remove_{op.split('_')[1]}",
        "difficulty": "medium",
        "instruction": instruction,
        "op_name": f"remove_{op.split('_')[1]}",
        "iou": iou,
        "orig_code_path": f"codes/{rid}_orig.py",
        "gt_code_path": f"codes/{rid}_gt.py",
        "orig_step_path": f"steps/{rid}_orig.step",
        "gt_step_path": f"steps/{rid}_gt.step",
        "status": "ok" if iou is not None and iou < 0.99 else "iou_too_high",
    }


def process_handcrafted(spec: dict, codes_dir: Path,
                         steps_dir: Path) -> dict:
    orig_path = BENCH / "codes" / spec["orig_file"]
    orig_text = orig_path.read_text()
    target = spec["remove_target"]
    if target not in orig_text:
        return {**spec, "record_id": f"topup_rm_{spec['family']}_{spec['op_name']}",
                "status": "fail_target_not_found"}
    # new_orig = orig (has the feature)
    # new_gt = orig with target removed
    gt_text = orig_text.replace(target, "")
    rid = f"topup_rm_{spec['family']}_{spec['op_name']}"
    (codes_dir / f"{rid}_orig.py").write_text(orig_text)
    (codes_dir / f"{rid}_gt.py").write_text(gt_text)
    # orig step: copy existing
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    if orig_step_src.exists():
        shutil.copy(orig_step_src, steps_dir / f"{rid}_orig.step")
    else:
        ok, _ = exec_cq(orig_text, steps_dir / f"{rid}_orig.step")
        if not ok:
            return {**spec, "record_id": rid, "status": "fail_orig_exec"}
    # gt step: exec
    ok, err = exec_cq(gt_text, steps_dir / f"{rid}_gt.step", timeout=30)
    if not ok:
        return {**spec, "record_id": rid, "status": "fail_gt_exec",
                "err": err[:200] if err else ""}
    from bench.metrics import compute_iou
    iou, _ = compute_iou(
        str(steps_dir / f"{rid}_orig.step"),
        str(steps_dir / f"{rid}_gt.step"),
    )
    return {
        "record_id": rid,
        "family": spec["family"],
        "edit_type": "remove_feature",
        "difficulty": "medium",
        "instruction": spec["instruction"],
        "op_name": spec["op_name"],
        "iou": iou,
        "orig_code_path": f"codes/{rid}_orig.py",
        "gt_code_path": f"codes/{rid}_gt.py",
        "orig_step_path": f"steps/{rid}_orig.step",
        "gt_step_path": f"steps/{rid}_gt.step",
        "status": "ok" if iou is not None and iou < 0.99 else "iou_too_high",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    kept = []
    for fam, op, inst in REVERSE_PAIRS:
        rec = process_reverse(fam, op, inst, codes_dir, steps_dir)
        kept.append(rec)
        print(f"{fam} remove_{op.split('_')[1]} IoU={rec['iou']:.3f} "
              f"status={rec['status']}")
    for spec in HANDCRAFTED:
        rec = process_handcrafted(spec, codes_dir, steps_dir)
        iou = rec.get("iou")
        iou_s = f"{iou:.3f}" if isinstance(iou, float) else "?"
        print(f"{spec['family']} {spec['op_name']} IoU={iou_s} "
              f"status={rec['status']}")
        if rec["status"] == "ok":
            kept.append(rec)

    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in kept)
    )
    with (OUT / "manifest.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["num", "record_id", "family", "edit_type", "iou",
                    "instruction"])
        for i, r in enumerate(kept, 1):
            w.writerow([i, r["record_id"], r["family"], r["edit_type"],
                        f"{r.get('iou'):.4f}" if isinstance(r.get('iou'),
                                                            float) else "",
                        r["instruction"]])
    print(f"\nkept {len(kept)} records")


if __name__ == "__main__":
    main()
