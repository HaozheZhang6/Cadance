"""UA-20 topup — hand-authored feature-level edits on existing bench origs.

Each spec reuses an existing pair_builder orig and appends a CadQuery op to
produce gt. Exec'd in subprocess (via run_edit_code.exec_cq style), IoU gated,
then rendered as a composite preview mosaic with record_id labels + CSV.

Phase-1 outputs to data/data_generation/bench_edit/topup_phase1/{codes,steps,
preview.png,manifest.csv,records.jsonl}.

Usage:
    python -m bench.edit_gen.topup_edits
    python -m bench.edit_gen.topup_edits --only capsule_add_axial_hole
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_phase1"
LD = os.environ.get("LD_LIBRARY_PATH", "/workspace/.local/lib")

# ── 10 seed specs ─────────────────────────────────────────────────────────────
# Each: record_id / orig file / edit_type / instruction / op_code (str appended
# as `result = result.<op>` before show_object(result)).

SPECS: list[dict] = [
    {
        "record_id": "topup_capsule_add_axial_hole",
        "family": "capsule",
        "orig": "capsule_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Drill a 14 mm diameter through-hole along the long (Z) axis of the capsule.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').cylinder(400.0, 7.0))"
        ),
    },
    {
        "record_id": "topup_capsule_add_radial_hole",
        "family": "capsule",
        "orig": "capsule_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 16 mm diameter cross-hole through the capsule along the X axis.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').transformed(rotate=cq.Vector(0,90,0))"
            ".cylinder(400.0, 8.0))"
        ),
    },
    {
        "record_id": "topup_rect_frame_add_fillet",
        "family": "rect_frame",
        "orig": "rect_frame_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Round the four outer vertical corners of the frame with an 8 mm fillet.",
        "op_code": "result = result.edges('|Z').fillet(8.0)",
    },
    {
        "record_id": "topup_mesh_panel_add_center_hole",
        "family": "mesh_panel",
        "orig": "mesh_panel_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Add a 20 mm diameter through-hole at the center of the panel.",
        "op_code": (
            "result = result.faces('>Z').workplane()"
            ".pushPoints([(0,0)]).hole(20.0)"
        ),
    },
    {
        "record_id": "topup_slotted_plate_add_corner_hole",
        "family": "slotted_plate",
        "orig": "slotted_plate_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Add a 20 mm through-hole at position (-30, -30) on the top face.",
        "op_code": (
            "result = result.faces('>Z').workplane()"
            ".pushPoints([(-30,-30)]).hole(20.0)"
        ),
    },
    {
        "record_id": "topup_u_channel_add_hole",
        "family": "u_channel",
        "orig": "u_channel_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Add a 25 mm diameter through-hole in the bottom of the U-channel, centered.",
        "op_code": (
            "result = result.faces('<Z').workplane()"
            ".pushPoints([(0,0)]).hole(25.0)"
        ),
    },
    {
        "record_id": "topup_z_bracket_add_hole",
        "family": "z_bracket",
        "orig": "z_bracket_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Add a 18 mm diameter through-hole at the center of the top face.",
        "op_code": (
            "result = result.faces('>Z').workplane()"
            ".pushPoints([(0,0)]).hole(18.0)"
        ),
    },
    {
        "record_id": "topup_hollow_tube_add_radial_hole",
        "family": "hollow_tube",
        "orig": "hollow_tube_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 20 mm diameter cross-hole through the tube along the Z axis.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').transformed(rotate=cq.Vector(90,0,0))"
            ".cylinder(200.0, 10.0))"
        ),
    },
    # ── Phase 1b — more creative ops ──────────────────────────────────────────
    {
        "record_id": "topup_standoff_add_top_chamfer",
        "family": "standoff",
        "orig": "standoff_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top circular edges (outer and bore) of the standoff by 0.8 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(0.8)",
    },
    {
        "record_id": "topup_bolt_add_hex_socket",
        "family": "bolt",
        "orig": "bolt_easy_r0_orig.py",
        "edit_type": "add_feature",
        "difficulty": "medium",
        "instruction": "Cut a 12 mm across-flats hex socket into the top of the bolt head, 5 mm deep.",
        "op_code": (
            "result = result.faces('>Z').workplane()"
            ".polygon(6, 12.0).cutBlind(-5.0)"
        ),
    },
    {
        "record_id": "topup_shaft_collar_add_setscrew",
        "family": "shaft_collar",
        "orig": "shaft_collar_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 10 mm diameter radial setscrew hole through the collar wall.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('YZ').cylinder(60.0, 5.0))"
        ),
    },
    {
        "record_id": "topup_rib_plate_add_slot",
        "family": "rib_plate",
        "orig": "rib_plate_easy_r0_orig.py",
        "edit_type": "add_slot",
        "difficulty": "medium",
        "instruction": "Cut a 30 mm × 8 mm slot through the bottom face of the plate, centered.",
        "op_code": (
            "result = result.faces('<Z').workplane()"
            ".slot2D(30.0, 8.0).cutThruAll()"
        ),
    },
    {
        "record_id": "topup_stepped_shaft_add_axial_bore",
        "family": "stepped_shaft",
        "orig": "stepped_shaft_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 12 mm diameter axial through-hole along the shaft Z axis.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').cylinder(200.0, 6.0))"
        ),
    },
    {
        "record_id": "topup_dovetail_slide_add_top_slot",
        "family": "dovetail_slide",
        "orig": "dovetail_slide_easy_r0_orig.py",
        "edit_type": "add_slot",
        "difficulty": "medium",
        "instruction": "Cut a 120 mm × 16 mm slot 5 mm deep into the top face of the slide block.",
        "op_code": (
            "result = result.faces('>Y').workplane("
            "centerOption='CenterOfBoundBox')"
            ".slot2D(120.0, 16.0).cutBlind(-5.0)"
        ),
    },
    {
        "record_id": "topup_pcb_standoff_plate_add_center_hole",
        "family": "pcb_standoff_plate",
        "orig": "pcb_standoff_plate_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Drill a 20 mm diameter through-hole at the center of the plate.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').cylinder(50.0, 10.0))"
        ),
    },
    {
        "record_id": "topup_hollow_tube_add_side_slot",
        "family": "hollow_tube",
        "orig": "hollow_tube_easy_r0_orig.py",
        "edit_type": "add_slot",
        "difficulty": "hard",
        "instruction": "Cut a 60 mm × 14 mm slot 8 mm deep into the +Y side face of the tube.",
        "op_code": (
            "result = result.faces('>Y').workplane("
            "centerOption='CenterOfBoundBox')"
            ".slot2D(60.0, 14.0).cutBlind(-8.0)"
        ),
    },
    {
        "record_id": "topup_pulley_add_radial_hole",
        "family": "pulley",
        "orig": "pulley_gid10233_medium_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "hard",
        "instruction": "Drill a 12 mm diameter radial hole through the pulley perpendicular to its axis.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('YZ').cylinder(400.0, 6.0))"
        ),
    },
]

# ── Exec CadQuery code in subprocess → STEP ───────────────────────────────────

_PREAMBLE = """
import cadquery as cq
try:
    import OCP.TopoDS as _td
    for _cls in (_td.TopoDS_Shape, _td.TopoDS_Face, _td.TopoDS_Edge, _td.TopoDS_Vertex,
                 _td.TopoDS_Wire, _td.TopoDS_Shell, _td.TopoDS_Solid,
                 _td.TopoDS_Compound, _td.TopoDS_CompSolid):
        if not hasattr(_cls, 'HashCode'):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
except Exception:
    pass
show_object = lambda *a, **kw: None
"""
_SUFFIX = """
import sys as _sys
try:
    cq.exporters.export(result, _sys.argv[1])
except Exception as _e:
    raise RuntimeError(f"export failed: {_e}")
"""


def exec_cq(code: str, out_path: Path, timeout: int = 60) -> tuple[bool, str | None]:
    lines = [
        ln for ln in code.splitlines()
        if ln.strip() not in ("import cadquery as cq", "import cadquery")
    ]
    script = _PREAMBLE + "\n".join(lines) + _SUFFIX
    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    out_abs = out_path.resolve()
    try:
        r = subprocess.run(
            [sys.executable, "-c", script, str(out_abs)],
            env=env, timeout=timeout,
            capture_output=True, cwd=tempfile.gettempdir(),
        )
        if r.returncode != 0:
            return False, r.stderr.decode(errors="replace")[-400:]
        if not out_path.exists() or out_path.stat().st_size < 100:
            return False, "step missing or empty"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def splice_gt_code(orig_text: str, op_code: str) -> str:
    """Insert `op_code` before `show_object(result)`; append at end if absent."""
    if "show_object(result)" in orig_text:
        head, tail = orig_text.split("show_object(result)", 1)
        return f"{head}{op_code}\n\nshow_object(result){tail}"
    return orig_text.rstrip() + f"\n\n{op_code}\n"


def process_spec(spec: dict) -> dict:
    orig_path = BENCH / "codes" / spec["orig"]
    if not orig_path.exists():
        return {**spec, "status": "fail_orig_missing"}
    orig_text = orig_path.read_text()

    # orig step — prefer existing verified orig step under bench_edit/steps/
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    # Output locations
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

    # orig step: copy if verified exists, else exec
    if orig_step_src.exists():
        orig_out_step.write_bytes(orig_step_src.read_bytes())
    else:
        ok, err = exec_cq(orig_text, orig_out_step)
        if not ok:
            return {**spec, "status": "fail_orig_exec", "err": err}

    # gt
    try:
        gt_text = splice_gt_code(orig_text, spec["op_code"])
    except Exception as e:
        return {**spec, "status": "fail_splice", "err": str(e)}
    gt_out_code.write_text(gt_text)

    ok, err = exec_cq(gt_text, gt_out_step)
    if not ok:
        return {**spec, "status": "fail_gt_exec", "err": err}

    # IoU
    try:
        from bench.metrics import compute_iou
        iou, iou_err = compute_iou(str(orig_out_step), str(gt_out_step))
    except Exception as e:
        iou, iou_err = None, str(e)[:200]

    return {
        **spec,
        "status": "ok",
        "orig_code_path": str(orig_out_code.relative_to(OUT)),
        "gt_code_path": str(gt_out_code.relative_to(OUT)),
        "orig_step_path": str(orig_out_step.relative_to(OUT)),
        "gt_step_path": str(gt_out_step.relative_to(OUT)),
        "iou": iou,
        "iou_err": iou_err,
    }


def build_preview_mosaic(records: list[dict], out_png: Path):
    """Compose N rows × (big #num | orig 4-view | gt 4-view) with labels."""
    from PIL import Image, ImageDraw, ImageFont
    from scripts.data_generation.render_normalized_views import (
        render_step_normalized,
    )

    row_imgs = []
    try:
        num_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        num_font = ImageFont.load_default()
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    NUM_W = 120  # width of the number column

    ok_records = [r for r in records if r.get("status") == "ok"]
    for idx, rec in enumerate(ok_records, 1):
        with tempfile.TemporaryDirectory() as td:
            try:
                o = render_step_normalized(
                    str(OUT / rec["orig_step_path"]), td, size=320, prefix="o_"
                )
                g = render_step_normalized(
                    str(OUT / rec["gt_step_path"]), td, size=320, prefix="g_"
                )
                oi = Image.open(o["composite"]).copy()
                gi = Image.open(g["composite"]).copy()
            except Exception as e:
                print(f"  preview fail {rec['record_id']}: {e}")
                continue
        w = NUM_W + oi.width + gi.width + 20
        h = max(oi.height, gi.height) + 70
        row = Image.new("RGB", (w, h), "white")
        row.paste(oi, (NUM_W, 60))
        row.paste(gi, (NUM_W + oi.width + 20, 60))
        d = ImageDraw.Draw(row)
        # Giant #N on the left
        d.text((15, 30), f"#{idx}", fill="black", font=num_font)
        # Title (record_id | iou | type) in top banner
        title = f"{rec['record_id']}  |  IoU={rec.get('iou', 0):.3f}  |  {rec['edit_type']}"
        d.text((NUM_W + 10, 10), title, fill="black", font=font)
        d.text((NUM_W + 10, 36), rec["instruction"][:140], fill="gray", font=small)
        # Panel labels
        d.text((NUM_W + oi.width // 2 - 20, h - 18), "ORIG",
               fill="black", font=font)
        d.text((NUM_W + oi.width + 20 + gi.width // 2 - 10, h - 18), "GT",
               fill="black", font=font)
        # Divider line between num column and panels
        d.line([(NUM_W - 5, 0), (NUM_W - 5, h)], fill="lightgray", width=1)
        row_imgs.append(row)

    if not row_imgs:
        print("no previews built")
        return

    W = max(r.width for r in row_imgs)
    H = sum(r.height for r in row_imgs) + 10 * len(row_imgs)
    canvas = Image.new("RGB", (W, H), "white")
    y = 0
    for r in row_imgs:
        canvas.paste(r, (0, y))
        y += r.height + 10
    canvas.save(str(out_png))
    print(f"mosaic → {out_png}  ({len(row_imgs)} rows, {W}×{H})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="record_id filter")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    specs = SPECS
    if args.only:
        specs = [s for s in SPECS if s["record_id"] == args.only]
        if not specs:
            raise SystemExit(f"no spec matches {args.only}")

    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for i, spec in enumerate(specs):
        print(f"[{i+1}/{len(specs)}] {spec['record_id']} ... ", end="", flush=True)
        rec = process_spec(spec)
        status = rec["status"]
        iou = rec.get("iou")
        iou_s = f"IoU={iou:.3f}" if isinstance(iou, float) else "IoU=?"
        print(f"{status} {iou_s}")
        if status != "ok":
            print(f"    err: {rec.get('err','')[:200]}")
        records.append(rec)

    # Write records.jsonl
    jl = OUT / "records.jsonl"
    with jl.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    # Write CSV (num, id, family, edit_type, difficulty, iou, status, instruction)
    # Only OK records get a # that aligns with the mosaic numbering.
    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["num", "record_id", "family", "edit_type", "difficulty",
             "iou", "status", "instruction"]
        )
        ok_idx = 0
        for r in records:
            if r["status"] == "ok":
                ok_idx += 1
                num = str(ok_idx)
            else:
                num = ""
            w.writerow([
                num,
                r["record_id"], r["family"], r["edit_type"], r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float) else "",
                r["status"], r["instruction"],
            ])
    print(f"\nwrote {csv_path}, {jl}")

    ok = sum(1 for r in records if r["status"] == "ok")
    print(f"ok: {ok}/{len(records)}")

    if not args.no_preview and ok:
        build_preview_mosaic(records, OUT / "preview.png")


if __name__ == "__main__":
    main()
