#!/usr/bin/env python
"""Reconstruct synthetic diverse parts from params using LLM codegen.

Reads synthetic diverse pairs (source=run_synthetic_diverse) from
verified_pairs.jsonl, generates CadQuery code from params JSON using
LLM providers (priority: codex → openai → glm), verifies generated
STEP against original synthetic STEP via 3D IoU, and appends passing
pairs to verified_pairs.jsonl.

Each passing pair gets a new stem like: <orig_stem>_rec_<provider>
Source tag: run_synth_reconstruct_<provider>

Usage:
    LD_LIBRARY_PATH=/workspace/.local/lib PYTHONUNBUFFERED=1 \\
    uv run python scripts/data_generation/run_synth_reconstruct.py \\
      --provider openai --model gpt-5.2 --resume

    # GLM:
    uv run python scripts/data_generation/run_synth_reconstruct.py \\
      --provider glm --model glm-4.6v --resume
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_LD = "/workspace/.local/lib"
_cur = os.environ.get("LD_LIBRARY_PATH", "")
if _LD not in _cur:
    os.environ["LD_LIBRARY_PATH"] = f"{_LD}:{_cur}".strip(":")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)
except ImportError:
    pass

from scripts.data_generation.build_verified_pairs import (  # noqa: E402
    IOU_THRESHOLD,
    _classify_error_type,
    _compute_iou,
    _ensure_export_line,
    _execute_cadquery_script,
    _generate_code_codex,
    _generate_code_openai_with_retry,
    _patch_output_step_path,
    _strip_markdown_fences,
)
from scripts.data_generation.codex_validation import (  # noqa: E402
    _append_checkpoint,
    _load_checkpoint,
    _load_verified_stems,
)

VERIFIED_PAIRS = REPO_ROOT / "data/data_generation/verified/verified_pairs.jsonl"
OUT_DIR = REPO_ROOT / "data/data_generation/codex_validation/run_synth_reconstruct"
RUN_NAME = "run_synth_reconstruct"

SYNTH_SYSTEM_PROMPT = (
    "You are a CadQuery expert. Given a 3D part specification (op type + dimensions in mm), "
    "write minimal CadQuery Python code that creates the described geometry. "
    "Output ONLY the Python code, no explanation.\n\n"
    "VALID CadQuery APIs:\n"
    "  Sketch: .rect(w,h) .circle(r)\n"
    "  Lines: .lineTo(x,y) .line(dx,dy) .moveTo(x,y) .close()\n"
    "  Solid: .extrude(d) .revolve(deg,(ox,oy,oz),(ax,ay,az)) .shell(t) .loft()\n"
    "  Bool: .cut() .hole(d) .cutThruAll()\n"
    "  Modify: .fillet(r) .chamfer(d) .faces(sel) .edges(sel)\n"
    "  Arrays: .polarArray(r,start,deg,n) .rarray(xs,ys,nx,ny)\n"
    "  Loft wires: chain profiles via .workplane(offset=h) then .loft()\n"
    "  Planes: 'XY','XZ','YZ'\n\n"
    "OP-SPECIFIC PATTERNS:\n"
    "revolve_ring: cq.Workplane('XZ').moveTo(inner,0).lineTo(outer,0).lineTo(outer,h)"
    ".lineTo(inner,h).close().revolve(360,(0,0,0),(0,1,0))\n"
    "revolve_cylinder: cq.Workplane('XZ').moveTo(0,0).lineTo(r,0).lineTo(r,h)"
    ".lineTo(0,h).close().revolve(360,(0,0,0),(0,1,0))\n"
    "loft (chain workplanes): cq.Workplane('XY').circle(r1).workplane(offset=h).circle(r2).loft()\n"
    "shell (open top): cq.Workplane('XY').rect(w,d).extrude(h).faces('>Z').shell(-t)\n"
    "polar_array_holes: cq.Workplane('XY').circle(disc_r).extrude(h)"
    ".faces('>Z').workplane().polarArray(bolt_circle_r_mm,0,360,n).hole(hole_d)\n"
    "polar_array_bosses: cq.Workplane('XY').circle(base_r).extrude(h)"
    ".faces('>Z').workplane().polarArray(bolt_circle_r_mm,0,360,n).circle(boss_r).extrude(boss_h)\n"
    "rect_array_holes: cq.Workplane('XY').rect(w,d).extrude(h)"
    ".faces('>Z').workplane().rarray(xs_mm,ys_mm,nx,ny).hole(hole_d_mm)\n"
)


def _build_synth_user_prompt(params: dict) -> str:
    """Build the user prompt for synthetic params-based codegen."""
    params_str = json.dumps(params, indent=2)
    return (
        f"3D part specification (all dimensions in mm):\n{params_str}\n\n"
        "Rules:\n"
        "- Only: import cadquery as cq\n"
        "- Hard-code ALL values directly\n"
        "- Final result in variable 'result'\n"
        "- Last line: result.val().exportStep('output.step')\n"
        "- Output ONLY the Python code, no explanation"
    )


def _try_synth_codegen(
    params: dict,
    provider: str,
    model: str,
    reasoning_effort: str = "high",
) -> tuple[str | None, str | None, str]:
    """Generate CadQuery from params using specified provider."""
    user_prompt = _build_synth_user_prompt(params)
    empty_json: dict = {}

    if provider == "openai":
        code, err = _generate_code_openai_with_retry(
            empty_json, model=model, reasoning_effort=reasoning_effort,
            user_prompt=user_prompt, system_prompt=SYNTH_SYSTEM_PROMPT,
        )
        return code, err, "openai"

    # codex / auto
    codex_prompt = (
        "Write output.py containing CadQuery Python code.\n"
        f"{user_prompt}\n"
        "- Write ONLY the Python code to output.py, nothing else"
    )
    code, err = _generate_code_codex(
        empty_json, model=model, reasoning_effort=reasoning_effort, prompt=codex_prompt,
    )
    if code:
        return code, None, "codex"

    if provider == "codex":
        return None, err, "codex"

    # auto fallback chain
    err_type = _classify_error_type(err or "")
    if err_type in ("codex_auth_error", "oauth_error", "timeout", "other"):
        code2, err2 = _generate_code_openai_with_retry(
            empty_json, model="gpt-5.2", reasoning_effort=reasoning_effort,
            user_prompt=user_prompt, system_prompt=SYNTH_SYSTEM_PROMPT,
        )
        if code2:
            return code2, None, "openai"
        return None, f"codex: {err}; openai: {err2}", "openai"

    return None, err, "codex"


def _augment_params_from_cq(params: dict, cq_code_path: str | None) -> dict:
    """Fill in missing params by reading the original CQ source code."""
    if not cq_code_path:
        return params
    full_path = REPO_ROOT / cq_code_path
    if not full_path.exists():
        return params
    code = full_path.read_text(encoding="utf-8")
    op = params.get("op", "")
    if op in ("polar_array_bosses", "polar_array_holes") and "bolt_circle_r_mm" not in params:
        m = re.search(r"polarArray\(\s*([\d.]+)", code)
        if m:
            params = dict(params, bolt_circle_r_mm=float(m.group(1)))
    elif op == "rect_array_holes" and "xs_mm" not in params:
        m = re.search(r"rarray\(\s*([\d.]+)\s*,\s*([\d.]+)", code)
        if m:
            params = dict(params, xs_mm=float(m.group(1)), ys_mm=float(m.group(2)))
    return params


def _load_synth_pairs() -> list[dict]:
    """Load synthetic diverse pairs from verified_pairs.jsonl (deduped by stem, last wins)."""
    if not VERIFIED_PAIRS.exists():
        return []
    by_stem: dict[str, dict] = {}
    for line in VERIFIED_PAIRS.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("source") == "run_synthetic_diverse" and rec.get("gen_step_path"):
                by_stem[rec["stem"]] = rec  # last occurrence wins
        except Exception:  # noqa: BLE001
            pass
    return list(by_stem.values())


def _append_verified(rec: dict) -> None:
    VERIFIED_PAIRS.parent.mkdir(parents=True, exist_ok=True)
    with VERIFIED_PAIRS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def _execute(code: str, out_step: Path, timeout: int = 30) -> tuple[bool, str | None]:
    patched = _patch_output_step_path(code, out_step)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(patched)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return False, r.stderr.strip()[:300]
        if not out_step.exists():
            return False, "no STEP produced"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        Path(tmp).unlink(missing_ok=True)


def _run(
    limit: int,
    provider: str,
    model: str,
    reasoning_effort: str,
    resume: bool,
    out_dir: Path,
) -> None:
    gen_step_dir = out_dir / "generated_step"
    cq_dir = out_dir / "cadquery"
    gen_step_dir.mkdir(parents=True, exist_ok=True)
    cq_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = out_dir / "checkpoint.jsonl"
    done_stems: set[str] = _load_checkpoint(checkpoint_path) if resume else set()
    verified_stems: set[str] = _load_verified_stems(VERIFIED_PAIRS)

    pairs = _load_synth_pairs()
    if not pairs:
        print("No synthetic diverse pairs found in verified_pairs.jsonl.")
        sys.exit(1)
    if limit > 0:
        pairs = pairs[:limit]

    print(
        f"Loaded {len(pairs)} synthetic pairs. "
        f"provider={provider} model={model} resume={resume}\n"
    )
    ok = fail = skip = 0

    for i, pair in enumerate(pairs, 1):
        orig_stem = pair["stem"]
        new_stem = f"{orig_stem}_rec_{provider}"
        print(f"[{i}/{len(pairs)}] {orig_stem}")

        if new_stem in done_stems:
            print("  SKIP (checkpoint)")
            skip += 1
            continue

        if new_stem in verified_stems:
            print("  SKIP (already verified)")
            skip += 1
            _append_checkpoint(checkpoint_path, {"stem": new_stem, "stage": "done", "ok": True, "iou": 1.0})
            continue

        params = pair.get("params", {})
        if not params:
            print("  SKIP (no params in record)")
            skip += 1
            continue
        params = _augment_params_from_cq(params, pair.get("cq_code_path"))

        gt_step = REPO_ROOT / pair["gen_step_path"]
        if not gt_step.exists():
            print(f"  SKIP (GT STEP not found: {gt_step})")
            _append_checkpoint(checkpoint_path, {"stem": new_stem, "stage": "gt_missing", "ok": False})
            skip += 1
            continue

        # Codegen
        code, err, used_provider = _try_synth_codegen(
            params, provider=provider, model=model, reasoning_effort=reasoning_effort,
        )
        if not code:
            print(f"  FAIL codegen: {err}")
            _append_checkpoint(checkpoint_path, {"stem": new_stem, "stage": "codegen", "ok": False, "error": err})
            fail += 1
            continue

        # Execute
        gen_step = gen_step_dir / f"{new_stem}.step"
        success, exec_err = _execute(code, gen_step)
        if not success:
            print(f"  FAIL exec: {exec_err}")
            _append_checkpoint(checkpoint_path, {"stem": new_stem, "stage": "execute", "ok": False, "error": exec_err})
            fail += 1
            continue

        # IoU
        iou, iou_err = _compute_iou(gt_step, gen_step)
        verified = iou is not None and iou >= IOU_THRESHOLD
        print(f"  IoU={f'{iou:.4f}' if iou is not None else 'None'}  {'PASS' if verified else 'FAIL'}"
              + (f" ({iou_err})" if iou_err else ""))

        cq_file = cq_dir / f"{new_stem}.py"
        cq_file.write_text(code, encoding="utf-8")

        iou_val = round(iou, 6) if iou is not None else None
        result = {
            "stem": new_stem,
            "stage": "done",
            "ok": verified,
            "iou": iou_val,
            "provider": used_provider,
        }
        _append_checkpoint(checkpoint_path, result)

        if verified:
            ok += 1
            now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            source = f"{RUN_NAME}_{used_provider}"
            vp_rec = {
                "stem": new_stem,
                "base_stem": orig_stem,
                "raw_step_path": pair.get("raw_step_path"),
                "ops_json_path": None,
                "gen_step_path": _rel(gen_step),
                "cq_code_path": _rel(cq_file),
                "views_raw_dir": pair.get("views_raw_dir"),
                "views_gen_dir": None,
                "complexity_class": pair.get("complexity_class", params.get("op", "synth")),
                "iou": iou_val,
                "visual_verdict": "SKIP",
                "visual_reason": "synth reconstruct",
                "verified": True,
                "source": source,
                "timestamp": now,
                "params": params,
            }
            _append_verified(vp_rec)
            print(f"  → harvested: {new_stem}")
        else:
            fail += 1

    print(f"\nDONE: {ok} pass, {fail} fail, {skip} skip / {len(pairs)} total")
    vp_count = sum(1 for _ in VERIFIED_PAIRS.open()) if VERIFIED_PAIRS.exists() else 0
    print(f"verified_pairs.jsonl: {vp_count} total")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="auto",
                        choices=["auto", "codex", "openai"],
                        help="LLM provider (default: auto)")
    parser.add_argument("--model", default="gpt-5.2",
                        help="Model name (default: gpt-5.2)")
    parser.add_argument("--effort", default="high",
                        help="Reasoning effort for o-series models")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max pairs to process (0=all)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip stems already in checkpoint")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR,
                        help="Output directory")
    args = parser.parse_args()

    _run(
        limit=args.limit,
        provider=args.provider,
        model=args.model,
        reasoning_effort=args.effort,
        resume=args.resume,
        out_dir=args.out_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
