"""Phase 2 of UA-24 180k: render 4-view PNGs from existing gen.step files.

Phase 1 (run_180k_batch.sh with RENDER=0) produces code.py + gen.step + meta.json
without PNGs. This script walks every data_arg_180k_<family> verified dir, finds
gen.step missing render_*.png, and renders.

Resume-safe: skips stems whose 4 render_*.png already exist.
Workers: process pool (uses ProcessPoolExecutor).

Usage:
  uv run python3 scripts/data_generation/cad_synth/render_180k_phase2.py
  WORKERS=4 uv run python3 scripts/data_generation/cad_synth/render_180k_phase2.py
  FAMILIES="hex_nut pulley" uv run python3 scripts/data_generation/cad_synth/render_180k_phase2.py
"""

import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "data_generation"
GEN_DIR = DATA / "generated_data" / "fusion360"
LOG_DIR = DATA / "synth_reports"

sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))


def _needs_render(verified_dir: Path) -> bool:
    """True if this verified dir lacks complete render_0..3.png."""
    for i in range(4):
        if not (verified_dir / f"render_{i}.png").exists():
            return True
    return False


def _scan(families: list[str] | None) -> list[Path]:
    """Find all data_arg_180k_<family>/gen.step paths needing render."""
    todo = []
    if families:
        patterns = [f"verified_data_arg_180k_{f}" for f in families]
    else:
        patterns = ["verified_data_arg_180k_*"]
    for stem_dir in GEN_DIR.iterdir():
        if not stem_dir.is_dir():
            continue
        for pat in patterns:
            for vdir in stem_dir.glob(pat):
                step = vdir / "gen.step"
                if step.exists() and _needs_render(vdir):
                    todo.append(vdir)
    return todo


def _render_one(verified_dir: Path) -> tuple[str, bool, str]:
    """Render 4 views for one verified dir. Returns (stem, ok, reason)."""
    stem = verified_dir.parent.name
    step_path = verified_dir / "gen.step"
    try:
        from render_normalized_views import render_step_normalized

        view_dir = verified_dir / "views"
        render_step_normalized(str(step_path), str(view_dir))
        for i in range(4):
            src = view_dir / f"view_{i}.png"
            dst = verified_dir / f"render_{i}.png"
            if src.exists():
                shutil.copy2(src, dst)
        if not all((verified_dir / f"render_{i}.png").exists() for i in range(4)):
            return stem, False, "incomplete views"
        return stem, True, ""
    except Exception as e:  # noqa: BLE001
        return stem, False, str(e)[:200]


def main() -> None:
    workers = int(os.environ.get("WORKERS", "4"))
    families_env = os.environ.get("FAMILIES", "").strip()
    families = families_env.split() if families_env else None

    print(f"Scanning {GEN_DIR} ...")
    todo = _scan(families)
    print(f"Found {len(todo)} verified dirs missing renders. workers={workers}")
    if not todo:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    progress = LOG_DIR / "180k_render_progress.log"

    t0 = time.time()
    n_ok = n_fail = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_render_one, vdir) for vdir in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            stem, ok, reason = fut.result()
            if ok:
                n_ok += 1
            else:
                n_fail += 1
                with open(progress, "a") as f:
                    f.write(f"FAIL {stem}: {reason}\n")
            if i % 100 == 0 or i == len(todo):
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(todo) - i) / rate if rate > 0 else 0
                msg = (
                    f"[{i}/{len(todo)}] ok={n_ok} fail={n_fail} "
                    f"rate={rate:.1f}/s eta={eta / 60:.1f}min"
                )
                print(msg)
                with open(progress, "a") as f:
                    f.write(msg + "\n")

    print(f"DONE: {n_ok} rendered, {n_fail} failed ({(time.time() - t0) / 60:.1f}min)")


if __name__ == "__main__":
    main()
