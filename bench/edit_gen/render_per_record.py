"""Render per-record preview PNG for manual inspection.

For each record in topup_diverse/records.jsonl (and optionally topup_phase3/),
render a single side-by-side orig|gt composite labeled with record_id + IoU.
Write to <out>/previews/<record_id>.png.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
LD = os.environ.get("LD_LIBRARY_PATH", "/workspace/.local/lib")


_RENDER_SCRIPT = """
import sys
from scripts.data_generation.render_normalized_views import render_step_normalized
r = render_step_normalized(sys.argv[1], sys.argv[2], size=360, prefix=sys.argv[3])
print(r['composite'])
"""


def render_step_subprocess(step_path: str, tmp_dir: str,
                           prefix: str, timeout: int = 90) -> str | None:
    """Run render_step_normalized in subprocess, return composite path or None."""
    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    try:
        r = subprocess.run(
            [sys.executable, "-c", _RENDER_SCRIPT, step_path, tmp_dir, prefix],
            env=env, timeout=timeout,
            capture_output=True,
        )
        if r.returncode != 0:
            err_tail = r.stderr.decode(errors="replace")[-200:]
            print(f"    subprocess rc={r.returncode}: {err_tail}", flush=True)
            return None
        out = r.stdout.decode(errors="replace").strip().splitlines()
        return out[-1] if out else None
    except subprocess.TimeoutExpired:
        return None


def render_one(rec: dict, out_dir: Path, base_dir: Path) -> bool:
    from PIL import Image, ImageDraw, ImageFont
    rid = rec["record_id"]
    png = out_dir / f"{rid}.png"
    if png.exists():
        return True
    orig = base_dir / rec["orig_step_path"]
    gt = base_dir / rec["gt_step_path"]
    try:
        td = tempfile.mkdtemp(prefix=f"render_{rid}_")
        o_path = render_step_subprocess(str(orig), td, "o_")
        if o_path is None:
            print(f"  fail {rid}: orig render timeout/error", flush=True)
            return False
        g_path = render_step_subprocess(str(gt), td, "g_")
        if g_path is None:
            print(f"  fail {rid}: gt render timeout/error", flush=True)
            return False
        oi = Image.open(o_path).copy()
        gi = Image.open(g_path).copy()
    except Exception as e:
        print(f"  fail {rid}: {e}", flush=True)
        return False
    finally:
        try:
            import shutil
            shutil.rmtree(td, ignore_errors=True)
        except Exception:
            pass
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
        body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except Exception:
        title_font = body_font = small = ImageFont.load_default()
    GAP = 40
    TOP_BAND = 140
    BOT_BAND = 40
    w = oi.width + gi.width + GAP
    h = max(oi.height, gi.height) + TOP_BAND + BOT_BAND
    canvas = Image.new("RGB", (w, h), "white")
    canvas.paste(oi, (0, TOP_BAND))
    canvas.paste(gi, (oi.width + GAP, TOP_BAND))
    d = ImageDraw.Draw(canvas)
    iou = rec.get("iou")
    iou_s = f"{iou:.3f}" if isinstance(iou, float) else "?"
    d.text((15, 10), f"{rid}", fill="black", font=title_font)
    d.text((15, 52), f"type={rec['edit_type']}  IoU={iou_s}  "
                     f"fam={rec['family']}  diff={rec.get('difficulty','?')}",
           fill="gray", font=small)
    # Wrap long instruction over multiple lines
    instr = rec.get("instruction", "")
    max_chars = 110
    if len(instr) > max_chars:
        # split at nearest space
        cut = instr.rfind(" ", 0, max_chars)
        if cut == -1: cut = max_chars
        d.text((15, 82), instr[:cut], fill="black", font=body_font)
        d.text((15, 112), instr[cut+1:cut+1+max_chars], fill="black",
               font=body_font)
    else:
        d.text((15, 82), instr, fill="black", font=body_font)
    d.text((oi.width // 2 - 30, h - 32), "ORIG", fill="black",
           font=title_font)
    d.text((oi.width + GAP + gi.width // 2 - 20, h - 32), "GT",
           fill="black", font=title_font)
    canvas.save(str(png))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(BENCH / "topup_diverse"),
                    help="dir with records.jsonl")
    ap.add_argument("--family", default=None, help="family filter")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    src = Path(args.src)
    recs = [json.loads(ln) for ln in (src / "records.jsonl").read_text().splitlines() if ln]
    if args.family:
        recs = [r for r in recs if r["family"] == args.family]
    if args.limit:
        recs = recs[: args.limit]
    out_dir = src / "previews"
    out_dir.mkdir(exist_ok=True)
    done = 0
    for i, r in enumerate(recs, 1):
        if render_one(r, out_dir, src):
            done += 1
        if i % 10 == 0:
            print(f"[{i}/{len(recs)}] rendered {done} ok", flush=True)
    print(f"\ntotal: {done}/{len(recs)} in {out_dir}")


if __name__ == "__main__":
    main()
