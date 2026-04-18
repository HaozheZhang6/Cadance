#!/usr/bin/env python
"""Fix missing columns in verified_pairs.jsonl and render missing views.

Fixes applied:
1. claude_manual_fix: fill cq_code_path + gen_step_path
2. Fusion360 pairs: fill ops_json_path from base_stem
3. Synthetic pairs: fill raw_step_path = gen_step_path (GT IS the gen STEP)
                    fill ops_json_path = params JSON (generated from params)
4. All pairs: fill source/timestamp/verified where missing
5. Render views_raw_dir + views_gen_dir for all records missing them

Usage:
    LD_LIBRARY_PATH=/workspace/.local/lib PYTHONUNBUFFERED=1 \\
    uv run python scripts/data_generation/fix_verified_pairs.py

    # Only fix metadata (no rendering)
    uv run python scripts/data_generation/fix_verified_pairs.py --no-render

    # Only render views (skip metadata fixes)
    LD_LIBRARY_PATH=/workspace/.local/lib uv run python \\
        scripts/data_generation/fix_verified_pairs.py --render-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_LD = "/workspace/.local/lib"
_cur = os.environ.get("LD_LIBRARY_PATH", "")
if _LD not in _cur:
    os.environ["LD_LIBRARY_PATH"] = f"{_LD}:{_cur}".strip(":")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

VERIFIED_PAIRS = REPO_ROOT / "data/data_generation/verified/verified_pairs.jsonl"
CQ_DIR_MAIN = REPO_ROOT / "data/data_generation/codex_validation/run_v2_n1000/cadquery"
GEN_DIR_MAIN = REPO_ROOT / "data/data_generation/codex_validation/run_v2_n1000/generated_step"
FUSION360_JSON_DIR = REPO_ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"
VIEWS_BASE = REPO_ROOT / "data/views"
PARAMS_JSON_DIR = REPO_ROOT / "data/data_generation/codex_validation/params_json"

SYNTH_SOURCES = {"run_synthetic_diverse", "run_synth_reconstruct_openai",
                 "run_synth_reconstruct_glm", "run_synth_reconstruct_codex"}


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def _fix_metadata(records: list[dict]) -> tuple[list[dict], int]:
    """Fix missing metadata fields. Returns (fixed_records, n_changed)."""
    import datetime
    changed = 0

    for r in records:
        orig = dict(r)
        stem = r.get("stem", "")
        source = r.get("source", "")

        # Fix source for old records
        if not source:
            r["source"] = "claude_manual_fix"
            source = "claude_manual_fix"

        # Fix timestamp
        if not r.get("timestamp"):
            r["timestamp"] = "2026-02-01T00:00:00Z"

        # Fix verified based on iou
        if r.get("verified") is None:
            iou = r.get("iou")
            r["verified"] = bool(iou is not None and iou >= 0.99)

        # Fix any Fusion360 run: fill cq_code_path + gen_step_path from run_v2_n1000
        if not r.get("cq_code_path"):
            p = CQ_DIR_MAIN / f"{stem}.py"
            if p.exists():
                r["cq_code_path"] = _rel(p)
        if not r.get("gen_step_path"):
            p = GEN_DIR_MAIN / f"{stem}.step"
            if p.exists():
                r["gen_step_path"] = _rel(p)

        # Fix ops_json_path for Fusion360 pairs
        is_synth = any(source.startswith(s) for s in SYNTH_SOURCES) or "synth" in stem
        if not r.get("ops_json_path") and not is_synth:
            # Derive base_stem from stem (strip trailing _NNe suffix or _claude_fixed)
            base = stem.replace("_claude_fixed", "").replace("_auto", "")
            # base_stem is the part before the last index (e.g. 112099_2c7f567f_0000)
            j = FUSION360_JSON_DIR / f"{base}.json"
            if j.exists():
                r["ops_json_path"] = _rel(j)

        # Fix raw_step_path for synthetic pairs
        if is_synth and not r.get("raw_step_path"):
            # For synth_diverse: raw IS the gen_step
            # For synth_reconstruct: raw is the base pair's gen_step
            if source == "run_synthetic_diverse":
                if r.get("gen_step_path"):
                    r["raw_step_path"] = r["gen_step_path"]
            elif source.startswith("run_synth_reconstruct"):
                # base_stem = stem without _rec_<provider> suffix
                base_stem = stem.rsplit("_rec_", 1)[0] if "_rec_" in stem else stem
                # Find the original synth STEP
                synth_step = (REPO_ROOT / "data/data_generation/codex_validation/run_synthetic_diverse"
                              / "generated_step" / f"{base_stem}.step")
                if synth_step.exists():
                    r["raw_step_path"] = _rel(synth_step)

        # Fix ops_json_path for synthetic pairs: generate from params
        if is_synth and not r.get("ops_json_path"):
            params = r.get("params")
            if params:
                PARAMS_JSON_DIR.mkdir(parents=True, exist_ok=True)
                jp = PARAMS_JSON_DIR / f"{stem}.json"
                if not jp.exists():
                    jp.write_text(json.dumps(params, indent=2), encoding="utf-8")
                r["ops_json_path"] = _rel(jp)

        if r != orig:
            changed += 1

    return records, changed


def _render_views(records: list[dict], limit: int = 0) -> int:
    """Render 4-view PNGs for records missing views_raw_dir or views_gen_dir."""
    import signal

    try:
        from scripts.data_generation.render_step_views import render_step_views
    except Exception as exc:
        print(f"  [warn] cannot import render_step_views: {exc}")
        return 0

    def _timeout_handler(signum, frame):
        raise TimeoutError("render timeout")

    def _render_with_timeout(step_path, out_base, prefix, timeout_sec=60):
        old = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout_sec)
        try:
            render_step_views(step_path, out_base, prefix=prefix)
            return True
        except Exception:
            return False
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

    rendered = 0
    to_render = []
    for r in records:
        need_raw = not r.get("views_raw_dir") or not (REPO_ROOT / r["views_raw_dir"]).exists()
        need_gen = not r.get("views_gen_dir") or not (REPO_ROOT / r["views_gen_dir"]).exists()
        if need_raw or need_gen:
            to_render.append((r, need_raw, need_gen))

    if limit > 0:
        to_render = to_render[:limit]

    print(f"  Rendering views for {len(to_render)} records...")
    for i, (r, need_raw, need_gen) in enumerate(to_render, 1):
        stem = r["stem"]
        out_base = VIEWS_BASE / stem
        out_base.mkdir(parents=True, exist_ok=True)

        raw_done = False
        gen_done = False

        if need_raw and r.get("raw_step_path"):
            raw_step = REPO_ROOT / r["raw_step_path"]
            if raw_step.exists():
                if _render_with_timeout(raw_step, out_base, prefix="raw_"):
                    r["views_raw_dir"] = _rel(out_base)
                    raw_done = True

        if need_gen and r.get("gen_step_path"):
            gen_step = REPO_ROOT / r["gen_step_path"]
            if gen_step.exists():
                if _render_with_timeout(gen_step, out_base, prefix="gen_"):
                    r["views_gen_dir"] = _rel(out_base)
                    gen_done = True

        if raw_done or gen_done:
            rendered += 1
        if i % 50 == 0 or i == len(to_render):
            print(f"  [{i}/{len(to_render)}] rendered={rendered}")

    return rendered


def _save(records: list[dict]) -> None:
    VERIFIED_PAIRS.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-render", action="store_true", help="Skip view rendering")
    parser.add_argument("--render-only", action="store_true", help="Only render views")
    parser.add_argument("--render-limit", type=int, default=0,
                        help="Max records to render (0=all)")
    args = parser.parse_args()

    records = []
    for line in VERIFIED_PAIRS.open(encoding="utf-8"):
        line = line.strip()
        if line:
            records.append(json.loads(line))
    print(f"Loaded {len(records)} records")

    if not args.render_only:
        print("Fixing metadata...")
        records, n_changed = _fix_metadata(records)
        print(f"  Changed {n_changed} records")
        _save(records)
        print("  Saved.")

    if not args.no_render:
        print("Rendering views...")
        n_rendered = _render_views(records, limit=args.render_limit)
        print(f"  Rendered {n_rendered} new view sets")
        _save(records)
        print("  Saved with view paths.")

    # Final stats
    total = len(records)
    fields = ["raw_step_path", "ops_json_path", "gen_step_path", "cq_code_path",
              "verified", "source", "timestamp", "views_raw_dir", "views_gen_dir"]
    print("\nFinal missing field counts:")
    for f in fields:
        miss = sum(1 for r in records if not r.get(f) and r.get(f) != 0)
        if miss:
            print(f"  {f}: {miss} missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
