"""Render a CadQuery code file to normalized multi-view PNGs.

Usage:
  uv run python scripts/data_generation/render_cq_file.py \
    --code path/to/code.py \
    --out tmp/rendered \
    --size 512
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LD = "/workspace/.local/lib"
HASHCODE_PATCH = """
from OCP.TopoDS import (TopoDS_Shape, TopoDS_Face, TopoDS_Edge,
                        TopoDS_Vertex, TopoDS_Wire, TopoDS_Shell,
                        TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid)
for _cls in [TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
             TopoDS_Wire, TopoDS_Shell, TopoDS_Solid,
             TopoDS_Compound, TopoDS_CompSolid]:
    if not hasattr(_cls, "HashCode"):
        _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
"""


def _patch_export(code: str, out_step: str) -> str:
    code = re.sub(r"^\s*show_object\s*\(.*?\)\s*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"^\s*show\s*\(.*?\)\s*$", "", code, flags=re.MULTILINE)
    patched_body = re.sub(
        r'(\.exportStep\s*\()["\'].*?["\']\)',
        f'.exportStep("{out_step}")',
        code,
    )
    if ".exportStep" not in patched_body:
        patched_body += f'\nresult.val().exportStep("{out_step}")\n'
    return HASHCODE_PATCH + "\n" + patched_body


def run_cq(code_path: Path, timeout: int) -> tuple[Path | None, str | None]:
    code = code_path.read_text()
    step_tmp = Path(tempfile.mktemp(suffix=".step"))
    patched = _patch_export(code, str(step_tmp))

    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    try:
        r = subprocess.run(
            [sys.executable, "-c", patched],
            env=env,
            timeout=timeout,
            capture_output=True,
            cwd=str(ROOT),
            text=True,
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"

    if r.returncode != 0 or not step_tmp.exists():
        return None, (r.stderr or r.stdout or "render failed")[:2000]
    return step_tmp, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Run CadQuery code and render normalized views")
    ap.add_argument("--code", required=True, help="Path to CadQuery Python file")
    ap.add_argument("--out", required=True, help="Output directory for rendered images")
    ap.add_argument("--size", type=int, default=512, help="Per-view render size")
    ap.add_argument("--timeout", type=int, default=90, help="Execution timeout in seconds")
    ap.add_argument("--keep-step", action="store_true", help="Keep exported STEP in output dir")
    args = ap.parse_args()

    code_path = Path(args.code).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    step_path, err = run_cq(code_path, timeout=args.timeout)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))
    from render_normalized_views import render_step_normalized

    paths = render_step_normalized(str(step_path), str(out_dir), size=args.size)

    final_step = out_dir / f"{code_path.stem}.step"
    if args.keep_step:
        shutil.copy2(step_path, final_step)
        step_path.unlink(missing_ok=True)
    else:
        step_path.unlink(missing_ok=True)

    print(f"code: {code_path}")
    if args.keep_step:
        print(f"step: {final_step}")
    print(f"composite: {paths['composite']}")
    for i in range(4):
        print(f"view_{i}: {paths[f'view_{i}']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
