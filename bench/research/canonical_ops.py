"""Per-family essential ops — AND-of-(OR-tuples) format.

The dict `ESSENTIAL_BY_FAMILY` is loaded at import time from the sibling
`canonical_ops.yaml`. Edit the YAML to tweak the metric — no code change.

Format (in YAML):
  family_name: [<element>, ...]
    • outer list = AND (every element must be satisfied)
    • element = string (single required op)  OR  list of strings (OR alternatives)

Match rule:
  essential_pass = True iff for every outer element, at least one alternative
  is in gen_ops. E.g. `[[sweep, revolve], rarray]` ⇒ (sweep OR revolve) AND rarray.

Independent of FEATURE_CLASS (chamfer / fillet / hole) — scored separately
via feature_f1; those names must NOT appear inside essentials.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Union

import yaml

OpSpec = Union[str, tuple[str, ...]]
EssentialList = list[OpSpec]

YAML_PATH = Path(__file__).with_suffix(".yaml")

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


def _load_essentials(path: Path = YAML_PATH) -> dict[str, EssentialList]:
    """Read canonical_ops.yaml; convert YAML lists → tuples for hashable OR-sets."""
    raw = yaml.safe_load(path.read_text()) or {}
    out: dict[str, EssentialList] = {}
    for fam, spec in raw.items():
        if not isinstance(spec, list):
            raise ValueError(f"{fam}: spec must be a list, got {type(spec).__name__}")
        elements: EssentialList = []
        for elem in spec:
            if isinstance(elem, str):
                elements.append(elem)
            elif isinstance(elem, list):
                elements.append(tuple(elem))
            else:
                raise ValueError(f"{fam}: element must be str or list, got {elem!r}")
        # sanity: forbid feature ops in essentials
        flat = {a for e in elements for a in (e if isinstance(e, tuple) else (e,))}
        bad = flat & FEATURE_CLASS
        if bad:
            raise ValueError(f"{fam}: feature ops {bad} cannot be in essentials")
        out[fam] = elements
    return out


ESSENTIAL_BY_FAMILY: dict[str, EssentialList] = _load_essentials()


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
