#!/usr/bin/env python3
"""ReAct-based CadQuery code generation for Fusion360 stems.

Loop per stem:
  Round 1: Generate CQ code from F360 JSON
  Round N: Feed (original code + execution error/IoU) back → ask model to fix
  Stop when IoU >= 0.99 or max_rounds exhausted

Usage:
  # Retry GLM-balance failures with ReAct (codex provider):
  export PATH="$HOME/.local/bin:$PATH"
  LD_LIBRARY_PATH=/workspace/.local/lib PYTHONUNBUFFERED=1 \\
  uv run python3 scripts/data_generation/react_codegen.py \\
    --retry-reason glm_balance glm_timeout exec_error iou_zero \\
    --provider codex --model gpt-5.3-codex \\
    --max-rounds 3 --limit 500 \\
    --run-name react_v1 \\
    --out-dir data/data_generation/codex_validation \\
    >> /tmp/react_v1.log 2>&1 &

  # Resume after interruption:
    ... --resume

  # Specific stems:
    --stems 43934_912ff891_0027 101289_a540a982_0000
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_LD = "/workspace/.local/lib"
_cur = os.environ.get("LD_LIBRARY_PATH", "")
if _LD not in _cur:
    os.environ["LD_LIBRARY_PATH"] = f"{_LD}:{_cur}".strip(":")

REPO_ROOT = Path(__file__).resolve().parents[2]
STEM_FS = REPO_ROOT / "data/data_generation/generated_data/fusion360"
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=True)
except ImportError:
    pass

from scripts.data_generation.build_verified_pairs import (  # noqa: E402
    GT_STEP_DIR,
    IOU_THRESHOLD,
    SYSTEM_PROMPT,
    _build_index,
    _classify_complexity,
    _compute_iou,
    _execute_cadquery_script,
    _generate_code_openai_with_retry,
    _safe_json_load,
    _step_metrics,
)
from scripts.data_generation.codex_validation import (  # noqa: E402
    _try_codegen,
    _append_checkpoint,
    _load_checkpoint,
)
import scripts.data_generation.db as db

JSON_DIR = REPO_ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"

# ---------------------------------------------------------------------------
# ReAct prompts
# ---------------------------------------------------------------------------

REACT_FIX_SYSTEM = SYSTEM_PROMPT  # same system prompt

# ---------------------------------------------------------------------------
# Normalized-output prompts (for --normalize / T8b mode)
# ---------------------------------------------------------------------------

NORM_SYSTEM = """\
You are an expert CadQuery programmer. Your task is to rewrite CadQuery code so the \
output shape is in NORMALIZED space: bounding box center at origin, longest dimension = 1.0.

Rules:
- All coordinates, dimensions, and distances must be pre-multiplied by the scale factor provided.
- Center offset must be subtracted before scaling.
- Output ONLY clean Python code. No formulas like `scale = ...` in the output — hardcode the final numbers.
- Last line must be: result.val().exportStep("output.step")
"""

NORM_REWRITE_TEMPLATE = """\
Rewrite the CadQuery code below into NORMALIZED space.

## Normalization transform (precomputed from GT STEP bounding box)
GT bbox center: cx={cx:.6f}  cy={cy:.6f}  cz={cz:.6f}  (all in mm)
GT longest dimension: {longest:.6f} mm
Scale factor: s = {scale:.8f}  (= 1 / {longest:.6f})

## Rules — two types of numbers:
1. DISTANCES (rect dims, extrude depth, radii, arc lengths): scale only
     d_norm = d_mm * s = d_mm * {scale:.8f}

2. COORDINATES (absolute positions): translate then scale using the WORLD axis table below

## CRITICAL — CadQuery workplane axis mapping
Each Workplane maps its local (u, v, normal) axes to world (X, Y, Z):

  Workplane("XY"):
    moveTo(u, v)              → u=worldX, v=worldY
    transformed(offset=(a,b,c)) → a=worldX, b=worldY, c=worldZ(normal)
    coord_norm: a→(a-{cx:.6f})*s,  b→(b-{cy:.6f})*s,  c→(c-{cz:.6f})*s

  Workplane("XZ"):
    moveTo(u, v)              → u=worldX, v=worldZ
    transformed(offset=(a,b,c)) → a=worldX, b=worldZ, c=worldY(normal)
    coord_norm: a→(a-{cx:.6f})*s,  b→(b-{cz:.6f})*s,  c→(c-{cy:.6f})*s

  Workplane("YZ"):
    moveTo(u, v)              → u=worldY, v=worldZ
    transformed(offset=(a,b,c)) → a=worldY, b=worldZ, c=worldX(normal)
    coord_norm: a→(a-{cy:.6f})*s,  b→(b-{cz:.6f})*s,  c→(c-{cx:.6f})*s

## Step-by-step process
1. Identify current Workplane (XY/XZ/YZ)
2. Evaluate every arithmetic expression to get mm value
3. Classify each value as DISTANCE or COORDINATE (and which world axis)
4. Apply the correct formula from the table above
5. Write clean output with hardcoded computed floats — no variables, no formulas

## Original code
```python
{code}
```

Output ONLY the rewritten Python code with hardcoded normalized values.
"""

NORM_FIX_TEMPLATE = """\
Your normalized CadQuery code ran but the geometry does not match the normalized GT \
(IoU={iou:.4f}, need ≥ 0.95).

## Normalization transform (precomputed)
GT center: cx={cx:.6f}  cy={cy:.6f}  cz={cz:.6f}  mm  |  scale = {scale:.8f}

GT normalized volume: {gt_vol:.6f}
Generated normalized volume: {gen_vol:.6f}
Volume ratio: {vol_ratio:.3f}

## Workplane axis mapping (common mistake — verify your offsets use the right center)
  Workplane("XZ"): transformed(offset=(a,b,c)) → a=worldX→(a-{cx:.6f})*s, b=worldZ→(b-{cz:.6f})*s
  Workplane("XY"): transformed(offset=(a,b,c)) → a=worldX→(a-{cx:.6f})*s, b=worldY→(b-{cy:.6f})*s
  Workplane("YZ"): transformed(offset=(a,b,c)) → a=worldY→(a-{cy:.6f})*s, b=worldZ→(b-{cz:.6f})*s

{vision_hint}

Your code:
```python
{code}
```

Fix the code so all coordinates are correctly normalized. Hardcode computed values — no formula variables.
Output ONLY the corrected Python code.
"""

NORM_GEN_FROM_JSON_TEMPLATE = """\
## Normalization transform (precomputed from GT STEP)
GT bounding box center: cx={cx:.6f}  cy={cy:.6f}  cz={cz:.6f}  (mm)
GT longest dimension: {longest:.6f} mm
Scale factor s = 1 / {longest:.6f} = {scale:.8f}

## Task
Generate CadQuery code for the Fusion360 part described in the JSON below.
Output shape MUST be in normalized space (bbox center at origin, longest dim = 1.0).

## CRITICAL — CadQuery workplane axis mapping
  Workplane("XY"):  moveTo(u,v) → u=worldX, v=worldY
    transformed(offset=(a,b,c)): a→(a-{cx:.6f})*s, b→(b-{cy:.6f})*s, c→(c-{cz:.6f})*s

  Workplane("XZ"):  moveTo(u,v) → u=worldX, v=worldZ
    transformed(offset=(a,b,c)): a→(a-{cx:.6f})*s, b→(b-{cz:.6f})*s, c→(c-{cy:.6f})*s

  Workplane("YZ"):  moveTo(u,v) → u=worldY, v=worldZ
    transformed(offset=(a,b,c)): a→(a-{cy:.6f})*s, b→(b-{cz:.6f})*s, c→(c-{cx:.6f})*s

  Distances (rect dims, extrude depth, radii): d_norm = d_mm * s  (no offset)

Hardcode ALL computed values directly. Do NOT include formula variables.
Last line: result.val().exportStep("output.step")

## Fusion360 JSON
{json_snippet}
"""

REACT_FIX_USER_TEMPLATE = """\
Your previous CadQuery code failed. Here is the code you wrote:

```python
{code}
```

Execution result:
{result}

Fix the code so it runs correctly and matches the geometry.
Output ONLY the corrected Python code.
"""

REACT_IOU_USER_TEMPLATE = """\
Your CadQuery code ran but the geometry does not match (IoU={iou:.4f}, need ≥ {threshold:.2f}).

GT volume: {gt_vol:.2f} mm³
Generated volume: {gen_vol:.2f} mm³
Volume ratio (gen/GT): {vol_ratio:.3f}

Original Fusion360 JSON:
{json_snippet}

Your code:
```python
{code}
```

{hint}

Fix the code to better match the GT geometry.
Output ONLY the corrected Python code.
"""

REACT_IOU_VISION_USER_TEMPLATE = """\
Your CadQuery code ran but the geometry does not match (IoU={iou:.4f}, need ≥ {threshold:.2f}).

GT volume: {gt_vol:.2f} mm³
Generated volume: {gen_vol:.2f} mm³
Volume ratio (gen/GT): {vol_ratio:.3f}

Two images follow: GT part composite (front/right/top/iso), then your generated part composite.
Use the visual comparison to identify the shape difference.

Original Fusion360 JSON:
{json_snippet}

Your code:
```python
{code}
```

{hint}

Fix the code to better match the GT geometry.
Output ONLY the corrected Python code.
"""


def _get_norm_params(gt_step_path: str) -> tuple[float, float, float, float]:
    """Return (cx, cy, cz, longest) from GT STEP bounding box."""
    import cadquery as cq
    shape = cq.importers.importStep(gt_step_path)
    bb = shape.val().BoundingBox()
    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2
    cz = (bb.zmin + bb.zmax) / 2
    longest = max(bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
    return cx, cy, cz, longest


def _iou_vs_norm_step(gt_norm_step: str, gen_step: str) -> float:
    """Compute IoU between gen_step (already in norm space) and gt_norm_step."""
    import cadquery as cq
    gt_s = cq.importers.importStep(gt_norm_step)
    gen_s = cq.importers.importStep(gen_step)
    vgt = float(gt_s.val().Volume())
    vgen = float(gen_s.val().Volume())
    vc = float(gt_s.val().intersect(gen_s.val()).Volume())
    denom = vgt + vgen - vc
    return vc / denom if denom > 1e-12 else 0.0


def _harvest_norm(stem: str, norm_cq_path: str, norm_iou: float) -> None:
    """Update norm_cq_code_path + norm_iou + sft_ready in verified_parts.csv."""
    import fcntl
    import pandas as pd
    lock_path = str(db.VERIFIED_CSV) + ".lock"
    with open(lock_path, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            vdf = pd.read_csv(db.VERIFIED_CSV)
            mask = vdf["stem"] == stem
            if not mask.any():
                return
            idx = vdf[mask].index[0]
            vdf["sft_ready"] = vdf["sft_ready"].astype(object)
            vdf.at[idx, "norm_cq_code_path"] = norm_cq_path
            vdf.at[idx, "norm_iou"] = round(norm_iou, 4)
            gt_norm = str(vdf.at[idx, "gt_norm_step_path"] or "")
            vdf.at[idx, "sft_ready"] = "true" if (gt_norm and norm_cq_path and norm_iou >= 0.95) else "false"
            vdf.to_csv(db.VERIFIED_CSV, index=False)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _vol_hint(gen_vol: float, gt_vol: float) -> str:
    if gt_vol <= 0:
        return ""
    ratio = gen_vol / gt_vol
    if ratio > 1.5:
        return "Hint: generated part is too large — check extrude distances, both=True usage, or extra features."
    if ratio < 0.7:
        return "Hint: generated part is too small — check extrude distances or missing features."
    return "Hint: volume is close but shape differs — check sketch coordinates, plane orientation, or feature positions."


_FAILURE_LABELS = {
    "dim_error/local_feat", "dim_error/aspect_ratio",
    "wrong_plane/non_xy_high", "wrong_plane/non_xy_low",
    "feature_count", "wrong_primitive", "partial_geom",
    "degenerate", "exec_error",
}

_CLASSIFY_SYSTEM = (
    "You classify CAD code generation failures. "
    "Output EXACTLY one label from this list, nothing else:\n"
    "dim_error/local_feat | dim_error/aspect_ratio | "
    "wrong_plane/non_xy_high | wrong_plane/non_xy_low | "
    "feature_count | wrong_primitive | partial_geom | degenerate | exec_error"
)


def _classify_failure_code(
    last_err: str,
    iou: float,
    code: str | None,
    gt_vol: float,
    gen_vol: float,
    json_snippet: str,
    model: str,
) -> str:
    """Ask LLM to classify the failure type. Returns one of _FAILURE_LABELS."""
    if last_err or code is None:
        return "exec_error"
    vol_ratio = gen_vol / max(gt_vol, 1e-9)
    user_prompt = (
        f"Final IoU: {iou:.4f}  GT vol: {gt_vol:.2f}mm³  "
        f"Gen vol: {gen_vol:.2f}mm³  vol_ratio: {vol_ratio:.3f}\n\n"
        f"Code:\n```python\n{code[:2000]}\n```\n\n"
        f"Fusion360 JSON (trimmed):\n{json_snippet[:800]}"
    )
    try:
        raw, _err = _generate_code_openai_with_retry(
            json_data={},
            model=model,
            reasoning_effort="low",
            user_prompt=user_prompt,
            system_prompt=_CLASSIFY_SYSTEM,
        )
        if raw:
            raw = raw.strip().lower()
            if raw in _FAILURE_LABELS:
                return raw
            # substring match fallback
            for label in _FAILURE_LABELS:
                if label in raw:
                    return label
    except Exception:
        pass
    # heuristic fallback
    if iou < 0.05:
        return "degenerate" if gen_vol < gt_vol * 0.1 else "wrong_plane/non_xy_low"
    if gen_vol > gt_vol * 1.4:
        return "feature_count"
    if gen_vol < gt_vol * 0.5:
        return "partial_geom"
    return "dim_error/local_feat"


def _encode_png_b64(path: Path) -> str | None:
    """Return base64-encoded PNG string, or None if file missing/unreadable."""
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return None


def _render_composite(step_path: Path, tmp_dir: Path, prefix: str = "") -> Path | None:
    """Render 4-view composite (front/right/top/iso) for a STEP file.

    For GT steps, checks stem-centric FS for a pre-existing composite first
    to avoid redundant renders.
    Returns path to composite.png or None on failure.
    """
    # Check for pre-existing GT composite in stem-centric FS
    step_p = Path(step_path)
    if step_p.parts and "gt" in step_p.parts:
        gt_idx = list(step_p.parts).index("gt")
        gt_views = step_p.parents[len(step_p.parts) - gt_idx - 2] / "gt" / "views"
        for name in ("composite.png", "raw_composite.png"):
            candidate = gt_views / name
            if candidate.exists():
                return candidate

    try:
        from render_normalized_views import render_step_normalized
        paths = render_step_normalized(str(step_path), str(tmp_dir))
        cp = paths.get("composite")
        return Path(cp) if cp else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Normalized ReAct loop (T8b — fix low_iou norm stems)
# ---------------------------------------------------------------------------

def react_generate_norm(
    stem: str,
    cq_path: str,
    gt_step_path: str,
    gt_norm_step_path: str,
    run_name: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    max_rounds: int,
    vision: bool = False,
    keep_failed: bool = False,
) -> dict:
    """ReAct loop that rewrites existing CQ code into normalized space.

    Round 1: rewrite existing verified cq.py → normalized coords using precomputed params.
    Round 2+: fix normalized code based on IoU vs gt_norm_step.
    Writes output to <stem_dir>/cq_norm.py (never overwrites cq.py).
    """
    base = stem.rsplit("_claude_fixed", 1)[0]
    norm_dir = STEM_FS / base / f"verified_{run_name}"
    norm_dir.mkdir(parents=True, exist_ok=True)
    norm_py = norm_dir / "cq_norm.py"
    gen_step = norm_dir / "gen_norm.step"

    # Compute norm params from GT STEP
    try:
        cx, cy, cz, longest = _get_norm_params(gt_step_path)
    except Exception as e:
        return {"stem": stem, "status": "skip", "error": f"norm_params: {e}"}
    if longest < 1e-9:
        return {"stem": stem, "status": "skip", "error": "degenerate GT"}
    scale = 1.0 / longest

    try:
        orig_code = Path(cq_path).read_text(encoding="utf-8")
    except Exception as e:
        return {"stem": stem, "status": "skip", "error": f"read_cq: {e}"}

    iou = 0.0
    gen_vol = 0.0
    code: str | None = None
    last_err = ""
    rounds_done = 0

    # GT norm volume (for hints)
    try:
        import cadquery as _cq_mod
        gt_norm_shape = _cq_mod.importers.importStep(gt_norm_step_path)
        gt_norm_vol = float(gt_norm_shape.val().Volume())
    except Exception:
        gt_norm_vol = 0.0

    messages: list[dict] = []

    for round_num in range(1, max_rounds + 1):
        rounds_done = round_num
        t0 = time.time()
        cur_vision_images: list[str] = []

        if round_num == 1:
            user_msg = NORM_REWRITE_TEMPLATE.format(
                cx=cx, cy=cy, cz=cz, longest=longest, scale=scale,
                code=orig_code,
            )
            messages = [
                {"role": "system", "content": NORM_SYSTEM},
                {"role": "user", "content": user_msg},
            ]
        else:
            vision_hint = ""
            if vision and provider == "openai":
                with tempfile.TemporaryDirectory() as td:
                    tmp = Path(td)
                    gt_comp = _render_composite(Path(gt_norm_step_path), tmp / "gt")
                    gen_comp = _render_composite(gen_step, tmp / "gen") if gen_step.exists() else None
                    if gt_comp and gen_comp:
                        gt_b64 = _encode_png_b64(gt_comp)
                        gen_b64 = _encode_png_b64(gen_comp)
                        if gt_b64 and gen_b64:
                            cur_vision_images = [gt_b64, gen_b64]
                            vision_hint = "Two images follow: GT normalized composite, then your generated composite."
            user_msg = NORM_FIX_TEMPLATE.format(
                iou=iou, cx=cx, cy=cy, cz=cz, scale=scale,
                gt_vol=gt_norm_vol, gen_vol=gen_vol,
                vol_ratio=gen_vol / max(gt_norm_vol, 1e-12),
                vision_hint=vision_hint,
                code=code,
            )
            messages.append({"role": "user", "content": user_msg})

        new_code, err = _call_fix(messages, provider=provider, model=model,
                                  reasoning_effort=reasoning_effort,
                                  vision_images=cur_vision_images,
                                  system_prompt=NORM_SYSTEM)
        if not new_code:
            last_err = err or "no output"
            print(f"  [R{round_num}] codegen failed: {last_err[:80]}")
            break

        code = new_code
        messages.append({"role": "assistant", "content": code})
        norm_py.write_text(code, encoding="utf-8")

        sec = round(time.time() - t0, 1)
        ran, run_err = _execute_cadquery_script(code, gen_step, timeout_sec=60)
        if not ran:
            last_err = run_err or "execute failed"
            print(f"  [R{round_num}] exec error ({sec}s): {last_err[:80]}")
            continue

        try:
            iou = _iou_vs_norm_step(gt_norm_step_path, str(gen_step))
            gen_vol_raw, _, _ = _step_metrics(gen_step)
            gen_vol = gen_vol_raw or 0.0
            last_err = ""
            print(f"  [R{round_num}] norm_IoU={iou:.4f} ({sec}s) {'✓ PASS' if iou >= 0.95 else '✗ FAIL'}")
        except Exception as e:
            last_err = str(e)
            print(f"  [R{round_num}] iou error: {last_err[:60]}")

        if iou >= 0.95:
            break

    iou_pass = iou >= 0.95
    rel_norm = str(norm_py.relative_to(REPO_ROOT)) if iou_pass else ""

    if iou_pass:
        _harvest_norm(stem, rel_norm, iou)
        print(f"  → norm_iou={iou:.4f} ✓ wrote {rel_norm}")
    else:
        if norm_py.exists() and not keep_failed:
            norm_py.unlink()

    return {
        "stem": stem,
        "ok": iou_pass,
        "norm_iou": round(iou, 4),
        "norm_cq_code_path": rel_norm,
        "rounds": rounds_done,
        "error": last_err if not iou_pass else "",
    }


# ---------------------------------------------------------------------------
# Single-stem ReAct loop
# ---------------------------------------------------------------------------

def react_generate(
    rec,
    out_dir: Path,
    provider: str,
    model: str,
    reasoning_effort: str,
    max_rounds: int,
    run_name: str,
    vision: bool = False,
    normalize: bool = False,
) -> dict:
    """Run ReAct loop for one stem. Returns checkpoint-compatible dict.

    normalize=True: generate directly in normalized space.
      - Round 1 prompt includes precomputed norm params (cx,cy,cz,scale).
      - Validation vs gt_norm_step (threshold 0.95, not 0.99).
      - Output written to cq_norm.py; norm_cq_code_path + norm_iou updated in CSV.
    """
    stem = rec.base_stem
    stem_dir = STEM_FS / stem / run_name
    stem_dir.mkdir(parents=True, exist_ok=True)
    gen_step = stem_dir / "gen.step"
    code_path = stem_dir / ("cq_norm.py" if normalize else "cq.py")
    code_dir = stem_dir

    gt_vol, gt_dims, gt_err = _step_metrics(rec.gt_step_path)
    if gt_err:
        return {"stem": stem, "stage": "gt_step", "ok": False, "error": gt_err,
                "provider": provider, "rounds": 0}

    # Resolve norm params and gt_norm_step path when normalize=True
    norm_params: tuple[float, float, float, float] | None = None
    gt_norm_step: Path | None = None
    if normalize:
        try:
            norm_params = _get_norm_params(str(rec.gt_step_path))
        except Exception as e:
            return {"stem": stem, "stage": "norm_params", "ok": False, "error": str(e),
                    "provider": provider, "rounds": 0}
        gt_norm_step = STEM_FS / stem / "gt" / "gt_norm.step"
        if not gt_norm_step.exists():
            # Generate gt_norm.step on-the-fly
            try:
                cx, cy, cz, longest = norm_params
                import cadquery as _cq_mod
                from OCP.gp import gp_Trsf, gp_Vec, gp_Pnt
                from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
                _shape = _cq_mod.importers.importStep(str(rec.gt_step_path))
                t = gp_Trsf(); t.SetTranslation(gp_Vec(-cx, -cy, -cz))
                s = gp_Trsf(); s.SetScale(gp_Pnt(0, 0, 0), 1.0 / longest)
                ts = gp_Trsf(); ts.Multiply(s); ts.Multiply(t)
                norm_shape = _cq_mod.Shape(BRepBuilderAPI_Transform(_shape.val().wrapped, ts, True).Shape())
                gt_norm_step.parent.mkdir(parents=True, exist_ok=True)
                norm_shape.exportStep(str(gt_norm_step))
            except Exception as e:
                return {"stem": stem, "stage": "gt_norm_step", "ok": False,
                        "error": f"gt_norm.step gen failed: {e}", "provider": provider, "rounds": 0}

    try:
        json_data = _safe_json_load(rec.json_path)
    except Exception as e:
        return {"stem": stem, "stage": "json_load", "ok": False, "error": str(e),
                "provider": provider, "rounds": 0}

    complexity = _classify_complexity(json_data)
    json_snippet = json.dumps(json_data, indent=2)[:3000]

    iou_threshold = 0.95 if normalize else IOU_THRESHOLD

    # Conversation history for multi-turn
    messages: list[dict] = []
    code: str | None = None
    last_err = ""
    iou = 0.0
    gen_vol = 0.0
    rounds_done = 0
    # Track round-1 outcome for correction pair collection
    r1_code: str | None = None
    r1_err: str = ""
    r1_iou: float = 0.0

    for round_num in range(1, max_rounds + 1):
        rounds_done = round_num
        t0 = time.time()

        if round_num == 1:
            if normalize:
                # Normalized mode: inject precomputed transform into JSON prompt
                cx, cy, cz, longest = norm_params
                scale = 1.0 / longest
                user_msg = NORM_GEN_FROM_JSON_TEMPLATE.format(
                    cx=cx, cy=cy, cz=cz, longest=longest, scale=scale,
                    json_snippet=json_snippet,
                )
                new_code, err = _call_fix(
                    [{"role": "system", "content": NORM_SYSTEM},
                     {"role": "user", "content": user_msg}],
                    provider=provider, model=model, reasoning_effort=reasoning_effort,
                    system_prompt=NORM_SYSTEM,
                )
                messages = [
                    {"role": "system", "content": NORM_SYSTEM},
                    {"role": "user", "content": user_msg},
                ]
            else:
                new_code, err, _ = _try_codegen(
                    json_data, provider=provider, model=model,
                    reasoning_effort=reasoning_effort,
                )
                messages = [
                    {"role": "system", "content": REACT_FIX_SYSTEM},
                    {"role": "user", "content": json.dumps(json_data)},
                ]
            if not new_code:
                last_err = err or "no output"
                print(f"  [R{round_num}] codegen failed: {last_err[:80]}")
                continue
            code = new_code
            messages.append({"role": "assistant", "content": code})
        else:
            # Fix round: build user message from last error/iou
            vision_images: list[str] = []
            gt_step_for_render = str(gt_norm_step) if normalize else str(rec.gt_step_path)
            if last_err:
                user_msg = REACT_FIX_USER_TEMPLATE.format(
                    code=code, result=last_err[:800]
                )
            elif normalize:
                cx, cy, cz, longest = norm_params
                scale = 1.0 / longest
                vision_hint = ""
                if vision and provider == "openai":
                    with tempfile.TemporaryDirectory() as td:
                        tmp = Path(td)
                        gt_comp  = _render_composite(Path(gt_step_for_render), tmp / "gt")
                        gen_comp = _render_composite(gen_step, tmp / "gen")
                        if gt_comp and gen_comp:
                            gt_b64 = _encode_png_b64(gt_comp)
                            gen_b64 = _encode_png_b64(gen_comp)
                            if gt_b64 and gen_b64:
                                vision_images = [gt_b64, gen_b64]
                                vision_hint = "Two images follow: GT normalized composite, then yours."
                user_msg = NORM_FIX_TEMPLATE.format(
                    iou=iou, cx=cx, cy=cy, cz=cz, scale=scale,
                    gt_vol=gt_vol, gen_vol=gen_vol,
                    vol_ratio=gen_vol / max(gt_vol, 1e-12),
                    vision_hint=vision_hint,
                    code=code,
                )
            else:
                iou_tmpl = REACT_IOU_USER_TEMPLATE
                if vision and provider == "openai":
                    with tempfile.TemporaryDirectory() as td:
                        tmp = Path(td)
                        gt_comp  = _render_composite(Path(rec.gt_step_path), tmp / "gt")
                        gen_comp = _render_composite(gen_step, tmp / "gen")
                        if gt_comp and gen_comp:
                            gt_b64  = _encode_png_b64(gt_comp)
                            gen_b64 = _encode_png_b64(gen_comp)
                            if gt_b64 and gen_b64:
                                vision_images = [gt_b64, gen_b64]
                                iou_tmpl = REACT_IOU_VISION_USER_TEMPLATE
                user_msg = iou_tmpl.format(
                    code=code,
                    iou=iou,
                    threshold=iou_threshold,
                    gt_vol=gt_vol,
                    gen_vol=gen_vol,
                    vol_ratio=gen_vol / max(gt_vol, 1),
                    json_snippet=json_snippet,
                    hint=_vol_hint(gen_vol, gt_vol),
                )
            messages.append({"role": "user", "content": user_msg})

            new_code, err = _call_fix(messages, provider=provider, model=model,
                                      reasoning_effort=reasoning_effort,
                                      vision_images=vision_images,
                                      system_prompt=NORM_SYSTEM if normalize else None)
            if not new_code:
                last_err = err or "no output"
                print(f"  [R{round_num}] fix codegen failed: {last_err[:80]}")
                break
            code = new_code
            messages.append({"role": "assistant", "content": code})

        sec = round(time.time() - t0, 1)
        code_path.write_text(code, encoding="utf-8")
        ran, run_err = _execute_cadquery_script(code, gen_step, timeout_sec=60)
        if not ran:
            last_err = run_err or "execute failed"
            print(f"  [R{round_num}] exec error ({sec}s): {last_err[:80]}")
            if round_num == 1:
                r1_code = code
                r1_err = last_err
                r1_iou = 0.0
                bad_path = code_dir / f"{stem}_bad.py"
                bad_path.write_text(code, encoding="utf-8")
            continue

        # Code ran — compute IoU
        if normalize:
            try:
                try_iou = _iou_vs_norm_step(str(gt_norm_step), str(gen_step))
                iou_err = ""
            except Exception as e:
                try_iou, iou_err = 0.0, str(e)
        else:
            try_iou, iou_err = _compute_iou(rec.gt_step_path, gen_step)

        if iou_err:
            last_err = iou_err
            print(f"  [R{round_num}] iou error ({sec}s): {iou_err[:60]}")
        else:
            gen_vol_val, _, _ = _step_metrics(gen_step)
            gen_vol = gen_vol_val or 0.0
            iou = try_iou
            last_err = ""
            label = "norm_IoU" if normalize else "IoU"
            print(f"  [R{round_num}] {label}={iou:.4f} ({sec}s) {'✓ PASS' if iou >= iou_threshold else '✗ FAIL'}")
        if round_num == 1 and iou < iou_threshold:
            r1_code = code
            r1_err = last_err
            r1_iou = iou
            bad_path = code_dir / f"{stem}_bad.py"
            bad_path.write_text(code, encoding="utf-8")
        if iou >= iou_threshold:
            break

    # Build result
    iou_pass = iou >= iou_threshold

    # Rename stem dir to verified_ prefix on pass
    if iou_pass:
        verified_dir = STEM_FS / stem / f"verified_{run_name}"
        if stem_dir.exists() and not verified_dir.exists():
            stem_dir.rename(verified_dir)
            stem_dir = verified_dir
            code_path = stem_dir / ("cq_norm.py" if normalize else "cq.py")
            gen_step = stem_dir / "gen.step"
            code_dir = stem_dir

    failure_code = ""
    if not iou_pass:
        failure_code = _classify_failure_code(
            last_err=last_err,
            iou=iou,
            code=code,
            gt_vol=gt_vol,
            gen_vol=gen_vol,
            json_snippet=json_snippet,
            model=model if "gpt" in model else "gpt-4o-mini",
        )
    # Classify round-1 failure code for correction pairs
    # (only when react succeeded on round>1, so we have both bad+good code)
    r1_failure_code = ""
    bad_cq_path = ""
    bad_path = code_dir / f"{stem}_bad.py"
    if r1_code is not None and bad_path.exists():
        try:
            bad_cq_path = str(bad_path.relative_to(REPO_ROOT))
        except ValueError:
            bad_cq_path = str(bad_path)
        if iou_pass and rounds_done > 1:
            r1_failure_code = _classify_failure_code(
                last_err=r1_err,
                iou=r1_iou,
                code=r1_code,
                gt_vol=gt_vol,
                gen_vol=gen_vol,
                json_snippet=json_snippet,
                model=model if "gpt" in model else "gpt-4o-mini",
            )
        elif not iou_pass:
            r1_failure_code = failure_code

    # Harvest normalize result into norm columns (not a new verified row)
    if normalize and iou_pass:
        rel_norm = str(code_path.relative_to(REPO_ROOT))
        _harvest_norm(stem, rel_norm, iou)

    return {
        "stem": stem,
        "stage": "done" if code is not None else "codegen",
        "ok": iou_pass,
        "complexity": complexity,
        "gt_vol": round(gt_vol, 4),
        "iou": round(iou, 6),
        "iou_pass": iou_pass,
        "norm_iou": round(iou, 6) if normalize else None,
        "failure_code": failure_code,
        "r1_failure_code": r1_failure_code,
        "bad_cq_path": bad_cq_path,
        "visual_verdict": "SKIP",
        "visual_reason": "",
        "provider": provider,
        "rounds": rounds_done,
        "error": last_err if not iou_pass else "",
    }


def _call_fix(
    messages: list[dict],
    provider: str,
    model: str,
    reasoning_effort: str,
    vision_images: list[str] | None = None,
    system_prompt: str | None = None,
) -> tuple[str | None, str]:
    """Call LLM with conversation history for fix round."""
    if provider == "openai":
        return _call_openai_fix(messages, model, reasoning_effort,
                                vision_images=vision_images or [],
                                system_prompt=system_prompt)
    elif provider == "codex":
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        json_data = {}
        code, err, _ = _try_codegen(
            json_data, provider="codex", model=model,
            reasoning_effort=reasoning_effort, user_prompt=last_user,
        )
        return code, err or ""
    else:
        return None, "provider not supported in fix round"


def _call_openai_fix(
    messages: list[dict],
    model: str,
    reasoning_effort: str,
    vision_images: list[str] | None = None,
    system_prompt: str | None = None,
) -> tuple[str | None, str]:
    """Multi-turn OpenAI fix call — collapses history into user_prompt.

    If vision_images is provided (list of base64 PNG strings), includes them
    as image_url content blocks alongside the text user message.
    system_prompt overrides the default REACT_FIX_SYSTEM when provided.
    """
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    if vision_images:
        content: list[dict] = [{"type": "text", "text": last_user}]
        for b64 in vision_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"},
            })
        user_prompt_content = json.dumps(content)
        is_multimodal = True
    else:
        user_prompt_content = last_user
        is_multimodal = False

    code, err = _generate_code_openai_with_retry(
        json_data={},
        model=model,
        reasoning_effort=reasoning_effort,
        user_prompt=user_prompt_content,
        system_prompt=system_prompt or REACT_FIX_SYSTEM,
        multimodal=is_multimodal,
    )
    return code, err or ""


# ---------------------------------------------------------------------------
# Regen verified-missing helpers
# ---------------------------------------------------------------------------

def _update_verified_row(stem: str, cq_code_path: str, gen_step_path: str) -> None:
    """Update cq_code_path and gen_step_path in-place in verified_parts.csv."""
    import pandas as pd
    vdf = pd.read_csv(db.VERIFIED_CSV)
    mask = vdf["stem"] == stem
    if mask.any():
        vdf.loc[mask, "cq_code_path"] = cq_code_path
        vdf.loc[mask, "gen_step_path"] = gen_step_path
        vdf.to_csv(db.VERIFIED_CSV, index=False)


def _run_regen_verified_missing(args) -> None:
    """Process verified stems whose cq_code_path file no longer exists on disk."""
    import pandas as pd
    from scripts.data_generation.build_verified_pairs import PartIndexRecord

    vdf = pd.read_csv(db.VERIFIED_CSV)

    # Filter: cq_code_path is set but file missing
    def _is_dead(row) -> bool:
        p = row.get("cq_code_path", "")
        if not p or (isinstance(p, float)):
            return False
        return not (REPO_ROOT / p).exists()

    dead = vdf[vdf.apply(_is_dead, axis=1)].copy()

    # Skip copy_gt and synth stems (no ops_json_path on disk)
    def _has_json(row) -> bool:
        p = row.get("ops_json_path", "")
        if not p or (isinstance(p, float)):
            return False
        return (REPO_ROOT / p).exists()

    dead = dead[dead.apply(_has_json, axis=1)]

    if args.offset:
        dead = dead.iloc[args.offset:]
    if args.limit:
        dead = dead.iloc[: args.limit]

    out_dir = REPO_ROOT / args.out_dir / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "checkpoint.jsonl"
    done_stems = _load_checkpoint(checkpoint_path) if args.resume else set()

    targets = dead[~dead["stem"].isin(done_stems)]
    print(f"Regen-verified-missing: {len(targets)} stems  provider={args.provider}  "
          f"model={args.model}  run={args.run_name}")

    passed = 0
    for i, (_, row) in enumerate(targets.iterrows(), 1):
        stem = row["stem"]
        # Resolve paths
        raw_step = REPO_ROOT / row["raw_step_path"]
        ops_json = REPO_ROOT / row["ops_json_path"]
        if not raw_step.exists() or not ops_json.exists():
            print(f"[{i}] {stem} — source files missing, skip")
            continue

        # base_stem: strip _claude_fixed suffix if present
        base_stem = stem.replace("_claude_fixed", "")

        rec = PartIndexRecord(
            base_stem=base_stem,
            stem=raw_step.stem,
            json_path=ops_json,
            gt_step_path=raw_step,
        )

        print(f"[{i}/{len(targets)}] {stem}")
        result = react_generate(
            rec=rec,
            out_dir=out_dir,
            provider=args.provider,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            max_rounds=args.max_rounds,
            run_name=args.run_name,
            vision=args.vision,
        )
        _append_checkpoint(checkpoint_path, result)

        if result.get("iou_pass"):
            passed += 1
            rel_cq = str(code_path.relative_to(REPO_ROOT))
            rel_step = str(gen_step.relative_to(REPO_ROOT))
            _update_verified_row(stem, rel_cq, rel_step)
            print(f"  → updated verified row  [pass {passed}]")
        else:
            fc = result.get("failure_code", "")
            if fc:
                print(f"  → still failing  failure_code={fc}")
        print()

    print(f"Done: {passed}/{len(targets)} regen passed")


# ---------------------------------------------------------------------------
# Normalize mode (T8b)
# ---------------------------------------------------------------------------

def _run_normalize_mode(args) -> None:
    """Process verified stems to produce normalized CQ code via LLM."""
    import pandas as pd

    vdf = pd.read_csv(db.VERIFIED_CSV)

    norm_gen = getattr(args, "norm_gen", False)

    has_gt_norm = vdf["gt_norm_step_path"].notna() & (vdf["gt_norm_step_path"] != "")
    has_cq = vdf["cq_code_path"].notna() & (vdf["cq_code_path"] != "")
    has_json = vdf["gt_json_path"].notna() & (vdf["gt_json_path"] != "")

    if norm_gen:
        # Include: stems with gt_norm_step + (has_cq OR has_json) + no norm_iou
        pool = vdf[has_gt_norm & (has_cq | has_json)].copy()
    else:
        # Code-rewrite mode requires cq_code_path
        pool = vdf[has_cq & has_gt_norm].copy()

    if args.norm_low_iou_only:
        low = pool["norm_iou"].isna() | (pool["norm_iou"] < 0.95)
        pool = pool[low]

    if args.stems:
        pool = pool[pool["stem"].isin(args.stems)]

    if args.offset:
        pool = pool.iloc[args.offset:]
    if args.limit:
        pool = pool.iloc[: args.limit]

    # For --norm-gen: load F360 index to use JSON-based generation instead of rewrite
    stem_to_rec: dict = {}
    if norm_gen:
        all_recs = _build_index(JSON_DIR, GT_STEP_DIR, limit=0, offset=0)
        stem_to_rec = {r.base_stem: r for r in all_recs}

    total = len(pool)
    mode = "json-gen" if norm_gen else "code-rewrite"
    print(f"Normalize mode ({mode}): {total} stems  provider={args.provider}  "
          f"model={args.model}  max_rounds={args.max_rounds}  run={args.run_name}")

    passed = 0
    for i, (_, row) in enumerate(pool.iterrows(), 1):
        stem = str(row["stem"])
        gt_step = str(REPO_ROOT / row["gt_step_path"]) if row.get("gt_step_path") else ""
        gt_norm_step = str(REPO_ROOT / row["gt_norm_step_path"])

        if not gt_step or not Path(gt_step).exists():
            print(f"[{i}/{total}] {stem} — skip (no gt_step)")
            continue
        if not Path(gt_norm_step).exists():
            print(f"[{i}/{total}] {stem} — skip (no gt_norm_step)")
            continue

        print(f"[{i}/{total}] {stem}")

        if norm_gen:
            # JSON-based generation: use F360 JSON + norm params
            base = stem.rsplit("_claude_fixed", 1)[0]
            rec = stem_to_rec.get(base)
            if rec is None:
                print(f"  skip: no F360 index entry")
                print()
                continue
            # Override gt_step with rec's path (may differ from verified_parts)
            result = react_generate(
                rec=rec,
                out_dir=REPO_ROOT / args.out_dir / args.run_name,
                provider=args.provider,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                max_rounds=args.max_rounds,
                run_name=args.run_name,
                vision=args.vision,
                normalize=True,
            )
            # react_generate with normalize=True already calls _harvest_norm on pass
            ok = result.get("iou_pass", False)
            norm_iou = result.get("norm_iou") or result.get("iou", 0)
        else:
            # Code-rewrite: rewrite existing verified cq.py
            cq_path = str(REPO_ROOT / row["cq_code_path"])
            if not Path(cq_path).exists():
                print(f"  skip: cq_code missing")
                print()
                continue
            result = react_generate_norm(
                stem=stem,
                cq_path=cq_path,
                gt_step_path=gt_step,
                gt_norm_step_path=gt_norm_step,
                run_name=args.run_name,
                provider=args.provider,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                max_rounds=args.max_rounds,
                vision=args.vision,
                keep_failed=getattr(args, "keep_failed", False),
            )
            ok = result.get("ok", False)
            norm_iou = result.get("norm_iou", 0)

        if ok:
            passed += 1
            print(f"  → PASS norm_iou={norm_iou:.4f}  [pass {passed}]")
        else:
            print(f"  → FAIL norm_iou={norm_iou:.4f}  {result.get('error','')[:80]}")
        print()

    print(f"Done: {passed}/{total} normalized")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retry-reason", nargs="+",
                    default=["exec_error"],
                    help="Filter parts.csv by retry_reason values (default: exec_error only)")
    ap.add_argument("--status", nargs="+", default=None,
                    help="Filter parts.csv by status values (e.g. failed near_miss)")
    ap.add_argument("--provider", default="codex",
                    choices=["codex", "openai"])
    ap.add_argument("--model", default="gpt-5.3-codex")
    ap.add_argument("--reasoning-effort", default="low")
    ap.add_argument("--max-rounds", type=int, default=3,
                    help="Max ReAct rounds per stem")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--run-name", default="react_v1")
    ap.add_argument("--out-dir", default="data/data_generation/codex_validation")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--stems", nargs="+", help="Explicit stems to retry")
    ap.add_argument("--vision", action="store_true",
                    help="Include GT+gen iso renders as images in IoU fix rounds (openai only)")
    ap.add_argument("--regen-verified-missing", action="store_true",
                    help="Regen CQ code for verified stems whose cq_code_path is missing from disk")
    ap.add_argument("--normalize", action="store_true",
                    help="T8b mode: rewrite verified CQ code into normalized space via LLM")
    ap.add_argument("--norm-low-iou-only", action="store_true",
                    help="With --normalize: only process stems with missing or low norm_iou (<0.95)")
    ap.add_argument("--normalize-gen", action="store_true",
                    help="Generate directly in normalized space from JSON (for new stems, T6+norm)")
    ap.add_argument("--keep-failed", action="store_true",
                    help="Keep cq_norm.py on disk even when norm_iou fails (for debugging)")
    ap.add_argument("--norm-gen", action="store_true",
                    help="With --normalize: use JSON-based generation instead of code-rewrite (F360 stems only)")
    args = ap.parse_args()

    if args.regen_verified_missing:
        _run_regen_verified_missing(args)
        return

    if args.normalize:
        _run_normalize_mode(args)
        return

    import pandas as pd, re
    from collections import defaultdict

    out_dir = REPO_ROOT / args.out_dir / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "checkpoint.jsonl"
    done_stems = _load_checkpoint(checkpoint_path) if args.resume else set()

    # Build target stems
    if args.stems:
        target_stems = set(args.stems)
    elif args.status:
        parts = pd.read_csv(db.PARTS_CSV)
        mask = parts["status"].isin(args.status)
        target_parts = parts[mask]
        if args.offset:
            target_parts = target_parts.iloc[args.offset:]
        if args.limit:
            target_parts = target_parts.iloc[: args.limit]
        target_stems = set(target_parts["stem"].tolist())
    else:
        parts = pd.read_csv(db.PARTS_CSV)
        mask = parts["retry_reason"].isin(args.retry_reason)
        target_parts = parts[mask]
        if args.offset:
            target_parts = target_parts.iloc[args.offset:]
        if args.limit:
            target_parts = target_parts.iloc[: args.limit]
        target_stems = set(target_parts["stem"].tolist())

    print(f"Target stems: {len(target_stems)}  provider={args.provider}  "
          f"model={args.model}  max_rounds={args.max_rounds}  run={args.run_name}")

    # Build index (all valid stems → records)
    all_records = _build_index(JSON_DIR, GT_STEP_DIR, limit=0, offset=0)
    stem_to_rec = {r.base_stem: r for r in all_records}

    vp = pd.read_csv(db.VERIFIED_CSV)
    genuine_stems = set(vp[~vp["note"].str.contains("copy_gt", na=False)]["stem"].tolist())

    targets = [s for s in sorted(target_stems)
               if s not in done_stems and s not in genuine_stems and s in stem_to_rec]
    print(f"After dedup/filter: {len(targets)} stems to process\n")

    passed = 0
    for i, stem in enumerate(targets, 1):
        rec = stem_to_rec[stem]
        print(f"[{i}/{len(targets)}] {stem}")

        use_norm_gen = getattr(args, "normalize_gen", False)
        result = react_generate(
            rec=rec,
            out_dir=out_dir,
            provider=args.provider,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            max_rounds=args.max_rounds,
            run_name=args.run_name,
            vision=args.vision,
            normalize=use_norm_gen,
        )
        _append_checkpoint(checkpoint_path, result)

        if result.get("iou_pass"):
            passed += 1
            source = f"{args.run_name}_{args.provider}"
            r1_fc = result.get("r1_failure_code", "")
            bad_cq = result.get("bad_cq_path", "")

            # For normalize-gen: _harvest_norm already called inside react_generate;
            # still add a verified row so stem appears in verified_parts.csv
            stem_verified_dir = STEM_FS / stem / f"verified_{args.run_name}"
            cq_fname = "cq_norm.py" if use_norm_gen else "cq.py"
            cq_rel = str((stem_verified_dir / cq_fname).relative_to(REPO_ROOT))
            gen_rel = str((stem_verified_dir / "gen.step").relative_to(REPO_ROOT))
            db.append_verified({
                "stem": stem,
                "gt_step_path": str(Path(rec.gt_step_path).relative_to(REPO_ROOT)),
                "ops_json_path": str(Path(rec.json_path).relative_to(REPO_ROOT)),
                "gen_step_path": gen_rel,
                "cq_code_path": cq_rel,
                "bad_cq_path": bad_cq,
                "iou": result["iou"],
                "verified": True,
                "views_raw_dir": "",
                "views_gen_dir": "",
                "source": source,
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "note": f"react_rounds={result['rounds']}{'_norm' if use_norm_gen else ''}",
            })
            db.update_part_status(stem, status="verified", iou=result["iou"],
                                   retry_reason="")
            if bad_cq and r1_fc:
                db.update_part_status(stem, status=None, failure_code=r1_fc)
                print(f"  → bad_code saved  r1_failure_code={r1_fc}")
            print(f"  → harvested  [pass {passed}]")
        else:
            # Update retry_reason to more specific error
            err = result.get("error", "")
            new_reason = "react_fail_exec" if "error" in err.lower() else "react_fail_iou"
            db.update_part_status(stem, status="failed",
                                   iou=result.get("iou") or None,
                                   retry_reason=new_reason,
                                   failure_code=result.get("failure_code", ""))
            fc = result.get("failure_code", "")
            if fc:
                print(f"  → failure_code={fc}")

        print()

    print(f"Done: {passed}/{len(targets)} passed")


if __name__ == "__main__":
    main()
