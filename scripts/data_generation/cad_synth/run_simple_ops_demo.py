"""Generate ~50 simple_ops samples + render mosaic."""

import json
import sys
import traceback
from pathlib import Path

import cadquery as cq
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))

from render_normalized_views import render_step_normalized
from scripts.data_generation.cad_synth.families.simple_ops import (
    SimpleArcFamily,
    SimpleBoxChamferFamily,
    SimpleBoxCutFamily,
    SimpleBoxHoleFamily,
    SimpleComposeFamily,
    SimpleCutFamily,
    SimpleCylChamferFamily,
    SimpleCylHoleFamily,
    SimpleExtrudeChamferFamily,
    SimpleExtrudeCutFamily,
    SimpleExtrudeHoleFamily,
    SimpleFilletFamily,
    SimpleHoleFamily,
    SimpleLoftCutFamily,
    SimpleLoftFamily,
    SimplePolarArrayFamily,
    SimplePolygonFamily,
    SimplePolygonHoleFamily,
    SimplePolylineFamily,
    SimpleRevolveCutFamily,
    SimpleRevolveFamily,
    SimpleShellFamily,
    SimpleSphereFamily,
    SimpleSweepHelixFamily,
    SimpleSweepSplineFamily,
    SimpleTaperExtrudeFamily,
    SimpleTwistExtrudeFamily,
    SimpleTwistSweepFamily,
    SimpleUnionFamily,
)

OUT = ROOT / "data" / "data_generation" / "simple_ops_preview"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "step").mkdir(exist_ok=True)
(OUT / "png").mkdir(exist_ok=True)

# 29 families × 16 = 464. Mirror dropped (ops + family). 11 explicit base × mod
# combo families added (simple_box_hole, simple_extrude_cut, etc.) for
# composition coverage with clean Op programs.
PLAN = [
    # focal-op families
    (SimpleRevolveFamily(), 16),
    (SimpleLoftFamily(), 16),
    (SimpleSweepHelixFamily(), 16),
    (SimpleSweepSplineFamily(), 16),
    (SimpleTwistExtrudeFamily(), 16),
    (SimpleTwistSweepFamily(), 16),
    (SimpleTaperExtrudeFamily(), 16),
    (SimplePolarArrayFamily(), 16),
    (SimpleUnionFamily(), 16),
    (SimpleCutFamily(), 16),
    (SimpleFilletFamily(), 16),
    (SimpleComposeFamily(), 16),
    (SimplePolylineFamily(), 16),
    (SimpleArcFamily(), 16),
    (SimplePolygonFamily(), 16),
    (SimpleSphereFamily(), 16),
    (SimpleShellFamily(), 16),
    (SimpleHoleFamily(), 16),
    # explicit base × modifier combo families
    (SimpleBoxHoleFamily(), 16),
    (SimpleBoxCutFamily(), 16),
    (SimpleBoxChamferFamily(), 16),
    (SimpleCylHoleFamily(), 16),
    (SimpleCylChamferFamily(), 16),
    (SimpleExtrudeCutFamily(), 16),
    (SimpleExtrudeHoleFamily(), 16),
    (SimpleExtrudeChamferFamily(), 16),
    (SimplePolygonHoleFamily(), 16),
    (SimpleRevolveCutFamily(), 16),
    (SimpleLoftCutFamily(), 16),
]
TOTAL = sum(n for _, n in PLAN)  # 464


def _worker_init(root_str: str):
    """Pool initializer — set up sys.path and cache family instances + render fn."""
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, root_str)
    _sys.path.insert(0, str(_Path(root_str) / "scripts" / "data_generation"))

    import cadquery as _cq
    from render_normalized_views import render_step_normalized as _render
    from scripts.data_generation.cad_synth.families.simple_ops import (
        SimpleArcFamily,
        SimpleBoxChamferFamily,
        SimpleBoxCutFamily,
        SimpleBoxHoleFamily,
        SimpleComposeFamily,
        SimpleCutFamily,
        SimpleCylChamferFamily,
        SimpleCylHoleFamily,
        SimpleExtrudeChamferFamily,
        SimpleExtrudeCutFamily,
        SimpleExtrudeHoleFamily,
        SimpleFilletFamily,
        SimpleHoleFamily,
        SimpleLoftCutFamily,
        SimpleLoftFamily,
        SimplePolarArrayFamily,
        SimplePolygonFamily,
        SimplePolygonHoleFamily,
        SimplePolylineFamily,
        SimpleRevolveCutFamily,
        SimpleRevolveFamily,
        SimpleShellFamily,
        SimpleSphereFamily,
        SimpleSweepHelixFamily,
        SimpleSweepSplineFamily,
        SimpleTaperExtrudeFamily,
        SimpleTwistExtrudeFamily,
        SimpleTwistSweepFamily,
        SimpleUnionFamily,
    )

    classes = [
        SimpleRevolveFamily, SimpleLoftFamily, SimpleSweepHelixFamily,
        SimpleSweepSplineFamily, SimpleTwistExtrudeFamily, SimpleTwistSweepFamily,
        SimpleTaperExtrudeFamily, SimplePolarArrayFamily, SimpleUnionFamily,
        SimpleCutFamily, SimpleFilletFamily, SimpleComposeFamily,
        SimplePolylineFamily, SimpleArcFamily, SimplePolygonFamily,
        SimpleSphereFamily, SimpleShellFamily, SimpleHoleFamily,
        SimpleBoxHoleFamily, SimpleBoxCutFamily, SimpleBoxChamferFamily,
        SimpleCylHoleFamily, SimpleCylChamferFamily, SimpleExtrudeCutFamily,
        SimpleExtrudeHoleFamily, SimpleExtrudeChamferFamily, SimplePolygonHoleFamily,
        SimpleRevolveCutFamily, SimpleLoftCutFamily,
    ]
    global _FAM, _CQ, _RENDER
    _FAM = {cls().name: cls() for cls in classes}
    _CQ = _cq
    _RENDER = _render


SAMPLE_TIMEOUT_S = 45  # hard timeout per sample — OCCT can deadlock on bad inputs


class _SampleTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise _SampleTimeout()


def _worker_process(args):
    fam_name, params, stem, diff, step_dir, png_dir = args
    import signal as _signal

    # SIGALRM unwinds OCCT/VTK if a sample stalls > SAMPLE_TIMEOUT_S. macOS only
    # delivers SIGALRM on the main thread, which is fine for serial in-process.
    _signal.signal(_signal.SIGALRM, _alarm_handler)
    _signal.alarm(SAMPLE_TIMEOUT_S)
    try:
        fam = _FAM[fam_name]
        wp = fam.build(params)
        bb = wp.val().BoundingBox()
        if bb.xlen < 0.1 or bb.ylen < 0.1 or bb.zlen < 0.1:
            return {"family": fam_name, "stem": stem, "error": f"degen {bb.xlen:.1f}x{bb.ylen:.1f}x{bb.zlen:.1f}"}
        step_path = f"{step_dir}/{stem}.step"
        _CQ.exporters.export(wp, step_path, exportType=_CQ.exporters.ExportTypes.STEP)
        paths = _RENDER(step_path, png_dir, prefix=f"{stem}_")
        return {
            "family": fam_name,
            "stem": stem,
            "diff": diff,
            "params": params,
            "composite": paths["composite"],
        }
    except _SampleTimeout:
        return {"family": fam_name, "stem": stem, "error": f"TIMEOUT after {SAMPLE_TIMEOUT_S}s"}
    except Exception as e:
        return {"family": fam_name, "stem": stem, "error": f"{type(e).__name__}: {str(e)[:160]}"}
    finally:
        _signal.alarm(0)


def _build_args(plan, root_seed=42):
    """Sequentially generate (fam_name, params, stem, diff, step_dir, png_dir) tuples.

    Sequential param sampling keeps rng draws reproducible. Per family, sample
    until we have n valid params (or exhaust 8n attempts).
    """
    args_list = []
    seed = root_seed
    step_dir = str(OUT / "step")
    skip_log = []
    for fam, n in plan:
        rng = np.random.default_rng(seed)
        seed += 1
        png_dir = str(OUT / "png" / fam.name)
        Path(png_dir).mkdir(parents=True, exist_ok=True)
        got = 0
        attempts = 0
        max_attempts = n * 8
        while got < n and attempts < max_attempts:
            attempts += 1
            diff = ["easy", "medium", "hard"][attempts % 3]
            try:
                params = fam.sample_params(diff, rng)
                if not fam.validate_params(params):
                    continue
            except Exception as e:
                skip_log.append({"family": fam.name, "attempt": attempts, "error": f"sample: {e}"})
                continue
            stem = f"{fam.name}_{got:02d}"
            args_list.append((fam.name, params, stem, diff, step_dir, png_dir))
            got += 1
        if got < n:
            skip_log.append({"family": fam.name, "got": got, "needed": n})
    return args_list, skip_log


def main():
    print(f"Building args ...")
    args_list, skip_log = _build_args(PLAN)
    total_args = len(args_list)

    # Skip args whose composite PNG already exists. Lets us resume after a crash
    # or kill without redoing 200+ already-rendered samples.
    pending = []
    pre_done = []
    for a in args_list:
        fam_name, params, stem, diff, step_dir, png_dir = a
        comp = Path(png_dir) / f"{stem}_composite.png"
        if comp.exists():
            pre_done.append({
                "family": fam_name, "stem": stem, "diff": diff,
                "params": params, "composite": str(comp),
            })
        else:
            pending.append(a)
    print(f"Total {total_args} samples — {len(pre_done)} already done, {len(pending)} pending")

    results = list(pre_done)
    fail_log = list(skip_log)

    if pending:
        # Serial in-process — VTK GPU context contention makes parallel slower
        # than serial on macOS. Initialize the worker globals here in main proc.
        _worker_init(str(ROOT))
        for i, a in enumerate(pending):
            r = _worker_process(a)
            done = i + 1
            if "composite" in r:
                results.append(r)
                if done % 10 == 0 or done == len(pending):
                    print(f"  [{done}/{len(pending)}] OK {r['family']}/{r['stem']}")
            else:
                fail_log.append(r)
                print(f"  [{done}/{len(pending)}] FAIL {r.get('family')}/{r.get('stem')}: {r.get('error')}")

    # Sort results by PLAN order × stem index
    fam_order = {fam.name: i for i, (fam, _) in enumerate(PLAN)}
    results.sort(key=lambda r: (fam_order.get(r["family"], 999), r["stem"]))

    # Mosaic: rows by family, cols are samples
    per_row = max(n for _, n in PLAN)
    n_rows = len(PLAN)
    cell = 268
    header = 36
    margin = 8
    mosaic_w = per_row * cell + margin * 2
    mosaic_h = n_rows * (cell + header) + margin * 2
    mosaic = Image.new("RGB", (mosaic_w, mosaic_h), (245, 245, 245))
    draw = ImageDraw.Draw(mosaic)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    by_fam = {}
    for r in results:
        by_fam.setdefault(r["family"], []).append(r)

    for r, (fam, n) in enumerate(PLAN):
        y0 = margin + r * (cell + header)
        items = by_fam.get(fam.name, [])
        draw.rectangle([margin, y0, mosaic_w - margin, y0 + header], fill=(40, 40, 70))
        draw.text((margin + 12, y0 + 6), f"{fam.name}  ({len(items)}/{n})", fill="white", font=font)
        for c, item in enumerate(items):
            if c >= per_row:
                break
            try:
                img = Image.open(item["composite"]).convert("RGB").resize((cell, cell))
                mosaic.paste(img, (margin + c * cell, y0 + header))
            except Exception as e:
                draw.text((margin + c * cell + 8, y0 + header + 8), f"err: {e}", fill="red")

    mosaic_path = OUT / "mosaic_simple_ops.png"
    mosaic.save(str(mosaic_path))
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    (OUT / "fails.json").write_text(json.dumps(fail_log, indent=2))
    print(f"\nMosaic: {mosaic_path}")
    print(f"Total: {len(results)}/{TOTAL}, fails: {len(fail_log)}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
