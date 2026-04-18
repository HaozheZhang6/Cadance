#!/usr/bin/env python
"""Build verified Fusion360 JSON -> CadQuery -> STEP training pairs.

Pipeline stages per part:
1) Build JSON <-> GT STEP index (last extrude step for each base stem)
2) Validate GT STEP geometry and render 4-view PNGs
3) Generate CadQuery code from Fusion360 JSON (LLM, with rule-based fallback)
4) Execute generated CadQuery to STEP and verify against GT STEP

Outputs:
- data/data_generation/views/<base_stem>/{front,right,top,iso}.png
- data/cadquery/<base_stem>.py
- <out-dir>/generated_step/<base_stem>.step
- <out-dir>/verified_pairs.jsonl
- data/data_generation/views/skipped.txt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
_CQ_VENV = REPO_ROOT / "tools/cadquery/.venv/bin/python"
_UV_VENV = REPO_ROOT / ".venv/bin/python"
CQ_PYTHON = _CQ_VENV if _CQ_VENV.exists() else _UV_VENV
GT_STEP_DIR = (
    REPO_ROOT
    / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools"
)
JSON_DIR = REPO_ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


STEP_SUFFIX_RE = re.compile(r"^(?P<base>.+)_(?P<idx>\d+)e$")
VALID_ENTITY_TYPES = {"Sketch", "ExtrudeFeature"}
VIEWS = ("front", "right", "top", "iso")
IOU_THRESHOLD = 0.99
SYSTEM_PROMPT = (
    "You are a CadQuery expert. Given a Fusion360 reconstruction JSON, write "
    "minimal CadQuery Python code that reproduces the geometry. Output ONLY "
    "the Python code, no explanation. The code must end with: result = "
    "<workplane_expr>; result.val().exportStep('output.step')\n\n"
    "VALID CadQuery APIs (use only these — do NOT invent methods):\n"
    "  Sketch primitives: .rect(w,h) .circle(r) .polygon(n,d) .slot2D(l,w)\n"
    "  Lines/arcs: .lineTo(x,y) .line(dx,dy) .hLineTo(x) .vLineTo(y)\n"
    "              .threePointArc((mx,my),(ex,ey)) .radiusArc((ex,ey),r) .sagittaArc((ex,ey),s)\n"
    "  Splines: .spline([(x,y),...]) — NOT makeArc/makeBsplineEdge/makeSpline\n"
    "  Solid ops: .extrude(d) .revolve(deg) .loft([wp,...]) .shell(t) .sweep(path)\n"
    "  Bool ops: .cut(wp) .union(wp) .intersect(wp) .cutThruAll() .hole(d)\n"
    "  Selectors: .faces(sel) .edges(sel) .vertices(sel) .wires(sel)\n"
    "  Modify: .fillet(r) .chamfer(d) .workplane() .transformed(offset,rotate)\n"
    "  Arrays: .polarArray(r,start,deg,n) .rarray(xs,ys,nx,ny,center)\n"
    "  Wire: .close() .wire() .consolidateWires()\n"
    "  Planes: 'XY','XZ','YZ' or cq.Plane(origin,xDir,normal)\n"
    "WRONG (do not use): cq.Edge.makeArc, cq.Edge.makeBsplineEdge,\n"
    "  cq.Edge.makeSpline, .workplane(Plane(...)) with Plane object as arg\n"
    "  (use .transformed() or pass plane string instead)\n\n"
    "DIVERSE OP EXAMPLES — use these patterns when the geometry calls for it:\n"
    "# Revolve ring: profile around Y axis\n"
    "result = (cq.Workplane('XZ').moveTo(20,0).lineTo(35,0).lineTo(35,10)"
    ".lineTo(20,10).close().revolve(360,(0,0,0),(0,1,0)))\n"
    "# Extrude + post-extrude fillet on vertical edges\n"
    "result = cq.Workplane('XY').rect(40,30).extrude(20).edges('|Z').fillet(5)\n"
    "# Extrude + chamfer on top face edges\n"
    "result = cq.Workplane('XY').rect(40,30).extrude(20).edges('>Z').chamfer(3)\n"
    "# Shell: hollow box (negative t = inward)\n"
    "result = cq.Workplane('XY').rect(50,40).extrude(30).faces('>Z').shell(-4)\n"
    "# Polar array of holes\n"
    "result = (cq.Workplane('XY').circle(30).extrude(8)"
    ".faces('>Z').workplane().polarArray(18,0,360,6).hole(4))\n"
    "# Loft: circle (bottom) to rectangle (top)\n"
    "result = cq.Workplane('XY').circle(15).workplane(offset=25).rect(40,30).loft()\n"
    "# Loft: two circles (frustum)\n"
    "result = cq.Workplane('XY').circle(20).workplane(offset=30).circle(10).loft()"
)


@dataclass(frozen=True)
class PartIndexRecord:
    """Resolved JSON + GT STEP pair for a Fusion360 part."""

    base_stem: str
    stem: str
    json_path: Path
    gt_step_path: Path


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _append_skipped(
    skipped_path: Path, base_stem: str, stage: str, reason: str
) -> None:
    skipped_path.parent.mkdir(parents=True, exist_ok=True)
    with skipped_path.open("a", encoding="utf-8") as f:
        f.write(f"{base_stem}\t{stage}\t{reason}\n")


def _safe_json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_api_keys() -> list[str]:
    """Return available OpenAI API keys (primary then backup)."""
    keys = []
    for var in ("OPENAI_API_KEY", "OPENAI_API_KEY1"):
        k = os.environ.get(var, "").strip()
        if k:
            keys.append(k)
    return keys


def _classify_error_type(err: str) -> str:
    """Classify error string into a category for stats/resume logic."""
    e = (err or "").lower()
    if "oauth" in e or "device auth" in e or "chatgpt" in e:
        return "oauth_error"
    if "exit=1" in e and ("codex" in e or "auth" in e):
        return "codex_auth_error"
    if "rate limit" in e or "rate_limit" in e or ("429" in e and "\u4f59\u989d" not in e):
        return "rate_limit"
    if "\u4f59\u989d\u4e0d\u8db3" in e or "insufficient balance" in e or "no_balance" in e:
        return "no_balance"
    if "model" in e and ("not found" in e or "does not exist" in e or "not supported" in e):
        return "model_not_found"
    if "timeout" in e or "timed out" in e:
        return "timeout"
    if "api key" in e or "no api key" in e or "api_key" in e:
        return "no_api_key"
    return "other"


def _build_index(
    json_dir: Path,
    step_dir: Path,
    limit: int,
    offset: int = 0,
) -> list[PartIndexRecord]:
    step_map: dict[str, list[Path]] = {}
    step_files = sorted(list(step_dir.glob("*.step")) + list(step_dir.glob("*.STEP")))
    for step_path in step_files:
        match = STEP_SUFFIX_RE.match(step_path.stem)
        if not match:
            continue
        base_stem = match.group("base")
        step_map.setdefault(base_stem, []).append(step_path)

    all_records: list[PartIndexRecord] = []
    for json_path in sorted(json_dir.glob("*.json")):
        base_stem = json_path.stem
        candidates = step_map.get(base_stem)
        if not candidates:
            continue
        last_step = sorted(candidates, key=lambda p: p.stem)[-1]
        all_records.append(
            PartIndexRecord(
                base_stem=base_stem,
                stem=last_step.stem,
                json_path=json_path,
                gt_step_path=last_step,
            )
        )

    sliced = all_records[offset:] if offset > 0 else all_records
    if limit > 0:
        sliced = sliced[:limit]
    return sliced


_EXTRUDE_DROP = frozenset(
    {
        "faces",
        "bodies",
        "extrude_bodies",
        "extrude_faces",
        "extrude_side_faces",
        "extrude_end_faces",
        "extrude_start_faces",
    }
)


def _trim_sketch(ent: dict[str, Any]) -> dict[str, Any]:
    """Keep structural profile data only; drop raw points/curves/constraints."""
    out: dict[str, Any] = {
        "name": ent.get("name"),
        "type": ent.get("type"),
        "transform": ent.get("transform"),
    }
    ref = ent.get("reference_plane")
    if ref:
        out["reference_plane"] = {
            k: v for k, v in ref.items() if k != "corrective_transform"
        }
    profiles = ent.get("profiles", {})
    trimmed: dict[str, Any] = {}
    for pid, profile in (profiles.items() if isinstance(profiles, dict) else []):
        loops = []
        for loop in profile.get("loops", []):
            curves = [
                {k: v for k, v in pc.items() if k != "curve"}
                for pc in loop.get("profile_curves", [])
            ]
            loops.append({"is_outer": loop.get("is_outer"), "profile_curves": curves})
        trimmed[pid] = {"loops": loops}
    out["profiles"] = trimmed
    return out


def _trim_extrude(ent: dict[str, Any]) -> dict[str, Any]:
    """Keep operation/extent/profile refs; drop face and body arrays."""
    out = {k: v for k, v in ent.items() if k not in _EXTRUDE_DROP}
    ext = ent.get("extent_one")
    if ext and isinstance(ext, dict):
        dist = ext.get("distance", {})
        out["extent_one"] = {
            "type": ext.get("type"),
            "distance": {"value": dist.get("value")},
        }
    start = ent.get("start_extent")
    if start and isinstance(start, dict):
        out["start_extent"] = {"type": start.get("type")}
    return out


def _trim_json_for_prompt(data: dict[str, Any]) -> dict[str, Any]:
    timeline = data.get("timeline")
    if timeline is None:
        timeline = data.get("sequence", [])
    entities: dict[str, Any] = {}
    for ent_id, ent in data.get("entities", {}).items():
        if not isinstance(ent, dict):
            continue
        t = ent.get("type")
        if t == "Sketch":
            entities[ent_id] = _trim_sketch(ent)
        elif t == "ExtrudeFeature":
            entities[ent_id] = _trim_extrude(ent)
    return {"timeline": timeline, "entities": entities}


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _ensure_export_line(code: str) -> str:
    required = "result.val().exportStep('output.step')"
    stripped = code.rstrip()
    if not stripped.endswith(required):
        stripped = f"{stripped}\n{required}"
    return stripped + "\n"


def _load_rule_based_codegen() -> tuple[Any | None, str | None]:
    try:
        from scripts.data_generation import fusion360_pipeline as f360
    except Exception as exc:  # noqa: BLE001
        return None, f"cannot import fusion360_pipeline: {exc}"

    if hasattr(f360, "generate_cadquery_code"):
        return f360.generate_cadquery_code, None

    if hasattr(f360, "_convert_fusion_json") and hasattr(f360, "_generate_cadquery"):
        convert_fn = f360._convert_fusion_json
        generate_fn = f360._generate_cadquery

        def _fallback(json_path: Path, _json_data: dict[str, Any]) -> str:
            program, reason = convert_fn(json_path)
            if program is None:
                raise RuntimeError(reason or "rule-based conversion failed")
            code = generate_fn(program)
            if not code:
                raise RuntimeError("rule-based code generation returned empty code")
            return str(code)

        return _fallback, None

    return None, "fusion360_pipeline has no usable codegen function"


CODEX_BIN = REPO_ROOT / "node_modules/.bin/codex"
_CODEX_BIN_FALLBACK = Path("/workspace/.local/node_modules/.bin/codex")


def _codex_bin() -> Path | None:
    for candidate in (CODEX_BIN, _CODEX_BIN_FALLBACK):
        if candidate.exists():
            return candidate
    return None


def _generate_code_codex(
    json_data: dict[str, Any],
    model: str = "gpt-5.3-codex",
    reasoning_effort: str = "low",
    timeout_sec: int = 120,
    prompt: str | None = None,
) -> tuple[str | None, str | None]:
    """Generate CadQuery code via the Codex CLI (ChatGPT auth, no API key needed).

    Trims JSON to Sketch/ExtrudeFeature entities only and inlines it directly
    in the prompt so codex writes output.py in a single pass without file I/O steps.
    If prompt is provided directly, use it instead of building from json_data.
    """
    codex = _codex_bin()
    if codex is None:
        return None, "codex CLI not found"

    if prompt is None:
        trimmed = _trim_json_for_prompt(json_data)
        trimmed_json_str = json.dumps(trimmed, ensure_ascii=True)
        prompt = (
            "Write output.py containing CadQuery Python code that reproduces this "
            "Fusion360 geometry.\n"
            f"JSON (Sketch+ExtrudeFeature entities only, coordinates in cm):\n"
            f"{trimmed_json_str}\n\n"
            "Rules:\n"
            "- Multiply ALL coordinate/dimension values by 10 (cm → mm)\n"
            "- Only: import cadquery as cq\n"
            "- Final workplane in variable 'result'\n"
            "- Last line: result.val().exportStep('output.step')\n"
            "- Write ONLY the Python code to output.py, nothing else"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        env = dict(os.environ)
        # Pass prompt via stdin ("-") to avoid OS arg-length limits on large JSONs
        cmd = [
            str(codex),
            "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "-m",
            model,
            "-c",
            f"model_reasoning_effort={reasoning_effort!r}",
            "-C",
            str(tmp),
            "-",  # read prompt from stdin
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return None, f"codex timed out after {timeout_sec}s"
        except Exception as exc:  # noqa: BLE001
            return None, f"codex failed to start: {exc}"

        if proc.returncode != 0:
            return None, f"codex exit={proc.returncode}: {proc.stderr.strip()[:300]}"

        out_py = tmp / "output.py"
        if not out_py.exists():
            return None, "codex ran but output.py not created"

        code = out_py.read_text(encoding="utf-8").strip()
        if not code:
            return None, "codex produced empty output.py"

        return _ensure_export_line(code), None


def _generate_code_llm(json_data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Generate code via Codex CLI first, fall back to OpenAI API."""
    code, err = _generate_code_codex(json_data)
    if code:
        return code, None

    # Fallback: direct OpenAI API
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        return None, f"codex failed ({err}); openai import failed: {exc}"

    client = OpenAI()
    trimmed = _trim_json_for_prompt(json_data)
    user_prompt = (
        "Fusion360 reconstruction JSON (trimmed to timeline + Sketch/"
        f"ExtrudeFeature entities):\n{json.dumps(trimmed, ensure_ascii=True)}"
    )

    try:
        response = client.chat.completions.create(
            model="o3",
            reasoning_effort="high",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return None, "LLM returned empty content"
        code = _strip_markdown_fences(content)
        if not code.strip():
            return None, "LLM returned blank code after cleanup"
        return _ensure_export_line(code), None
    except Exception as exc:  # noqa: BLE001
        return None, f"codex failed ({err}); LLM request failed: {exc}"


def _generate_code_openai_with_retry(
    json_data: dict[str, Any],
    model: str = "o3",
    reasoning_effort: str = "high",
    timeout_sec: int = 300,
    max_retries: int = 1,
    user_prompt: str | None = None,
    system_prompt: str | None = None,
    multimodal: bool = False,
) -> tuple[str | None, str | None]:
    """Generate CadQuery code via OpenAI API with key rotation.

    If user_prompt/system_prompt are provided, use them instead of building from json_data.
    If multimodal=True, user_prompt is a JSON-encoded list of content blocks (text + image_url).
    """
    keys = _get_api_keys()
    if not keys:
        return None, "no_api_key: OPENAI_API_KEY not set"

    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        return None, f"openai import failed: {exc}"

    if user_prompt is None:
        trimmed = _trim_json_for_prompt(json_data)
        user_prompt = (
            "Fusion360 reconstruction JSON (coords in cm):\n"
            f"{json.dumps(trimmed, ensure_ascii=True)}\n\n"
            "Rules:\n"
            "- Multiply ALL coordinate/dimension values by 10 (cm → mm)\n"
            "- Only: import cadquery as cq\n"
            "- Hard-code ALL values directly — do NOT read from any file\n"
            "- Final workplane in variable 'result'\n"
            "- Last line: result.val().exportStep('output.step')\n"
            "- Output ONLY the Python code, no explanation"
        )
    sys_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT

    # Decode multimodal content blocks if needed
    user_content: Any = json.loads(user_prompt) if multimodal else user_prompt

    last_err: str | None = None
    for api_key in keys[:max(1, max_retries)]:
        try:
            client = OpenAI(api_key=api_key)
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_content},
                ],
                "timeout": timeout_sec,
            }
            if model.startswith("o") or "codex" in model:
                kwargs["reasoning_effort"] = reasoning_effort
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content:
                last_err = "LLM returned empty content"
                continue
            code = _strip_markdown_fences(content)
            if not code.strip():
                last_err = "LLM returned blank code after cleanup"
                continue
            # Reject code that reads from files (model misunderstood the task)
            if 'open(' in code and ('"input' in code or '"model' in code or '.json"' in code):
                last_err = "model generated file-reading code (not inline)"
                continue
            return _ensure_export_line(code), None
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)

    return None, last_err


def _generate_code_claude(
    json_data: dict[str, Any],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8096,
    timeout_sec: int = 120,
) -> tuple[str | None, str | None]:
    """Generate CadQuery code via Anthropic Claude API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None, "no ANTHROPIC_API_KEY"

    try:
        import anthropic
    except ImportError:
        return None, "anthropic package not installed; run: uv add anthropic"

    trimmed = _trim_json_for_prompt(json_data)
    user_prompt = (
        "Fusion360 reconstruction JSON (coords in cm):\n"
        f"{json.dumps(trimmed, ensure_ascii=True)}\n\n"
        "Rules:\n"
        "- Multiply ALL coordinate/dimension values by 10 (cm → mm)\n"
        "- Only: import cadquery as cq\n"
        "- Final workplane in variable 'result'\n"
        "- Last line: result.val().exportStep('output.step')\n"
        "- Output ONLY the Python code, no explanation"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=timeout_sec,
        )
        content = response.content[0].text if response.content else None
        if not content:
            return None, "Claude returned empty content"
        code = _strip_markdown_fences(content)
        if not code.strip():
            return None, "Claude returned blank code after cleanup"
        return _ensure_export_line(code), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Claude API error: {exc}"


_GLM_MAX_PROMPT_CHARS = 30_000  # truncate JSON prompt to avoid multi-minute hangs


def _generate_code_glm(
    json_data: dict[str, Any],
    model: str = "glm-4.7",
    timeout_sec: int = 120,
    user_prompt: str | None = None,
    system_prompt: str | None = None,
) -> tuple[str | None, str | None]:
    """Generate CadQuery code via Zhipu AI GLM API (OpenAI-compatible).

    If user_prompt/system_prompt are provided, use them instead of building from json_data.
    """
    api_key = os.environ.get("ZHIPU_API_KEY", "").strip()
    if not api_key:
        return None, "no_api_key: ZHIPU_API_KEY not set"

    try:
        import httpx
        from openai import OpenAI
    except ImportError:
        return None, "openai/httpx package not installed"

    if user_prompt is None:
        trimmed = _trim_json_for_prompt(json_data)
        json_str = json.dumps(trimmed, ensure_ascii=True)
        if len(json_str) > _GLM_MAX_PROMPT_CHARS:
            json_str = json_str[:_GLM_MAX_PROMPT_CHARS] + "... (truncated)"
        user_prompt = (
            "Fusion360 reconstruction JSON (coords in cm):\n"
            f"{json_str}\n\n"
            "Rules:\n"
            "- Multiply ALL coordinate/dimension values by 10 (cm → mm)\n"
            "- Only: import cadquery as cq\n"
            "- Final workplane in variable 'result'\n"
            "- Last line: result.val().exportStep('output.step')\n"
            "- Output ONLY the Python code, no explanation"
        )
    sys_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return None, "GLM returned empty content"
        code = _strip_markdown_fences(content)
        if not code.strip():
            return None, "GLM returned blank code after cleanup"
        return _ensure_export_line(code), None
    except Exception as exc:  # noqa: BLE001
        return None, f"GLM API error: {exc}"


def _refine_code_with_claude_feedback(
    json_data: dict[str, Any],
    initial_code: str,
    gt_step_path: Path,
    gen_step_path: Path,
    initial_iou: float,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8096,
    timeout_sec: int = 120,
    max_rounds: int = 5,
    iou_threshold: float = IOU_THRESHOLD,
) -> tuple[str | None, float, int]:
    """Iteratively refine CadQuery code using Claude + geometry feedback.

    Returns (best_code, best_iou, rounds_used).
    best_code is None if all rounds fail to execute.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None, initial_iou, 0

    try:
        import anthropic
    except ImportError:
        return None, initial_iou, 0

    trimmed = _trim_json_for_prompt(json_data)
    json_str = json.dumps(trimmed, separators=(",", ":"), ensure_ascii=True)

    best_code = initial_code
    best_iou = initial_iou

    def _step_info(path: Path) -> str:
        try:
            import cadquery as cq

            shape = cq.importers.importStep(str(path)).val()
            bb = shape.BoundingBox()
            vol = float(shape.Volume())
            return (
                f"volume={vol:.2f}mm³  "
                f"bbox=({bb.xlen:.2f}×{bb.ylen:.2f}×{bb.zlen:.2f})mm"
            )
        except Exception as exc:  # noqa: BLE001
            return f"(could not load: {exc})"

    # Multi-turn conversation: system + initial attempt + feedback rounds
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Fusion360 JSON (Sketch+Extrude only, coords in cm):\n{json_str}\n\n"
                "Rules: ×10 cm→mm | only `import cadquery as cq` | "
                "no file I/O — hardcode all values | "
                "final shape in `result` | last line: result.val().exportStep('output.step')\n\n"
                "Write the CadQuery code:"
            ),
        },
        {"role": "assistant", "content": initial_code},
    ]

    client = anthropic.Anthropic(api_key=api_key)

    for round_idx in range(1, max_rounds + 1):
        gt_info = _step_info(gt_step_path)
        gen_info = (
            _step_info(gen_step_path) if gen_step_path.exists() else "not generated"
        )

        messages.append(
            {
                "role": "user",
                "content": (
                    f"That code is wrong (IoU={best_iou:.4f}, need ≥{iou_threshold}).\n\n"
                    f"Ground truth: {gt_info}\n"
                    f"Your output:  {gen_info}\n\n"
                    "Analyse the geometry mismatch and output corrected Python code only."
                ),
            }
        )

        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
                timeout=timeout_sec,
            )
            content = resp.content[0].text if resp.content else None
            if not content:
                messages.append({"role": "assistant", "content": ""})
                continue

            code = _ensure_export_line(_strip_markdown_fences(content))

            with tempfile.TemporaryDirectory() as tmp:
                new_step = Path(tmp) / "test.step"
                ran, exec_err = _execute_cadquery_script(code, new_step, timeout_sec=60)
                if not ran:
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Execution error:\n{exec_err or 'execute failed'}\n\n"
                                "Fix it. Output only corrected Python."
                            ),
                        }
                    )
                    continue

                new_iou, _iou_err = _compute_iou(gt_step_path, new_step)
                messages.append({"role": "assistant", "content": code})

                if new_iou > best_iou:
                    best_code = code
                    best_iou = new_iou
                    import shutil

                    gen_step_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(new_step), str(gen_step_path))

                if new_iou >= iou_threshold:
                    return best_code, best_iou, round_idx

        except Exception as exc:  # noqa: BLE001
            messages.append({"role": "assistant", "content": str(exc)})

    return (best_code if best_iou > initial_iou else None), best_iou, max_rounds


def _refine_code_with_feedback(
    json_data: dict[str, Any],
    initial_code: str,
    gt_step_path: Path,
    gen_step_path: Path,
    initial_iou: float,
    model: str = "o3",
    reasoning_effort: str = "high",
    timeout_sec: int = 300,
    max_rounds: int = 5,
    iou_threshold: float = IOU_THRESHOLD,
) -> tuple[str | None, float, int]:
    """Iteratively refine CadQuery code using geometry feedback until IoU >= threshold.

    Each round feeds the model:
      - Original Fusion360 JSON (trimmed)
      - Current failed code
      - GT vs Gen volume/bbox diff
      - IoU score
      - Instruction to fix

    Returns (best_code, best_iou, rounds_used).
    best_code is None if all rounds fail to execute.
    """
    keys = _get_api_keys()
    if not keys:
        return None, initial_iou, 0

    try:
        from openai import OpenAI
    except ImportError:
        return None, initial_iou, 0

    trimmed = _trim_json_for_prompt(json_data)
    json_str = json.dumps(trimmed, separators=(",", ":"), ensure_ascii=True)

    best_code = initial_code
    best_iou = initial_iou

    def _step_info(path: Path) -> str:
        try:
            import cadquery as cq

            shape = cq.importers.importStep(str(path)).val()
            bb = shape.BoundingBox()
            vol = float(shape.Volume())
            return (
                f"volume={vol:.2f}mm³  "
                f"bbox=({bb.xlen:.2f}×{bb.ylen:.2f}×{bb.zlen:.2f})mm"
            )
        except Exception as exc:  # noqa: BLE001
            return f"(could not load: {exc})"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Fusion360 JSON (Sketch+Extrude only, coords in cm):\n{json_str}\n\n"
                "Rules: ×10 cm→mm | only `import cadquery as cq` | "
                "no file I/O — hardcode all values | "
                "final shape in `result` | last line: result.val().exportStep('output.step')"
            ),
        },
        {"role": "assistant", "content": initial_code},
    ]

    client = OpenAI(api_key=keys[0])

    for round_idx in range(1, max_rounds + 1):
        gt_info = _step_info(gt_step_path)
        gen_info = (
            _step_info(gen_step_path) if gen_step_path.exists() else "not generated"
        )

        messages.append(
            {
                "role": "user",
                "content": (
                    f"That code is wrong (IoU={best_iou:.4f}, threshold={iou_threshold}).\n\n"
                    f"Ground truth: {gt_info}\n"
                    f"Your output:  {gen_info}\n\n"
                    "Analyse the geometry mismatch and output corrected Python code only."
                ),
            }
        )

        try:
            kwargs: dict[str, Any] = {"model": model, "messages": messages}
            if model.startswith("o") or "codex" in model:
                kwargs["reasoning_effort"] = reasoning_effort
            resp = client.chat.completions.create(**kwargs, timeout=timeout_sec)
            content = resp.choices[0].message.content
            if not content:
                messages.append({"role": "assistant", "content": ""})
                continue
            code = _ensure_export_line(_strip_markdown_fences(content))

            with tempfile.TemporaryDirectory() as tmp:
                new_step = Path(tmp) / "test.step"
                ran, exec_err = _execute_cadquery_script(code, new_step, timeout_sec=60)
                if not ran:
                    # feed error back
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Execution error:\n{exec_err or 'execute failed'}\n\n"
                                "Fix it. Output only corrected Python."
                            ),
                        }
                    )
                    continue

                new_iou, _iou_err = _compute_iou(gt_step_path, new_step)
                messages.append({"role": "assistant", "content": code})

                if new_iou > best_iou:
                    best_code = code
                    best_iou = new_iou
                    import shutil

                    gen_step_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(new_step), str(gen_step_path))

                if new_iou >= iou_threshold:
                    return best_code, best_iou, round_idx

        except Exception as exc:  # noqa: BLE001
            messages.append({"role": "assistant", "content": str(exc)})

    return (best_code if best_iou > initial_iou else None), best_iou, max_rounds


def _generate_code_rule_based(
    json_path: Path,
    json_data: dict[str, Any],
    fallback_fn: Any | None,
) -> tuple[str | None, str | None]:
    if fallback_fn is None:
        return None, "rule-based fallback unavailable"
    try:
        code = fallback_fn(json_path, json_data)
    except TypeError:
        # If generate_cadquery_code exists with a different signature, retry.
        try:
            code = fallback_fn(json_data)
        except Exception as exc:  # noqa: BLE001
            return None, f"rule-based fallback failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        return None, f"rule-based fallback failed: {exc}"

    code_text = str(code).strip()
    if not code_text:
        return None, "rule-based fallback returned empty code"
    return _ensure_export_line(code_text), None


def _classify_complexity(json_data: dict[str, Any]) -> str:
    entities = json_data.get("entities", {})
    sketch_count = 0
    curve_types: set[str] = set()

    for ent in entities.values():
        if not isinstance(ent, dict) or ent.get("type") != "Sketch":
            continue
        sketch_count += 1
        profiles = ent.get("profiles", {})
        if not isinstance(profiles, dict):
            continue
        for profile in profiles.values():
            loops = profile.get("loops", [])
            for loop in loops:
                for curve in loop.get("profile_curves", []):
                    ctype = curve.get("type")
                    if isinstance(ctype, str):
                        curve_types.add(ctype)

    if not curve_types:
        return "box"
    if sketch_count > 1:
        return "complex"
    if curve_types == {"Circle3D"}:
        return "cylinder"
    return "complex"


def _step_metrics(
    step_path: Path,
) -> tuple[float, tuple[float, float, float], str | None]:
    try:
        import cadquery as cq

        shape = cq.importers.importStep(str(step_path)).val()
        bb = shape.BoundingBox()
        volume = float(shape.Volume())
        dims = (float(bb.xlen), float(bb.ylen), float(bb.zlen))
        return volume, dims, None
    except Exception as exc:  # noqa: BLE001
        return 0.0, (0.0, 0.0, 0.0), str(exc)


def _is_step_valid(step_path: Path) -> tuple[bool, str | None]:
    _, dims, err = _step_metrics(step_path)
    if err:
        return False, err
    if not (dims[0] > 0 and dims[1] > 0 and dims[2] > 0):
        return False, f"non-positive bbox dims: {dims}"
    return True, None


def _parse_svg_dim(raw_value: str | None, fallback: float = 1.0) -> float:
    if raw_value is None:
        return fallback
    text = raw_value.strip()
    if text.endswith("px"):
        text = text[:-2]
    try:
        value = float(text)
        return value if value > 0 else fallback
    except Exception:  # noqa: BLE001
        return fallback


def _svg_dims(svg_path: Path) -> tuple[float, float]:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    width = _parse_svg_dim(root.get("width"))
    height = _parse_svg_dim(root.get("height"))
    return width, height


def _svg_to_png(svg_path: Path, png_path: Path, max_px: int) -> None:
    """Rasterise an orthographic SVG to PNG using matplotlib (no cairo needed).

    The orthographic renderer emits only <polyline>, <line>, and <text> elements
    in pixel coordinates, which matplotlib handles without any C system libraries.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tree = ET.parse(svg_path)
    root = tree.getroot()
    strip_ns = lambda tag: tag.split("}")[-1]  # noqa: E731

    svg_w = float(root.get("width", 600))
    svg_h = float(root.get("height", 600))
    scale = max_px / max(svg_w, svg_h)

    fig, ax = plt.subplots(
        figsize=(svg_w * scale / 100, svg_h * scale / 100), facecolor="white"
    )
    ax.set_xlim(0, svg_w)
    ax.set_ylim(svg_h, 0)  # SVG y-axis points down
    ax.set_aspect("equal")
    ax.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    for el in root.iter():
        tag = strip_ns(el.tag)
        stroke = el.get("stroke", "black")
        lw = float(el.get("stroke-width", "1")) * scale
        if tag == "polyline":
            pts = [
                tuple(float(v) for v in p.split(","))
                for p in el.get("points", "").strip().split()
                if "," in p
            ]
            if pts:
                xs, ys = zip(*pts, strict=False)
                ax.plot(
                    xs,
                    ys,
                    color=stroke,
                    lw=lw,
                    solid_capstyle="round",
                    solid_joinstyle="round",
                )
        elif tag == "line":
            ax.plot(
                [float(el.get("x1", 0)), float(el.get("x2", 0))],
                [float(el.get("y1", 0)), float(el.get("y2", 0))],
                color=stroke,
                lw=lw,
            )
        elif tag == "text":
            txt = (el.text or "").strip()
            if txt:
                ax.text(
                    float(el.get("x", 0)),
                    float(el.get("y", 0)),
                    txt,
                    fontsize=float(el.get("font-size", 12)) * scale * 0.75,
                    color="#333333",
                    va="top",
                )

    fig.savefig(str(png_path), format="png", dpi=100, pad_inches=0)
    plt.close(fig)


def _render_views(
    step_path: Path, views_dir: Path, max_px: int
) -> tuple[bool, str | None]:
    try:
        from cad_drawing.orthographic import (
            OrthographicConfig,
            render_orthographic_from_step,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"cad_drawing unavailable: {exc}"

    views_dir.mkdir(parents=True, exist_ok=True)
    config = OrthographicConfig()

    try:
        svg_paths = render_orthographic_from_step(step_path, views_dir, config)
    except Exception as exc:  # noqa: BLE001
        return False, f"render failed: {exc}"

    svg_by_view: dict[str, Path] = {}
    for svg_path in svg_paths:
        for view in VIEWS:
            if svg_path.stem.endswith(f"_{view}"):
                svg_by_view[view] = svg_path
                break

    missing = [view for view in VIEWS if view not in svg_by_view]
    if missing:
        return False, f"missing rendered views: {missing}"

    try:
        for view in VIEWS:
            svg_path = svg_by_view[view]
            png_path = views_dir / f"{view}.png"
            _svg_to_png(svg_path, png_path, max_px=max_px)
            svg_path.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        return False, f"svg->png conversion failed: {exc}"

    return True, None


_OCP_HASHCODE_FIX = """\
# OCP 7.9.x hashcode compatibility fix
try:
    import OCC.Core.Standard as _occ_std
    if not hasattr(_occ_std.Standard_Transient, '__hash__'):
        _occ_std.Standard_Transient.__hash__ = lambda self: id(self)
except Exception:
    pass
try:
    from cadquery.occ_impl.shapes import Shape as _CqShape
    if not getattr(_CqShape, '_hashcode_patched', False):
        _orig_hc = _CqShape.hashCode
        def _safe_hashcode(self):
            try:
                return _orig_hc(self)
            except (AttributeError, TypeError):
                return id(self.wrapped)
        _CqShape.hashCode = _safe_hashcode
        _CqShape._hashcode_patched = True
except Exception:
    pass
"""


def _patch_output_step_path(code: str, output_step_path: Path) -> str:
    patched = _OCP_HASHCODE_FIX + code
    patched = patched.replace("'output.step'", repr(str(output_step_path)))
    patched = patched.replace('"output.step"', repr(str(output_step_path)))
    if "exportStep(" not in patched:
        patched = (
            patched.rstrip()
            + f"\n\nresult.val().exportStep({repr(str(output_step_path))})\n"
        )
    return patched


def _execute_cadquery_script(
    code: str,
    output_step_path: Path,
    timeout_sec: int = 30,
) -> tuple[bool, str | None]:
    output_step_path.parent.mkdir(parents=True, exist_ok=True)
    patched_code = _patch_output_step_path(code, output_step_path)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        tmp_file.write(patched_code)
        tmp_path = Path(tmp_file.name)

    env = dict(os.environ)
    env["OUTPUT_STEP"] = str(output_step_path)
    env["PYTHONPATH"] = f"{SRC_ROOT}:{env.get('PYTHONPATH', '')}"

    try:
        proc = subprocess.run(
            [str(CQ_PYTHON), str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        tmp_path.unlink(missing_ok=True)
        return False, f"execution timed out after {timeout_sec}s"
    except Exception as exc:  # noqa: BLE001
        tmp_path.unlink(missing_ok=True)
        return False, f"execution failed to start: {exc}"
    finally:
        tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        return False, f"returncode={proc.returncode}, stderr={stderr}, stdout={stdout}"

    if not output_step_path.exists():
        return False, "generated STEP file missing after execution"
    return True, None


def _within_rel_tol(value: float, target: float, tol: float) -> bool:
    if abs(target) < 1e-12:
        return abs(value) < 1e-12
    return abs(value - target) / abs(target) <= tol


def _compute_iou(
    gt_step_path: Path,
    gen_step_path: Path,
) -> tuple[float, str | None]:
    """Compute 3D IoU = Volume(GT ∩ Gen) / Volume(GT ∪ Gen) via OCCT booleans.

    Uses cadquery Shape.intersect() and arithmetic union formula to avoid the
    cost of an explicit fuse operation.
    """
    try:
        import cadquery as cq

        gt = cq.importers.importStep(str(gt_step_path)).val()
        gen = cq.importers.importStep(str(gen_step_path)).val()

        vol_gt = float(gt.Volume())
        vol_gen = float(gen.Volume())

        common = gt.intersect(gen)
        vol_common = float(common.Volume())

        # Union = A + B − A∩B  (avoids second boolean op)
        vol_union = vol_gt + vol_gen - vol_common
        if vol_union <= 0:
            return 0.0, "union volume is zero"

        iou = max(0.0, min(1.0, vol_common / vol_union))
        return iou, None
    except Exception as exc:  # noqa: BLE001
        return 0.0, str(exc)


def _parse_visual_verdict(text: str) -> tuple[str, str]:
    """Extract PASS/FAIL verdict from Codex CLI output (JSON or plain text)."""
    import re

    # Try JSON first
    json_match = re.search(r"\{[^{}]*\"verdict\"[^{}]*\}", text, re.DOTALL)
    if json_match:
        try:
            obj = json.loads(json_match.group())
            verdict = str(obj.get("verdict", "FAIL")).upper()
            reason = str(obj.get("reason", ""))
            if verdict in ("PASS", "FAIL"):
                return verdict, reason
        except Exception:  # noqa: BLE001
            pass

    # Fallback: look for PASS / FAIL keywords
    upper = text.upper()
    if "VERDICT: PASS" in upper or '"verdict": "PASS"' in text.lower():
        return "PASS", ""
    if "VERDICT: FAIL" in upper or '"verdict": "FAIL"' in text.lower():
        return "FAIL", text.strip()[:300]

    # Conservative: if no clear PASS, treat as FAIL
    return "FAIL", f"could not parse verdict from: {text.strip()[:200]}"


def _compare_views_visual(
    raw_views_dir: Path,
    gen_views_dir: Path,
    model: str = "gpt-5.3-codex",
    timeout_sec: int = 120,
) -> tuple[str, str]:
    """Compare raw vs generated STEP via Codex CLI vision.

    Copies 4-view PNGs to a temp dir, runs Codex CLI with a vision comparison
    prompt, reads verdict.json output.

    Returns (verdict, reason) where verdict ∈ {"PASS","FAIL","ERROR"}.
    """
    import shutil

    codex = _codex_bin()
    if codex is None:
        return "ERROR", "codex CLI not found"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        raw_dir = tmp / "raw"
        gen_dir = tmp / "gen"
        raw_dir.mkdir()
        gen_dir.mkdir()

        # Copy PNGs
        views_found = []
        for view in VIEWS:
            raw_png = raw_views_dir / f"{view}.png"
            gen_png = gen_views_dir / f"{view}.png"
            if raw_png.exists() and gen_png.exists():
                shutil.copy2(raw_png, raw_dir / f"{view}.png")
                shutil.copy2(gen_png, gen_dir / f"{view}.png")
                views_found.append(view)

        if len(views_found) < 4:
            missing = set(VIEWS) - set(views_found)
            return "ERROR", f"missing views: {missing}"

        prompt = (
            "Compare two CAD parts using their orthographic PNG views.\n"
            "'raw/' = ground truth STEP (4 views: front, right, top, iso).\n"
            "'gen/' = Codex-CLI generated STEP (same 4 views).\n\n"
            "Examine all 8 images and determine if the two parts are geometrically equivalent.\n"
            "Consider: overall shape, feature positions, holes, pockets, ribs, proportions.\n\n"
            "Write your result to verdict.json:\n"
            '{"verdict": "PASS", "reason": "geometrically identical", '
            '"views_checked": ["front","right","top","iso"]}\n'
            "or\n"
            '{"verdict": "FAIL", "reason": "describe visible geometric differences", '
            '"views_checked": ["front","right","top","iso"]}\n\n'
            "Write ONLY verdict.json. No other output."
        )

        cmd = [
            str(codex),
            "exec",
            "--skip-git-repo-check",
            "-m",
            model,
            "-c",
            "model_reasoning_effort=medium",
            "-s",
            "workspace-write",
            "-C",
            str(tmp),
            "-",
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
                env=dict(os.environ),
            )
        except subprocess.TimeoutExpired:
            return "ERROR", f"codex visual timed out after {timeout_sec}s"
        except Exception as exc:  # noqa: BLE001
            return "ERROR", f"codex visual failed: {exc}"

        verdict_json = tmp / "verdict.json"
        if verdict_json.exists():
            try:
                obj = json.loads(verdict_json.read_text(encoding="utf-8"))
                v = str(obj.get("verdict", "FAIL")).upper()
                r = str(obj.get("reason", ""))
                return (v if v in ("PASS", "FAIL") else "FAIL"), r
            except Exception:  # noqa: BLE001
                pass

        # Try parsing stdout/stderr
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return _parse_visual_verdict(combined)


def _process_part(
    record: PartIndexRecord,
    views_root: Path,
    cadquery_root: Path,
    gen_step_root: Path,
    skipped_path: Path,
    max_px: int,
    no_llm: bool,
    fallback_codegen_fn: Any | None,
    skip_visual: bool = False,
) -> dict[str, Any] | None:
    is_valid, reason = _is_step_valid(record.gt_step_path)
    if not is_valid:
        _append_skipped(skipped_path, record.base_stem, "step_validity", reason or "?")
        return None

    views_raw_dir = views_root / record.base_stem / "raw"
    rendered, reason = _render_views(record.gt_step_path, views_raw_dir, max_px=max_px)
    if not rendered:
        _append_skipped(skipped_path, record.base_stem, "render_raw", reason or "?")
        return None

    try:
        fusion_json = _safe_json_load(record.json_path)
    except Exception as exc:  # noqa: BLE001
        _append_skipped(skipped_path, record.base_stem, "json_load", str(exc))
        return None

    code: str | None = None
    if no_llm:
        code, reason = _generate_code_rule_based(
            record.json_path, fusion_json, fallback_codegen_fn
        )
        if not code:
            _append_skipped(
                skipped_path,
                record.base_stem,
                "rule_codegen",
                reason or "unknown",
            )
            return None
    else:
        code, reason = _generate_code_llm(fusion_json)
        if not code:
            code, fallback_reason = _generate_code_rule_based(
                record.json_path, fusion_json, fallback_codegen_fn
            )
            if not code:
                _append_skipped(
                    skipped_path,
                    record.base_stem,
                    "llm_codegen",
                    f"{reason}; fallback: {fallback_reason}",
                )
                return None

    cq_code_path = cadquery_root / f"{record.base_stem}.py"
    cq_code_path.parent.mkdir(parents=True, exist_ok=True)
    cq_code_path.write_text(_ensure_export_line(code), encoding="utf-8")

    gen_step_path = gen_step_root / f"{record.base_stem}.step"
    ran, reason = _execute_cadquery_script(code, gen_step_path, timeout_sec=60)
    if not ran:
        _append_skipped(skipped_path, record.base_stem, "execute", reason or "?")
        return None

    # Stage D1: 3D IoU
    iou, iou_err = _compute_iou(record.gt_step_path, gen_step_path)
    if iou_err:
        _append_skipped(skipped_path, record.base_stem, "iou", iou_err)
        return None

    complexity_class = _classify_complexity(fusion_json)
    iou_pass = iou >= IOU_THRESHOLD

    # Stage D2: visual comparison (only when D1 passes; skip if flag set)
    visual_verdict = "SKIP"
    visual_reason = ""
    if iou_pass and not skip_visual:
        views_gen_dir = gen_step_root.parent / "views_gen" / record.base_stem
        rendered_gen, render_err = _render_views(
            gen_step_path, views_gen_dir, max_px=max_px
        )
        if rendered_gen:
            visual_verdict, visual_reason = _compare_views_visual(
                views_raw_dir, views_gen_dir
            )
        else:
            visual_verdict = "ERROR"
            visual_reason = f"render_gen: {render_err}"
    elif not iou_pass:
        visual_verdict = "SKIP"
        visual_reason = f"IoU={iou:.3f} < {IOU_THRESHOLD} — visual skipped"

    views_gen_dir_final = (
        gen_step_root.parent / "views_gen" / record.base_stem
        if not skip_visual
        else None
    )

    verified = iou_pass and (skip_visual or visual_verdict == "PASS")

    return {
        "stem": record.stem,
        "base_stem": record.base_stem,
        "raw_step_path": _repo_rel(record.gt_step_path),
        "ops_json_path": _repo_rel(record.json_path),
        "gen_step_path": _repo_rel(gen_step_path),
        "cq_code_path": _repo_rel(cq_code_path),
        "views_raw_dir": _repo_rel(views_raw_dir),
        "views_gen_dir": (
            _repo_rel(views_gen_dir_final) if views_gen_dir_final else None
        ),
        "complexity_class": complexity_class,
        "iou": round(iou, 6),
        "visual_verdict": visual_verdict,
        "visual_reason": visual_reason,
        "verified": verified,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "data/verified",
        help="Output directory for verified index and generated STEPs",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most this many matched parts (0 = all)",
    )
    parser.add_argument(
        "--max-px",
        type=int,
        default=600,
        help="Max PNG dimension in pixels",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip OpenAI code generation and use rule-based only",
    )
    parser.add_argument(
        "--step-dir",
        type=Path,
        default=GT_STEP_DIR,
        help="Override GT STEP directory",
    )
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=JSON_DIR,
        help="Override Fusion360 reconstruction JSON directory",
    )
    parser.add_argument(
        "--skip-visual",
        action="store_true",
        help="Skip Stage D2 visual comparison (faster, IoU-only validation)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not CQ_PYTHON.exists():
        print(f"CadQuery python not found: {CQ_PYTHON}", file=sys.stderr)
        return 2

    views_root = REPO_ROOT / "data/views"
    cadquery_root = REPO_ROOT / "data/cadquery"
    gen_step_root = out_dir / "generated_step"
    skipped_path = views_root / "skipped.txt"
    verified_jsonl = out_dir / "verified_pairs.jsonl"

    records = _build_index(args.json_dir, args.step_dir, limit=args.limit)
    if not records:
        print("No matched JSON/STEP pairs found.")
        return 1

    fallback_codegen_fn, fallback_err = _load_rule_based_codegen()
    if args.no_llm and fallback_codegen_fn is None:
        print(
            "Rule-based codegen unavailable and --no-llm was requested: "
            f"{fallback_err}",
            file=sys.stderr,
        )
        return 2

    results: list[dict[str, Any]] = []
    for idx, record in enumerate(records, start=1):
        print(f"[{idx}/{len(records)}] {record.base_stem}")
        row = _process_part(
            record=record,
            views_root=views_root,
            cadquery_root=cadquery_root,
            gen_step_root=gen_step_root,
            skipped_path=skipped_path,
            max_px=args.max_px,
            no_llm=args.no_llm,
            fallback_codegen_fn=fallback_codegen_fn,
            skip_visual=args.skip_visual,
        )
        if row is not None:
            results.append(row)

    with verified_jsonl.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    summary = {
        "indexed": len(records),
        "written": len(results),
        "verified": sum(1 for row in results if row["verified"]),
        "iou_pass": sum(1 for row in results if row.get("iou", 0) >= IOU_THRESHOLD),
        "visual_pass": sum(1 for row in results if row.get("visual_verdict") == "PASS"),
        "verified_pairs_jsonl": _repo_rel(verified_jsonl),
        "skipped_log": _repo_rel(skipped_path),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
