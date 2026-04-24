"""Add translate + scale ops for 14 families that only have rotate records.

For each, emit 1 translate (X+10mm) + 1 scale (1.2x) gt. Combined with existing
rotate records, each family gets 3 diverse ops: rotate, translate, scale.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bench.edit_gen.topup_edits import exec_cq, splice_gt_code

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_transform"

FAMILIES = [
    "connector_faceplate", "cotter_pin", "fan_shroud", "i_beam",
    "j_hook", "pipe_elbow", "pull_handle", "rect_frame",
    "spacer_ring", "taper_pin", "turnbuckle", "u_channel",
    "vented_panel", "venturi_tube",
]


def pick_orig(family: str) -> Path | None:
    codes = BENCH / "codes"
    steps = BENCH / "steps"
    for c in [codes / f"{family}_easy_r0_orig.py",
              codes / f"{family}_hard_r0_orig.py",
              *sorted(codes.glob(f"{family}_gid*_orig.py"))]:
        if c.exists() and (steps / (c.stem + ".step")).exists():
            return c
    return None


def process(family: str, op_name: str, edit_type: str, difficulty: str,
            instruction: str, op_code: str,
            codes_dir: Path, steps_dir: Path) -> dict | None:
    orig_path = pick_orig(family)
    if orig_path is None:
        return None
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    rid = f"topup_xf_{family}_{op_name}"
    orig_out = codes_dir / f"{rid}_orig.py"
    gt_out = codes_dir / f"{rid}_gt.py"
    orig_step = steps_dir / f"{rid}_orig.step"
    gt_step = steps_dir / f"{rid}_gt.step"
    orig_out.write_text(orig_text)
    if orig_step_src.exists():
        orig_step.write_bytes(orig_step_src.read_bytes())
    gt_out.write_text(splice_gt_code(orig_text, op_code))
    ok, err = exec_cq(gt_out.read_text(), gt_step, timeout=30)
    if not ok:
        return {"family": family, "record_id": rid, "status": "fail",
                "err": err}
    from bench.metrics import compute_iou
    iou, _ = compute_iou(str(orig_step), str(gt_step))
    return {
        "record_id": rid, "family": family, "edit_type": edit_type,
        "difficulty": difficulty, "instruction": instruction,
        "op_name": op_name, "iou": iou,
        "orig_code_path": f"codes/{rid}_orig.py",
        "gt_code_path": f"codes/{rid}_gt.py",
        "orig_step_path": f"steps/{rid}_orig.step",
        "gt_step_path": f"steps/{rid}_gt.step",
        "status": "ok",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    kept = []
    for f in FAMILIES:
        # Translate: shift +10mm along X
        r = process(
            f, "translate_X10", "translate", "easy",
            "Translate the entire part by 10 mm along the +X axis.",
            "result = result.translate((10, 0, 0))",
            codes_dir, steps_dir,
        )
        if r and r["status"] == "ok":
            kept.append(r)
            print(f"{f} translate_X10 IoU={r['iou']:.3f}")
        # Scale: uniform 1.2x — use val().scale then re-wrap
        r = process(
            f, "scale_1p2", "scale", "medium",
            "Scale the entire part uniformly by a factor of 1.2.",
            "import cadquery as _cq\n"
            "result = _cq.Workplane(obj=result.val().scale(1.2))",
            codes_dir, steps_dir,
        )
        if r and r["status"] == "ok":
            kept.append(r)
            print(f"{f} scale_1p2 IoU={r['iou']:.3f}")
        elif r:
            print(f"{f} scale FAIL: {r.get('err','')[:100]}")

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
