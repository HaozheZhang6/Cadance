"""One-shot subprocess render: cq path → 4-view composite PNG.

Used by render_eval_codes.py via subprocess.run(timeout=N) for hard-timeout
isolation. VTK on macOS is single-threaded per process; running each render
in its own subprocess avoids Cocoa main-thread issues + lets parent SIGKILL
on timeout.

Args: cq_path  out_png  tmp_dir
"""

from __future__ import annotations

import sys
from pathlib import Path

_PRELUDE = """\
import cadquery as cq
try:
    import OCP.TopoDS as _td
    for _cls in (_td.TopoDS_Shape, _td.TopoDS_Face, _td.TopoDS_Edge, _td.TopoDS_Vertex,
                 _td.TopoDS_Wire, _td.TopoDS_Shell, _td.TopoDS_Solid,
                 _td.TopoDS_Compound, _td.TopoDS_CompSolid):
        if not hasattr(_cls, 'HashCode'):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
except Exception:
    pass
show_object = lambda *a, **kw: None
"""


def main() -> int:
    if len(sys.argv) != 4:
        sys.stderr.write("usage: _render_subproc.py <cq_path> <out_png> <tmp_dir>\n")
        return 2

    cq_path = Path(sys.argv[1])
    out_png = Path(sys.argv[2])
    tmp_dir = Path(sys.argv[3])
    tmp_dir.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "scripts" / "data_generation" / "ui"))
    from render import render_cq

    body = cq_path.read_text()
    if "import cadquery" not in body:
        body = _PRELUDE + body
    patched = tmp_dir / cq_path.name
    patched.write_text(body)

    comp_path, err = render_cq(str(patched), str(tmp_dir))
    patched.unlink(missing_ok=True)

    if comp_path and Path(comp_path).exists():
        out_png.parent.mkdir(parents=True, exist_ok=True)
        Path(comp_path).rename(out_png)
        return 0
    sys.stderr.write((err or "no composite")[:300])
    return 1


if __name__ == "__main__":
    sys.exit(main())
