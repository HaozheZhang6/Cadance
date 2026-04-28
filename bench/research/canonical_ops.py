"""Per-family essential ops — v4, AND-of-(OR-tuples) format.

User-requested format (2026-04-28):
  spec = [<element>, <element>, ...]      ← outer list is AND
  element = "op"  OR  ("op_a", "op_b")    ← string or tuple-of-alternatives is OR

Match rule:
  full score iff for every element, AT LEAST ONE of its alternatives is in
  gen_ops.  E.g. spec = [("sweep", "revolve"), "rarray"] requires gen to
  contain (sweep OR revolve) AND rarray.

Independent of FEATURE_CLASS (chamfer / fillet / hole) — those are scored
separately via has_* indicators; they never appear inside essentials.

Alternatives policy:
  - revolve ↔ sweep (axisymmetric: revolve(360°) ≡ sweep along closed circle)
  - revolve ↔ makeTorus (torus = revolved circle)
  - U/J  bend: sweep ≡ revolve(180°) trick
  - twistExtrude ↔ loft (twisted profile ≈ loft of N rotated cross-sections)
  - sweep+helix ↔ sweep (helix path is a special sweep curve)
  - taper= ↔ loft (tapered extrude ≈ loft between two scaled circles)

Excluded as essential (always-OK alternatives exist):
  - shell: NO good alternative — extrude+cut produces same shape but not the
    same intent; we still keep `shell` as the only spec because reviewer
    might disagree on "extrude+cut equivalent".
  - polarArray, rarray: arrays could be N copies via union, but that's brittle
    and not realistic for typical synthesis. We keep them strict.
"""
from __future__ import annotations

import re
from typing import Union

OpSpec = Union[str, tuple[str, ...]]
EssentialList = list[OpSpec]

# ── ops we recognize in code ──────────────────────────────────────────────
OP_PATTERNS: dict[str, str] = {
    "twistExtrude":  r"\.twistExtrude\s*\(",
    "sweep+helix":   r"\.sweep\s*\([^)]*helix|\.sweep\s*\([^)]*makeHelix|sweep.*makeHelix",
    "sweep":         r"\.sweep\s*\(",
    "revolve":       r"\.revolve\s*\(",
    "loft":          r"\.loft\s*\(",
    "shell":         r"\.shell\s*\(",
    "taper=":        r"taper\s*=",
    "polarArray":    r"\.polarArray\s*\(",
    "rarray":        r"\.rarray\s*\(",
    "makeTorus":     r"makeTorus\s*\(",
    # feature class (independent — for has_* score, NOT for essentials)
    "chamfer":       r"\.chamfer\s*\(",
    "fillet":        r"\.fillet\s*\(",
    "hole":          r"\.(hole|cboreHole|cskHole|cutThruAll)\s*\(",
}

ESSENTIAL_CLASS: frozenset[str] = frozenset({
    "sweep+helix", "sweep", "revolve", "loft", "shell", "taper=",
    "polarArray", "rarray", "twistExtrude", "makeTorus",
})
FEATURE_CLASS: frozenset[str] = frozenset({"chamfer", "fillet", "hole"})


# ── per-family essentials ─────────────────────────────────────────────────
# 44 families with essentials; 62 omitted = N/A (no essential check)
ESSENTIAL_BY_FAMILY: dict[str, EssentialList] = {
    # ── axisymmetric ──── revolve OR sweep (closed-path sweep ≡ revolve)
    "bellows":           [("revolve", "sweep")],
    "bucket":            [("revolve", "sweep")],
    "cotter_pin":        [("revolve", "sweep")],
    "dome_cap":          [("revolve", "sweep")],
    "grease_nipple":     [("revolve", "sweep")],
    "grommet":           [("revolve", "sweep")],
    "lathe_turned_part": [("revolve", "sweep")],
    "nozzle":            [("revolve", "sweep")],
    "piston":            [("revolve", "sweep")],
    "pulley":            [("revolve", "sweep")],
    "rivet":             [("revolve", "sweep")],
    "taper_pin":         [("revolve", "sweep")],
    "venturi_tube":      [("revolve", "sweep")],

    # ── ring / torus shapes ────
    "torus_link":  [("revolve", "sweep", "makeTorus")],
    "eyebolt":     [("makeTorus", "revolve", "sweep")],

    # ── partial-rotational (U / J) ────
    "u_bolt":  [("sweep", "revolve")],
    "j_hook":  [("sweep", "revolve")],

    # ── helical ────
    "torsion_spring": ["sweep+helix"],
    "worm_screw":     ["sweep+helix"],
    "coil_spring":    [("sweep+helix", "sweep")],

    # ── twisted along axis ────
    "twisted_drill":   [("twistExtrude", "loft")],
    "twisted_bracket": [("loft", "twistExtrude")],
    "helical_gear":    [("loft", "twistExtrude")],

    # ── loft (cross-section interpolation) ────
    "bevel_gear":   ["loft"],
    "propeller":    ["loft"],
    "tapered_boss": [("loft", "taper=")],
    "wing_nut":     ["loft"],

    # ── tapered profile ────
    "knob": [("taper=", "loft")],

    # ── shell / hollow ────
    "enclosure":        ["shell"],
    "sheet_metal_tray": ["shell"],

    # ── polar (rotational) arrays ────
    "motor_end_cap": ["polarArray"],

    # ── linear arrays ────
    "cable_routing_panel": ["rarray"],
    "heat_sink":           ["rarray"],
    "mesh_panel":          ["rarray"],
    "rib_plate":           ["rarray"],
    "slotted_plate":       ["rarray"],
    "vented_panel":        ["rarray"],
    "waffle_plate":        ["rarray"],

    # ── general sweep (non-helical) ────
    "duct_elbow": ["sweep"],
    "pipe_elbow": ["sweep"],

    # ── uncertain (yellow) — variants in GT ────
    "wall_anchor":    [("revolve", "sweep")],
    "round_flange":   ["polarArray"],
    "t_pipe_fitting": ["polarArray"],
    "tee_nut":        [("taper=", "loft")],
}


# ── helpers ───────────────────────────────────────────────────────────────
def find_ops(code: str) -> set[str]:
    """All recognized ops in code. Collapses sweep+helix → drops plain sweep."""
    found = set()
    for name, pat in OP_PATTERNS.items():
        if re.search(pat, code or ""):
            found.add(name)
    if "sweep+helix" in found:
        found.discard("sweep")
    return found


def essential_pass(family: str, gen_ops: set[str]) -> bool | None:
    """Per-stem essential check.

    Returns:
        True  — full score (every element satisfied by gen_ops)
        False — at least one element missing
        None  — N/A, family has no essential spec
    """
    spec = ESSENTIAL_BY_FAMILY.get(family)
    if not spec:
        return None
    for element in spec:
        if isinstance(element, str):
            if element not in gen_ops:
                return False
        else:  # tuple of alternatives
            if not any(alt in gen_ops for alt in element):
                return False
    return True


def feature_f1(gen_ops: set[str], gt_ops: set[str]) -> float:
    """F1 over FEATURE_CLASS indicators (chamfer, fillet, hole) — independent."""
    keys = list(FEATURE_CLASS)
    gt_b = {k: (k in gt_ops) for k in keys}
    gen_b = {k: (k in gen_ops) for k in keys}
    tp = sum(1 for k in keys if gt_b[k] and gen_b[k])
    fp = sum(1 for k in keys if gen_b[k] and not gt_b[k])
    fn = sum(1 for k in keys if gt_b[k] and not gen_b[k])
    if not (tp + fp + fn):
        return 1.0
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def fmt_spec(spec: EssentialList) -> str:
    parts = []
    for elem in spec:
        if isinstance(elem, str):
            parts.append(elem)
        else:
            parts.append("(" + " | ".join(elem) + ")")
    return " AND ".join(parts) if len(parts) > 1 else parts[0]
