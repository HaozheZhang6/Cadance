"""UA-20 — Render side-by-side orig|gt preview per curated pair.

Reads curate_final_plan.json (combined new+existing plan), renders each
pair with cadrille 4-view composite, stacks orig|gt horizontally, captions
with param/value change, dl, IoU. Writes previews/<family>.png.

Usage:
    python -m bench.edit_gen.curate_preview
    python -m bench.edit_gen.curate_preview --family knob
"""

from __future__ import annotations

import argparse
import json
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "data_generation" / "bench_edit"
PLAN_DIM = BASE / "curate_final_plan.json"
PLAN_ADD = BASE / "curate_additive_plan.json"
PLAN_MULTI = BASE / "curate_multi_plan.json"
PREVIEW_DIR = BASE / "previews"


def build_title(fam: str, entry: dict) -> tuple[str, str]:
    src = entry.get("source", "?")
    iou = float(entry["iou"])
    dl = int(entry["dl_est"])
    if "axes" in entry:
        axs = " & ".join(
            f"{a['axis']} {a['pct']:+d}%" for a in entry["axes"]
        )
        head = f"{fam} [multi] | {axs}"
        sub = f"IoU={iou:.3f} dl={dl} src={src}"
    elif entry.get("source") == "additive_strip":
        op = entry.get("op_type", "add")
        head = f"{fam} [{op}] | {entry.get('instruction','')[:90]}"
        sub = f"IoU={iou:.3f} dl={dl} src={src}"
    else:
        ov = float(entry["orig_value"])
        tv = float(entry["target_value"])
        pct = entry.get("pct_delta", 0)
        head = f"{fam} | {entry['axis']}: {ov:g} → {tv:g} ({pct:+d}%)"
        sub = f"IoU={iou:.3f} dl={dl} src={src}"
    return head, sub


def render_pair_preview(fam: str, entry: dict, out_path: Path, tag: str = ""):
    from PIL import Image, ImageDraw, ImageFont

    from scripts.data_generation.render_normalized_views import (
        render_step_normalized,
    )

    orig_step = BASE / entry["orig_step_path"]
    gt_step = BASE / entry["gt_step_path"]

    with tempfile.TemporaryDirectory() as td:
        o_paths = render_step_normalized(str(orig_step), td, size=256, prefix="orig_")
        g_paths = render_step_normalized(str(gt_step), td, size=256, prefix="gt_")
        o_img = Image.open(o_paths["composite"]).copy()
        g_img = Image.open(g_paths["composite"]).copy()

    w = o_img.width + g_img.width + 20
    h = max(o_img.height, g_img.height) + 70
    canvas = Image.new("RGB", (w, h), "white")
    canvas.paste(o_img, (0, 60))
    canvas.paste(g_img, (o_img.width + 20, 60))

    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except Exception:
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    head, sub = build_title(fam, entry)
    d.text((10, 10), head, fill="black", font=font)
    d.text((10, 35), sub, fill="gray", font=small)
    if entry.get("orig_line"):
        d.text(
            (10, 48),
            f"line: {entry['orig_line'][:120]}",
            fill="gray",
            font=small,
        )
    d.text((o_img.width // 2 - 20, h - 18), "ORIG", fill="black", font=font)
    d.text(
        (o_img.width + 20 + g_img.width // 2 - 10, h - 18),
        "GT",
        fill="black",
        font=font,
    )

    canvas.save(str(out_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default=None)
    ap.add_argument("--plan", default=None,
                    help="explicit plan file; default: render dim+additive+multi")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", action="store_true", help="skip families with existing preview png")
    args = ap.parse_args()

    items: list[tuple[str, dict, str]] = []
    if args.plan:
        plan = json.loads(Path(args.plan).read_text())
        for k, v in plan.items():
            items.append((k, v, ""))
    else:
        for path, tag in [(PLAN_DIM, ""), (PLAN_ADD, "add"), (PLAN_MULTI, "multi")]:
            if not path.exists():
                continue
            p = json.loads(path.read_text())
            for k, v in p.items():
                items.append((k, v, tag))

    if args.family:
        items = [(k, v, t) for (k, v, t) in items if k == args.family or v.get("family") == args.family]
    if args.limit:
        items = items[: args.limit]

    PREVIEW_DIR.mkdir(exist_ok=True)
    fails = []
    for i, (key, entry, tag) in enumerate(items):
        name = key if not tag else f"{key}"
        fam_label = entry.get("family", key)
        out = PREVIEW_DIR / f"{name}.png"
        if args.resume and out.exists():
            continue
        try:
            render_pair_preview(fam_label, entry, out, tag=tag)
            print(f"[{i+1:3d}/{len(items)}] OK   {name}", flush=True)
        except Exception as e:
            print(f"[{i+1:3d}/{len(items)}] FAIL {name}: {str(e)[:200]}")
            fails.append((name, str(e)[:200]))

    if fails:
        (BASE / "preview_fails.json").write_text(json.dumps(fails, indent=2))
        print(f"\n{len(fails)} preview failures logged to preview_fails.json")


if __name__ == "__main__":
    main()
