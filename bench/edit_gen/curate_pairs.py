"""UA-20 — Curate per-family low-coupling edit pairs.

For each family, pick the best single-occurrence param (late-feature preferred).
Apply a single-line body edit + param-comment update, exec gt, compute IoU.
Output pairs_curated.jsonl + gt code/step files.

Families with zero clean candidates go to curated_manual.jsonl (human-written).

Usage:
    python -m bench.edit_gen.curate_pairs                  # build all from plan
    python -m bench.edit_gen.curate_pairs --dry-run        # report only
    python -m bench.edit_gen.curate_pairs --family knob    # single family
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "data_generation" / "bench_edit"
PLAN = BASE / "curate_plan.json"
LD = os.environ.get("LD_LIBRARY_PATH", "/workspace/.local/lib")

LATE_PAT = re.compile(r"fillet|chamfer|bevel", re.I)
HOLE_PAT = re.compile(r"bore|hole|cbore", re.I)


def pct_for(param_name: str) -> int:
    n = param_name.lower()
    if LATE_PAT.search(n):
        return 15
    if HOLE_PAT.search(n):
        return -8
    return 5


def forms_of(v: float) -> list[str]:
    """Numeric forms to search for in code body."""
    if v == int(v):
        return sorted({f"{int(v)}", f"{int(v)}.0", f"{v}"}, key=len, reverse=True)
    return [f"{v}"]


def render_number(v: float) -> str:
    """Shortest representation at 4-decimal precision."""
    r = round(v, 4)
    s = f"{r:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def apply_edit(orig_text: str, param: str, old_value: float, new_value: float):
    """Replace param value in code: update comment + 1 body occurrence.

    Returns (gt_text, ok, msg).
    """
    lines = orig_text.splitlines()
    body_start = next(
        (i for i, l in enumerate(lines) if l.startswith("result = (")),
        None,
    )
    if body_start is None:
        return None, False, "no result block"
    head_lines = lines[:body_start]
    body_lines = lines[body_start:]

    # 1) Update param comment in head
    new_str = render_number(new_value)
    head_replaced = False
    new_head_lines = []
    pat_head = re.compile(
        rf"^(#\s*{re.escape(param)}\s*=\s*)" + r"(-?\d+(?:\.\d+)?)" + r"(\s*)$"
    )
    for ln in head_lines:
        if not head_replaced:
            m = pat_head.match(ln)
            if m:
                new_head_lines.append(f"{m.group(1)}{new_str}{m.group(3)}")
                head_replaced = True
                continue
        new_head_lines.append(ln)

    # 2) Update body — exactly 1 occurrence
    body = "\n".join(body_lines)
    replaced = False
    for form in forms_of(old_value):
        pat = r"(?<![\d.\-])" + re.escape(form) + r"(?![\d.])"
        new_body, n = re.subn(pat, new_str, body, count=1)
        if n >= 1:
            body = new_body
            replaced = True
            break
    if not replaced:
        return None, False, f"value {old_value} not found in body"
    if not head_replaced:
        # Not fatal; comment may be missing/malformed
        pass

    gt_text = "\n".join(new_head_lines) + "\n" + body
    return gt_text, True, None


_PREAMBLE = """
import cadquery as cq
try:
    import OCP.TopoDS as _td
    if not hasattr(_td.TopoDS_Shape, 'HashCode'):
        _td.TopoDS_Shape.HashCode = lambda self, upper: self.__hash__() % upper
except Exception:
    pass
show_object = lambda *a, **kw: None
"""
_SUFFIX = """
import sys as _sys
try:
    cq.exporters.export(result, _sys.argv[1])
except Exception as _e:
    raise RuntimeError(f"export failed: {_e}")
"""


def exec_cq(code: str, out_path: Path, timeout: int = 60):
    body = [
        ln
        for ln in code.splitlines()
        if ln.strip() not in ("import cadquery as cq", "import cadquery")
    ]
    script = _PREAMBLE + "\n".join(body) + _SUFFIX
    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    try:
        r = subprocess.run(
            [sys.executable, "-c", script, str(out_path)],
            env=env,
            timeout=timeout,
            capture_output=True,
            cwd=tempfile.gettempdir(),
        )
        if r.returncode != 0:
            return False, r.stderr.decode(errors="replace")[-300:]
        if not out_path.exists() or out_path.stat().st_size < 100:
            return False, "step missing or empty"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def human_name_for(param: str) -> str:
    """Convert param_name → 'param name' with small fixups."""
    return param.replace("_", " ")


def process_entry(entry: dict, gt_code_dir: Path, gt_step_dir: Path):
    from bench.metrics import compute_iou

    fam = entry["family"]
    param = entry["param"]
    old_v = float(entry["value"])
    orig_path = BASE / entry["orig_path"]
    if not orig_path.exists():
        return {"family": fam, "ok": False, "err": "orig missing"}

    pct = pct_for(param)
    new_v = round(old_v * (1 + pct / 100), 4)

    orig_text = orig_path.read_text()
    gt_text, ok, err = apply_edit(orig_text, param, old_v, new_v)
    if not ok:
        return {"family": fam, "ok": False, "err": err}

    gt_code_path = gt_code_dir / f"{fam}_gt.py"
    gt_code_path.write_text(gt_text)

    gt_step_path = gt_step_dir / f"{fam}_gt.step"
    exec_ok, exec_err = exec_cq(gt_text, gt_step_path)
    if not exec_ok:
        return {
            "family": fam,
            "ok": False,
            "err": f"exec fail: {exec_err}",
            "gt_code_path": str(gt_code_path.relative_to(BASE)),
        }

    # Locate the ORIG step path for this family+difficulty
    orig_step = orig_path.with_name(orig_path.name.replace("_orig.py", "_orig.step"))
    orig_step = orig_step.parent.parent / "steps" / orig_step.name
    if not orig_step.exists():
        return {"family": fam, "ok": False, "err": "orig step missing"}

    iou, iou_err = compute_iou(str(orig_step), str(gt_step_path))
    return {
        "family": fam,
        "difficulty": entry["difficulty"],
        "param": param,
        "orig_value": old_v,
        "target_value": new_v,
        "pct_delta": pct,
        "human_name": human_name_for(param),
        "orig_line": entry["line"],
        "orig_code_path": str(orig_path.relative_to(BASE)),
        "gt_code_path": str(gt_code_path.relative_to(BASE)),
        "orig_step_path": str(orig_step.relative_to(BASE)),
        "gt_step_path": str(gt_step_path.relative_to(BASE)),
        "iou_orig_gt": round(iou, 4),
        "iou_err": iou_err,
        "ok": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=str(PLAN))
    ap.add_argument("--family", default=None, help="only process this family")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    if args.family:
        plan = [e for e in plan if e["family"] == args.family]
    if args.limit:
        plan = plan[: args.limit]

    gt_code_dir = BASE / "curated_gt_codes"
    gt_step_dir = BASE / "curated_gt_steps"
    gt_code_dir.mkdir(exist_ok=True)
    gt_step_dir.mkdir(exist_ok=True)

    results = []
    for i, entry in enumerate(plan):
        fam = entry["family"]
        if args.dry_run:
            new_v = round(entry["value"] * (1 + pct_for(entry["param"]) / 100), 4)
            print(
                f"{i+1:3d}/{len(plan)}  {fam:28s}  {entry['param']:22s} "
                f"{entry['value']:.4g} → {new_v:.4g}"
            )
            continue
        r = process_entry(entry, gt_code_dir, gt_step_dir)
        results.append(r)
        status = "OK " if r["ok"] else "FAIL"
        iou = r.get("iou_orig_gt", "-")
        extra = r.get("err", "") if not r["ok"] else f"iou={iou}"
        print(
            f"[{i+1:3d}/{len(plan)}] {status} {fam:28s} "
            f"{entry['param']:22s} {extra}",
            flush=True,
        )

    if not args.dry_run:
        out_path = BASE / "curate_raw_results.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"\nwrote {out_path}")
        n_ok = sum(1 for r in results if r["ok"])
        n_iou_bad = sum(
            1 for r in results if r["ok"] and r.get("iou_orig_gt", 0) >= 0.99
        )
        print(f"  ok={n_ok}/{len(results)}, iou>=0.99 (too similar)={n_iou_bad}")


if __name__ == "__main__":
    main()
