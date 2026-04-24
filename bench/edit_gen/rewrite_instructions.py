"""Rewrite every instruction in topup_final/manifest.csv with explicit position.

For each record, look up its op_code from the source jsonl (topup_diverse,
topup_manual, topup_rotate), parse size/position/axis info, and emit a new
instruction that always specifies WHERE the edit is applied.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
FINAL = BENCH / "topup_final"


def load_op_codes() -> dict[str, str]:
    """Build record_id → op_code from all source jsonl."""
    codes = {}
    for src in [BENCH / "topup_diverse", BENCH / "topup_manual",
                BENCH / "topup_rotate"]:
        rec_file = src / "records.jsonl"
        if not rec_file.exists():
            continue
        for ln in rec_file.read_text().splitlines():
            if not ln:
                continue
            r = json.loads(ln)
            codes[r["record_id"]] = r.get("op_code") or ""
    return codes


# ── Regex helpers ─────────────────────────────────────────────────────────────
_RE_CUT_XY = re.compile(
    r"cq\.Workplane\('XY'\)"
    r"(?:\.transformed\(offset=cq\.Vector\(([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\)\))?"
    r"\.cylinder\(([\d\.]+),\s*([\d\.]+)\)"
)
_RE_CUT_YZ = re.compile(
    r"cq\.Workplane\('YZ'\)"
    r"(?:\.transformed\(offset=cq\.Vector\(([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\)\))?"
    r"\.cylinder\(([\d\.]+),\s*([\d\.]+)\)"
)
_RE_CUT_XZ = re.compile(
    r"cq\.Workplane\('XZ'\)"
    r"(?:\.transformed\(offset=cq\.Vector\(([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\)\))?"
    r"\.cylinder\(([\d\.]+),\s*([\d\.]+)\)"
)
_RE_CUT_BOX = re.compile(
    r"cq\.Workplane\('XY'\)"
    r"\.transformed\(offset=cq\.Vector\(([-\d\.]+),\s*([-\d\.]+),\s*([-\d\.]+)\)\)"
    r"\.box\(([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)\)"
)
_RE_FILLET = re.compile(r"\.edges\('([^']+)'\)\.fillet\(([\d\.]+)\)")
_RE_CHAMFER = re.compile(r"\.edges\('([^']+)'\)\.chamfer\(([\d\.]+)\)")
_RE_FACE_CHAMFER = re.compile(r"\.faces\('([^']+)'\)\.chamfer\(([\d\.]+)\)")
_RE_PUSH_HOLE = re.compile(
    r"\.faces\('([^']+)'\)\.workplane\(\)"
    r"\.pushPoints\(\[\(([-\d\.]+),\s*([-\d\.]+)\)\]\)\.hole\(([\d\.]+)\)"
)
_RE_PUSH_HOLE_CENTERED = re.compile(
    r"\.faces\('([^']+)'\)\.workplane\(centerOption='CenterOfBoundBox'\)"
    r"\.pushPoints\(\[\(([-\d\.]+),\s*([-\d\.]+)\)\]\)\.hole\(([\d\.]+)\)"
)
_RE_SLOT = re.compile(
    r"\.faces\('([^']+)'\)\.workplane\(centerOption='CenterOfBoundBox'\)"
    r"\.slot2D\(([\d\.]+),\s*([\d\.]+)\)\.cutBlind\(-([\d\.]+)\)"
)
_RE_POLYGON = re.compile(
    r"\.faces\('([^']+)'\)\.workplane\(centerOption='CenterOfBoundBox'\)"
    r"\.polygon\((\d+),\s*([\d\.]+)\)\.cutBlind\(-([\d\.]+)\)"
)
_RE_ROTATE = re.compile(
    r"result\.rotate\(\(0,0,0\),\s*\(([\d]+),([\d]+),([\d]+)\),\s*(\d+)\)"
)


def fmt(v: float) -> str:
    """Format number without unnecessary zeros."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def rewrite(op_code: str, edit_type: str, family: str) -> str:
    """Infer a positional instruction from op_code."""
    if not op_code:
        return ""

    # Rotation
    m = _RE_ROTATE.search(op_code)
    if m:
        vx, vy, vz, deg = m.groups()
        axis = "X" if vx == "1" else ("Y" if vy == "1" else "Z")
        return (f"Rotate the entire part about the origin by {deg}° around "
                f"the {axis} axis.")

    # Box cut (used for handle-slot style)
    m = _RE_CUT_BOX.search(op_code)
    if m:
        ox, oy, oz, bx, by, bz = m.groups()
        return (f"Cut a rectangular notch ({fmt(float(bx))}×{fmt(float(by))}×"
                f"{fmt(float(bz))} mm) centered at "
                f"({fmt(float(ox))}, {fmt(float(oy))}, {fmt(float(oz))}) mm.")

    # Cylinder cut along Z axis (Workplane('XY'))
    m = _RE_CUT_XY.search(op_code)
    if m:
        ox, oy, oz, L, r = m.groups()
        d = 2 * float(r)
        pos = "the center" if ox is None or (ox == oy == oz == "0.0") \
            else f"position ({fmt(float(ox))}, {fmt(float(oy))}) mm"
        if ox is None:
            pos = "the center"
        return (f"Drill a {fmt(d)} mm diameter through-hole at {pos} along "
                f"the Z axis.")

    # Cylinder cut along X axis (Workplane('YZ'))
    m = _RE_CUT_YZ.search(op_code)
    if m:
        ox, oy, oz, L, r = m.groups()
        d = 2 * float(r)
        if ox is None:
            pos = "centered on the origin"
        else:
            pos = (f"at z-offset {fmt(float(oz))} mm" if float(oz or 0) != 0
                   else "centered on the origin")
        return (f"Drill a {fmt(d)} mm diameter cross-hole through the part "
                f"along the X axis {pos}.")

    # Cylinder cut along Y axis (Workplane('XZ'))
    m = _RE_CUT_XZ.search(op_code)
    if m:
        ox, oy, oz, L, r = m.groups()
        d = 2 * float(r)
        if ox is None:
            pos = "centered on the origin"
        else:
            pos = f"at y-offset {fmt(float(oy))} mm" if float(oy or 0) != 0 \
                  else "centered on the origin"
        return (f"Drill a {fmt(d)} mm diameter cross-hole through the part "
                f"along the Y axis {pos}.")

    # Push-point hole on face
    m = _RE_PUSH_HOLE_CENTERED.search(op_code) or _RE_PUSH_HOLE.search(op_code)
    if m:
        face, px, py, d = m.groups()
        return (f"Drill a {fmt(float(d))} mm diameter through-hole at "
                f"({fmt(float(px))}, {fmt(float(py))}) on the '{face}' face.")

    # Slot on face
    m = _RE_SLOT.search(op_code)
    if m:
        face, L, W, D = m.groups()
        return (f"Cut a {fmt(float(L))}×{fmt(float(W))} mm slot "
                f"{fmt(float(D))} mm deep, centered on the '{face}' face.")

    # Polygon (hex socket) on face
    m = _RE_POLYGON.search(op_code)
    if m:
        face, n, D, d = m.groups()
        return (f"Cut a {n}-sided hex socket {fmt(float(D))} mm across-flats, "
                f"{fmt(float(d))} mm deep, centered on the '{face}' face.")

    # Fillet on edges
    m = _RE_FILLET.search(op_code)
    if m:
        selector, r = m.groups()
        human = selector_desc(selector)
        return f"Fillet {human} by {fmt(float(r))} mm."

    # Chamfer on edges
    m = _RE_CHAMFER.search(op_code)
    if m:
        selector, d = m.groups()
        human = selector_desc(selector)
        return f"Chamfer {human} by {fmt(float(d))} mm."

    # Face-level chamfer
    m = _RE_FACE_CHAMFER.search(op_code)
    if m:
        face, d = m.groups()
        return (f"Chamfer all edges of the '{face}' face by "
                f"{fmt(float(d))} mm.")

    # Union (boss/extrude) - we dropped boss, but keep a fallback
    if ".union(" in op_code and ".extrude(" in op_code:
        return op_code  # leave as-is; should not appear in final

    return ""  # unable to parse


def selector_desc(sel: str) -> str:
    sel_l = sel.lower()
    if sel_l == "|z":
        return "the outer vertical edges"
    if sel_l == "|x":
        return "the outer X-direction edges"
    if sel_l == "|y":
        return "the outer Y-direction edges"
    if "%circle" in sel_l:
        if ">z" in sel_l:
            return "the top circular edges"
        if "<z" in sel_l:
            return "the bottom circular edges"
        if ">y" in sel_l:
            return "the top (+Y) circular edges"
        if "<y" in sel_l:
            return "the bottom (-Y) circular edges"
        return "all circular edges"
    return f"edges matching selector '{sel}'"


def main():
    op_codes = load_op_codes()

    # Load current manifest
    rows = []
    with (FINAL / "manifest.csv").open() as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)

    # Rewrite
    unmatched = []
    rot_re = re.compile(r"_rotate_([XYZ])(\d+)$")
    for r in rows:
        rid = r["record_id"]
        op = op_codes.get(rid, "")
        new_inst = rewrite(op, r["edit_type"], r["family"])
        if not new_inst and r["edit_type"] == "rotate":
            m = rot_re.search(rid)
            if m:
                axis, deg = m.groups()
                new_inst = (f"Rotate the entire part about the origin by "
                            f"{deg}° around the {axis} axis.")
        if not new_inst:
            unmatched.append(rid)
            continue
        r["instruction"] = new_inst

    # Write back
    csv_path = FINAL / "manifest.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"rewrote {len(rows) - len(unmatched)} / {len(rows)} instructions")
    if unmatched:
        print(f"unmatched ({len(unmatched)}):")
        for u in unmatched[:20]:
            print(f"  {u}: op={op_codes.get(u, '(missing)')[:100]}")

    # Also update records.jsonl
    jl = FINAL / "records.jsonl"
    recs = [json.loads(ln) for ln in jl.read_text().splitlines() if ln]
    inst_by_rid = {r["record_id"]: r["instruction"] for r in rows}
    for r in recs:
        r["instruction"] = inst_by_rid.get(r["record_id"], r.get("instruction", ""))
    jl.write_text("\n".join(json.dumps(r) for r in recs))
    print(f"updated {jl}")


if __name__ == "__main__":
    main()
