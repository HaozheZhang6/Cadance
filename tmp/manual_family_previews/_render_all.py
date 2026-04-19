"""Render each manual_*.step file as an isometric SVG preview."""
import os
import cadquery as cq
from OCP.TopoDS import (
    TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
    TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid,
)
for _cls in [TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
             TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid]:
    if not hasattr(_cls, "HashCode"):
        _cls.HashCode = lambda self, ub=2147483647: id(self) % ub

here = os.path.dirname(__file__)
opts = {"showAxes": False, "width": 600, "height": 600, "projectionDir": (1.5, 1.0, 1.0)}

for name in sorted(os.listdir(here)):
    if not name.endswith(".step") or not name.startswith("manual_"):
        continue
    path = os.path.join(here, name)
    try:
        shape = cq.importers.importStep(path).val()
    except Exception as e:
        print(f"  SKIP {name}: {e}")
        continue
    svg = cq.exporters.getSVG(shape, opts)
    out_svg = path.replace(".step", ".svg")
    with open(out_svg, "w") as f:
        f.write(svg)
    print(f"  rendered {os.path.basename(out_svg)}")
