"""All system + user prompts and shared parsers used by bench runners.

Kept separate from the adapter layer: prompts are task-specific, adapters
are provider-specific, and the runner glues them.
"""

from __future__ import annotations

import json as _json
import re

# ── img2cq (eval.py / run_test.py) ────────────────────────────────────────────

SYSTEM_PROMPT = """Generate CadQuery Python code from a 2x2 composite of 4 diagonal views, all looking at the part center [0.5,0.5,0.5]:
- Top-left: camera at [ 1,  1,  1]
- Top-right: camera at [-1, -1, -1]
- Bottom-left: camera at [-1,  1, -1]
- Bottom-right: camera at [ 1, -1,  1]

Renders are normalized: bbox centered at [0.5,0.5,0.5], longest side maps to [0,1].
Match the orientation exactly - do not rotate or remap axes. World XYZ in your code must match world XYZ in the renders.
- cadquery is pre-imported as cq; no imports, no show_object
- Store final solid in result
- Output ONLY code, no explanation or markdown
"""

USER_PROMPT = (
    "Generate CadQuery code to recreate this industrial part shown in the "
    "4-view composite render."
)

CADRILLE_SYSTEM_PROMPT = (
    "You are a CadQuery expert. Given a 2×2 grid of normalized multi-view renders "
    "of a mechanical part (four diagonal viewpoints: [1,1,1], [-1,-1,-1], [-1,1,-1], "
    "[1,-1,1]), write CadQuery Python code that reproduces the geometry. "
    "Output ONLY Python code."
)

# ── QA (img + Qs) and code-QA (code + Qs) ─────────────────────────────────────

QA_IMG_SYSTEM_PROMPT = """You are an expert CAD engineer. You will be shown a 2×2 composite image of a mechanical part (4 diagonal viewpoints: camera at [1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1], looking at bbox center [0.5, 0.5, 0.5]).

You will be given a list of numeric questions about the part. Answer each with a single number.

Rules:
- Output ONLY a JSON array of numbers, one per question, in the same order.
- No text, no keys, no explanation. Just the array.
- For yes/no questions, use 1 for yes and 0 for no.
- For count questions, use an integer (e.g. 12, not "twelve").
- For ratio questions, use a decimal (e.g. 2.5).
- For dimensional questions, answer in whatever consistent unit the code uses (scale is arbitrary; the grader compares numeric magnitude).

Example input: ["How many teeth?", "What is the module?"]
Example output: [20, 2.5]"""

QA_CODE_SYSTEM_PROMPT = """You are an expert CAD engineer. You will be shown CadQuery Python code for a mechanical part. You will be given a list of numeric questions about the part this code produces.

Rules:
- Output ONLY a JSON array of numbers, one per question, in the same order.
- No text, no keys, no explanation. Just the array.
- For yes/no questions, use 1 for yes and 0 for no.
- For count questions, use an integer (e.g. 12, not "twelve").
- For ratio questions, use a decimal (e.g. 2.5).
- For dimensional questions, answer using the same scale as the numeric literals in the code.

Example input code creates a gear with 20 teeth and module 2.5.
Example input questions: ["How many teeth?", "What is the module?"]
Example output: [20, 2.5]"""


def build_qa_user_text(questions: list[str], code: str | None = None) -> str:
    """Compose the user message for QA: optional code preamble + JSON Qs."""
    qs = _json.dumps(questions)
    if code is not None:
        return (
            "CadQuery code:\n```python\n"
            + code
            + "\n```\n\nQuestions (answer each with a single number, JSON array):\n"
            + qs
        )
    return (
        "Answer these questions about the part shown. "
        "Output ONLY a JSON array of numbers, same order:\n" + qs
    )


# ── Edit (code + instr [+ img]) ───────────────────────────────────────────────

EDIT_CODE_SYSTEM_PROMPT = """You are an expert CAD engineer. You will be given:
1. A CadQuery Python script that builds a parametric mechanical part.
2. A natural-language edit instruction describing a single numeric change.

Your task: return the script with that one change applied. Keep every other line
and value exactly the same.

Rules:
- Output ONLY executable Python code, no explanation, no markdown fences.
- The top of the script has a `# --- parameters ---` comment block listing the
  numeric parameters by name. Use those names to find the value to change.
- If the instruction says "Set X to V", set the value to V (same scale as the original literal).
- If the instruction says "Change X by +P%" or "-P%", multiply the current value
  by (1 + P/100) and keep up to 4 decimal places.
- Do NOT refactor, rename, reorder, or add imports."""

EDIT_IMG_SYSTEM_PROMPT = """You are an expert CAD engineer. You will be given:
1. A 2x2 composite image of the part from 4 diagonal viewpoints.
2. A CadQuery Python script that builds the part.
3. A natural-language edit instruction describing a numeric change.

IMPORTANT — parameters are DERIVED, not literal:
The `# --- parameters ---` comment block lists the logical parameter names
(e.g. `hole_pitch_L = 120.0`), but the numbers in the actual code are USUALLY
NOT equal to the parameter value. They are arithmetic expressions over it
that have been pre-computed to floats. To edit correctly you MUST:
  (a) identify every literal that depends on the target parameter,
  (b) work out the formula from the literal + original parameter value,
  (c) re-evaluate the formula with the new parameter value.

Use the 2x2 image to disambiguate which literals correspond to which physical
dimension when the code alone is ambiguous.

Worked example
--------------
Original code (parameter comment says hole_pitch_L = 120.0):
    .transformed(offset=cq.Vector(-60.0, 0, 16.45))   # -60  == -L/2
    .transformed(offset=cq.Vector(60.0, 0, 16.45))    #  60  ==  L/2
    .cylinder(130.2, 5.1)                              # 130.2 == L + 10.2

Instruction: "Set the hole pitch L to 123.6."
You must update ALL THREE literals, not just the comment:
    .transformed(offset=cq.Vector(-61.8, 0, 16.45))    # -123.6/2
    .transformed(offset=cq.Vector(61.8, 0, 16.45))     #  123.6/2
    .cylinder(133.8, 5.1)                               #  123.6 + 10.2
and update the comment to `# hole_pitch_L = 123.6`.

Rules
-----
- Output ONLY executable Python code, no explanation, no markdown fences.
- For "Set X to V unit": set the parameter comment to V. For every literal that
  depended on the old value, recompute with the new value (preserve the
  inferred formula). Keep up to 4 decimals.
- For "Change X by +P%" / "-P%": new_X = old_X * (1 + P/100); then apply the
  same recomputation to every dependent literal.
- Do NOT refactor, rename, reorder, or add imports.
- Keep every literal that does NOT depend on X byte-identical."""


def build_edit_user_text(orig_code: str, instruction: str) -> str:
    return (
        "Original CadQuery code:\n```python\n"
        + orig_code
        + "\n```\n\nEdit instruction: "
        + instruction
        + "\n\nReturn the full modified script."
    )


# ── Output cleaning + parsing ─────────────────────────────────────────────────


def strip_fences(code: str) -> str:
    code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.M)
    code = re.sub(r"```\s*$", "", code, flags=re.M)
    return code.strip()


def parse_qa_answers(raw: str, n_expected: int) -> list[float] | None:
    """Extract a JSON array of n_expected numbers. Returns None on mismatch."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.M)
    s = re.sub(r"```\s*$", "", s, flags=re.M).strip()
    m = re.search(r"\[[^\[\]]*\]", s, flags=re.S)
    if not m:
        return None
    try:
        arr = _json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(arr, list) or len(arr) != n_expected:
        return None
    out: list[float] = []
    for x in arr:
        try:
            out.append(float(x))
        except Exception:
            return None
    return out
