"""Automatic dim-change topup for families with <3 records.

For each family, scan the orig .py, find a numeric param in a shape primitive
(.circle / .cylinder / .box / .extrude / .rect), scale by a factor (1.3 or
0.7), exec, gate by 0.3 < IoU < 0.99.

For each family tries up to N param substitutions, keeping up to (3 - have)
distinct successful edits.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from bench.edit_gen.topup_edits import exec_cq
from bench.edit_gen.edit_axes import EDIT_AXES

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
FINAL = BENCH / "topup_final"


def pick_orig(family: str) -> Path | None:
    codes = BENCH / "codes"
    steps = BENCH / "steps"
    for c in [codes / f"{family}_easy_r0_orig.py",
              codes / f"{family}_hard_r0_orig.py",
              *sorted(codes.glob(f"{family}_gid*_orig.py")),
              *sorted(codes.glob(f"{family}_*_orig.py"))]:
        if c.exists() and (steps / (c.stem + ".step")).exists():
            return c
    return None


def find_dim_candidates(text: str) -> list[tuple[str, str, float, str]]:
    """Return list of (search_str, kind, original_value, human_param_name).
    Each candidate replaces one numeric literal in a shape primitive.
    """
    cands = []

    # .circle(r)
    for m in re.finditer(r"\.circle\((\d+\.?\d*)\)", text):
        r = float(m.group(1))
        if r > 0.3:
            cands.append((m.group(0), "circle_radius", r, f"circle radius {r}"))

    # .cylinder(h, r)
    for m in re.finditer(r"\.cylinder\((\d+\.?\d*),\s*(\d+\.?\d*)\)", text):
        h = float(m.group(1))
        r = float(m.group(2))
        if r > 0.3:
            cands.append((m.group(0),
                          "cylinder_radius",
                          r,
                          f"cylinder radius {r}"))
        if h > 0.3:
            cands.append((m.group(0),
                          "cylinder_height",
                          h,
                          f"cylinder height {h}"))

    # .box(a, b, c)
    for m in re.finditer(r"\.box\((\d+\.?\d*),\s*(\d+\.?\d*),\s*(\d+\.?\d*)\)",
                          text):
        a = float(m.group(1))
        b = float(m.group(2))
        c = float(m.group(3))
        if a > 0.3: cands.append((m.group(0), "box_x", a, f"box x {a}"))
        if b > 0.3: cands.append((m.group(0), "box_y", b, f"box y {b}"))
        if c > 0.3: cands.append((m.group(0), "box_z", c, f"box z {c}"))

    # .extrude(h) where h is a bare float, not on multiple lines
    for m in re.finditer(r"\.extrude\((\d+\.?\d*)\)", text):
        h = float(m.group(1))
        if h > 0.3:
            cands.append((m.group(0),
                          "extrude",
                          h,
                          f"extrude height {h}"))

    # .rect(a, b)
    for m in re.finditer(r"\.rect\((\d+\.?\d*),\s*(\d+\.?\d*)\)", text):
        a = float(m.group(1))
        b = float(m.group(2))
        if a > 0.3: cands.append((m.group(0), "rect_a", a, f"rect width {a}"))
        if b > 0.3: cands.append((m.group(0), "rect_b", b, f"rect height {b}"))

    return cands


def apply_sub(text: str, cand: tuple, factor: float) -> tuple[str, float]:
    """Substitute the numeric in the first matching occurrence. Return
    (new_text, new_value)."""
    search, kind, orig_val, _ = cand
    new_val = round(orig_val * factor, 2)
    if new_val <= 0.1:
        return text, 0.0
    # Build replacement by swapping only the target number in the matched str.
    # Since the match uniquely determines position, find first occurrence of
    # search and rebuild with new value.
    idx = text.find(search)
    if idx < 0:
        return text, 0.0
    # Parse the search string's nested numbers
    nums = re.findall(r"\d+\.?\d*", search)
    # Decide which position to replace based on kind
    pos_map = {
        "circle_radius": 0,
        "cylinder_height": 0,
        "cylinder_radius": 1,
        "box_x": 0, "box_y": 1, "box_z": 2,
        "extrude": 0,
        "rect_a": 0, "rect_b": 1,
    }
    pos = pos_map[kind]
    if pos >= len(nums):
        return text, 0.0
    # Replace nth number in search
    count = 0
    def _rep(m, target_pos=pos):
        nonlocal count
        if count == target_pos:
            count += 1
            return str(new_val)
        count += 1
        return m.group(0)
    new_search = re.sub(r"\d+\.?\d*", _rep, search)
    return text[:idx] + new_search + text[idx+len(search):], new_val


def process_family(fam: str, need: int, existing_types: set) -> list[dict]:
    orig_path = pick_orig(fam)
    if orig_path is None:
        print(f"  {fam}: no orig found")
        return []
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    cands = find_dim_candidates(orig_text)
    if not cands:
        print(f"  {fam}: no dim candidates")
        return []

    codes_dir = FINAL / "codes"
    steps_dir = FINAL / "steps"
    kept = []
    seen_ops = set()
    # Try combinations of (candidate × factor) until we have enough
    for factor in [1.3, 0.7, 1.5, 0.5, 1.2, 0.8]:
        if len(kept) >= need:
            break
        for cand in cands:
            if len(kept) >= need:
                break
            search, kind, orig_val, human = cand
            op_id = f"{kind}_{orig_val}_{factor}"
            if op_id in seen_ops:
                continue
            seen_ops.add(op_id)
            new_text, new_val = apply_sub(orig_text, cand, factor)
            if new_text == orig_text or new_val <= 0.1:
                continue

            rid = f"auto_{fam}_{kind}_f{int(factor*100)}"
            orig_py = codes_dir / f"{rid}_orig.py"
            gt_py = codes_dir / f"{rid}_gt.py"
            orig_step = steps_dir / f"{rid}_orig.step"
            gt_step = steps_dir / f"{rid}_gt.step"
            orig_py.write_text(orig_text)
            gt_py.write_text(new_text)

            if orig_step_src.exists():
                shutil.copy(orig_step_src, orig_step)
            else:
                ok, err = exec_cq(orig_text, orig_step, timeout=30)
                if not ok:
                    continue

            ok, err = exec_cq(new_text, gt_step, timeout=30)
            if not ok:
                orig_py.unlink(); gt_py.unlink()
                if orig_step.exists(): orig_step.unlink()
                continue

            try:
                from bench.metrics import compute_iou
                iou, _ = compute_iou(str(orig_step), str(gt_step))
            except Exception:
                iou = None
            if iou is None or iou >= 0.99 or iou < 0.3:
                orig_py.unlink(); gt_py.unlink()
                if orig_step.exists(): orig_step.unlink()
                if gt_step.exists(): gt_step.unlink()
                continue

            instr = (f"Change the {human.replace(orig_val.__repr__()[:len(str(orig_val))]+'', '')[:50]} "
                     f"from {orig_val} to {new_val}.")
            # simpler instruction
            human_clean = human.split()[0] if " " in human else human
            direction = "Increase" if new_val > orig_val else "Decrease"
            short_name = {
                "circle_radius": "circle radius",
                "cylinder_radius": "cylinder radius",
                "cylinder_height": "cylinder height",
                "box_x": "box X dimension",
                "box_y": "box Y dimension",
                "box_z": "box Z dimension",
                "extrude": "extrude height",
                "rect_a": "rect width",
                "rect_b": "rect height",
            }.get(kind, kind)
            instr = f"{direction} the {short_name} from {orig_val} to {new_val}."

            kept.append({
                "record_id": rid,
                "family": fam,
                "edit_type": "dim",
                "difficulty": "easy",
                "instruction": instr,
                "iou": iou,
                "source": "auto_dim",
                "orig_code_path": f"codes/{rid}_orig.py",
                "gt_code_path": f"codes/{rid}_gt.py",
                "orig_step_path": f"steps/{rid}_orig.step",
                "gt_step_path": f"steps/{rid}_gt.step",
                "status": "ok",
            })
            print(f"  {fam}: {kind} ×{factor} IoU={iou:.3f}")
    return kept


def main():
    recs = [json.loads(l) for l in (FINAL/"records.jsonl").read_text().splitlines() if l]
    fam_cnt = {}
    for r in recs:
        fam_cnt[r["family"]] = fam_cnt.get(r["family"], 0) + 1
    need_fams = [(f, 3 - fam_cnt.get(f, 0))
                  for f in sorted(EDIT_AXES.keys())
                  if fam_cnt.get(f, 0) < 3]
    print(f"topping up {len(need_fams)} families")

    new_recs = []
    for fam, need in need_fams:
        existing_types = set(r["edit_type"] for r in recs if r["family"] == fam)
        got = process_family(fam, need, existing_types)
        new_recs.extend(got)

    print(f"\ncreated {len(new_recs)} new dim records")

    all_recs = recs + new_recs
    diff_rank = {"easy":0,"medium":1,"hard":2}
    all_recs.sort(key=lambda r: (r["family"], diff_rank.get(r.get("difficulty","medium"),9), r["record_id"]))
    (FINAL/"records.jsonl").write_text("\n".join(json.dumps(r) for r in all_recs))

    # Stats
    fam_cnt = {}
    for r in all_recs:
        fam_cnt[r["family"]] = fam_cnt.get(r["family"], 0) + 1
    from bench.edit_gen.edit_axes import EDIT_AXES as EA
    missing = [f for f in EA if fam_cnt.get(f, 0) < 3]
    print(f"\nstill <3: {len(missing)}")
    for f in missing:
        print(f"  {f}: {fam_cnt.get(f, 0)}")


if __name__ == "__main__":
    main()
