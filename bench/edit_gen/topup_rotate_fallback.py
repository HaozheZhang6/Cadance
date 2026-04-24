"""UA-20 Phase 3c — rotate-90° fallback for families still <2 after Phase 3b.

For any family where Phase 2 (non-boss) + Phase 3b combined yields <2 edits,
emit a trivial `rotate((0,0,0),(1,0,0),90)` gt. Rotation around X gives a
geometric change for most parts (bbox flips y↔z, content re-oriented).

Skips cylindrical / spherical parts whose rotation would be invariant.
Those families have to be hand-fixed — they go in a `still_missing.txt` list.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bench.edit_gen.edit_axes import EDIT_AXES
from bench.edit_gen.topup_edits import exec_cq, splice_gt_code

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_rotate"


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


def process_rotation(family: str, axis: str, deg: int,
                     codes_dir: Path, steps_dir: Path) -> dict:
    """axis in {'X','Y','Z'}; rotation around that axis by `deg`."""
    orig_path = pick_orig(family)
    if orig_path is None:
        return {"family": family, "status": "fail_no_orig"}
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")

    rid = f"topup_rot_{family}_rotate_{axis}{deg}"
    axis_vec = {"X": "(1,0,0)", "Y": "(0,1,0)", "Z": "(0,0,1)"}[axis]
    op_code = f"result = result.rotate((0,0,0), {axis_vec}, {deg})"
    instruction = f"Rotate the entire part by {deg}° about the {axis} axis."

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
            return {"family": family, "record_id": rid,
                    "status": "fail_orig_exec"}

    gt_text = splice_gt_code(orig_text, op_code)
    gt_out_code.write_text(gt_text)

    ok, err = exec_cq(gt_text, gt_out_step, timeout=30)
    if not ok:
        return {"family": family, "record_id": rid, "status": "fail_gt_exec"}

    try:
        from bench.metrics import compute_iou
        iou, _ = compute_iou(str(orig_out_step), str(gt_out_step))
    except Exception:
        iou = None

    if iou is None:
        status = "fail_iou"
    elif iou >= 0.99:
        status = "fail_iou_too_high"  # rotation-invariant (cylinder about own axis)
    else:
        status = "ok"

    return {
        "record_id": rid,
        "family": family,
        "edit_type": "rotate",
        "difficulty": "easy",
        "op_name": f"rotate_{axis}{deg}",
        "instruction": instruction,
        "orig_code_path": f"codes/{rid}_orig.py",
        "gt_code_path": f"codes/{rid}_gt.py",
        "orig_step_path": f"steps/{rid}_orig.step",
        "gt_step_path": f"steps/{rid}_gt.step",
        "status": status,
        "iou": iou,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", default=None,
                    help="comma-separated family list; default = read from "
                    "topup_final/coverage_report.json")
    args = ap.parse_args()

    if args.families:
        fams = [f.strip() for f in args.families.split(",") if f.strip()]
    else:
        cov = json.loads(
            (BENCH / "topup_final" / "coverage_report.json").read_text()
        )
        fams = [f for f, rs in cov["by_family"].items() if len(rs) < 2]
        missing = sorted(set(EDIT_AXES.keys()) - set(cov["by_family"].keys()))
        fams = sorted(set(fams + missing))
    print(f"rotate fallback for {len(fams)} families: {fams}")

    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    kept: list[dict] = []
    for i, f in enumerate(fams):
        # Try X first, then Y, then Z (last resort — may be invariant)
        for axis in ["X", "Y", "Z"]:
            rec = process_rotation(f, axis, 90, codes_dir, steps_dir)
            if rec["status"] == "ok":
                kept.append(rec)
                print(f"[{i+1:3d}/{len(fams)}] {f} rotate_{axis}90 "
                      f"IoU={rec['iou']:.3f}", flush=True)
                break
        else:
            print(f"[{i+1:3d}/{len(fams)}] {f} ALL axes invariant/fail",
                  flush=True)

    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in kept)
    )
    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["num", "record_id", "family", "edit_type", "iou",
                    "instruction"])
        for idx, r in enumerate(kept, 1):
            w.writerow([
                idx, r["record_id"], r["family"], r["edit_type"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float)
                else "",
                r["instruction"],
            ])
    print(f"\nkept: {len(kept)}/{len(fams)}")


if __name__ == "__main__":
    main()
