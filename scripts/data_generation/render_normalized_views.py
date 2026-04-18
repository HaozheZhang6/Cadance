"""
Normalized multi-view renderer for STEP files.

Matches reference render_img() from Cadrille RL training:
  Normalization: bbox center → [0.5,0.5,0.5], longest axis → [0,1]³
  Camera lookat: [0.5, 0.5, 0.5]
  Camera eye:    lookat + front_unnormalized * -0.9
  Fronts: [1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1]
  Per-view: 128×128 + 3px black border = 134×134
  Composite: 2×2 → 268×268
  Color: [255,255,136]/255 (yellowish)

Usage:
  python render_normalized_views.py --step part.step --out /tmp/views/
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np

CAMERA_FRONTS = [[1, 1, 1], [-1, -1, -1], [-1, 1, -1], [1, -1, 1]]
CAMERA_DISTANCE = -0.9   # applied to unnormalized front vector
IMG_SIZE = 128            # per-view size before border
BORDER = 3                # black border → final per-view 134×134, composite 268×268
LOOKAT = np.array([0.5, 0.5, 0.5], dtype=np.float64)
MESH_COLOR = np.array([255, 255, 136]) / 255.0
EDGE_COLOR = (0.12, 0.12, 0.12)
EDGE_LINE_WIDTH = 1.6


# ── VTK renderer (matches reference camera spec) ──────────────────────────────

def _mesh_to_image_vtk(verts, tris, front, img_size=IMG_SIZE):
    """Render one view via VTK OffscreenRenderer."""
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk

    front_arr = np.array(front, dtype=np.float64)
    up = np.array([0.0, 1.0, 0.0])

    eye = LOOKAT + front_arr * CAMERA_DISTANCE

    # Build true_up orthogonal to both front and right
    right = np.cross(up, front_arr)
    right /= np.linalg.norm(right)
    true_up = np.cross(front_arr, right)

    # Build VTK mesh
    points = vtk.vtkPoints()
    points.SetData(numpy_to_vtk(verts.astype(np.float64), deep=True))

    cells = vtk.vtkCellArray()
    for tri in tris:
        cells.InsertNextCell(3)
        for idx in tri:
            cells.InsertCellPoint(int(idx))

    pd = vtk.vtkPolyData()
    pd.SetPoints(points)
    pd.SetPolys(cells)

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.ComputePointNormalsOn()
    normals.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(*MESH_COLOR)
    prop.SetAmbient(0.3)
    prop.SetDiffuse(0.7)

    # Overlay visible mesh edges so silhouettes and sharp feature breaks read
    # more clearly in the normalized renders.
    edges = vtk.vtkFeatureEdges()
    edges.SetInputConnection(normals.GetOutputPort())
    edges.BoundaryEdgesOn()
    edges.FeatureEdgesOn()
    edges.ManifoldEdgesOff()
    edges.NonManifoldEdgesOn()
    edges.SetFeatureAngle(35.0)

    edge_mapper = vtk.vtkPolyDataMapper()
    edge_mapper.SetInputConnection(edges.GetOutputPort())

    edge_actor = vtk.vtkActor()
    edge_actor.SetMapper(edge_mapper)
    edge_prop = edge_actor.GetProperty()
    edge_prop.SetColor(*EDGE_COLOR)
    edge_prop.SetLineWidth(EDGE_LINE_WIDTH)
    edge_prop.SetRepresentationToWireframe()
    edge_prop.LightingOff()

    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.AddActor(edge_actor)
    renderer.SetBackground(1.0, 1.0, 1.0)  # white bg, will be cropped by open3d ref too

    cam = renderer.GetActiveCamera()
    cam.SetPosition(*eye.tolist())
    cam.SetFocalPoint(*LOOKAT.tolist())
    cam.SetViewUp(*true_up.tolist())
    cam.SetViewAngle(60.0)

    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.AddRenderer(renderer)
    render_window.SetSize(img_size * 4, img_size * 4)  # render bigger, then resize
    render_window.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(render_window)
    w2i.Update()

    import vtk.util.numpy_support as nps
    img_data = w2i.GetOutput()
    dims = img_data.GetDimensions()
    arr = nps.vtk_to_numpy(img_data.GetPointData().GetScalars())
    arr = arr.reshape(dims[1], dims[0], -1)[::-1]  # flip Y
    arr = arr[:, :, :3].astype(np.uint8)

    # Resize to img_size×img_size
    from PIL import Image
    img_pil = Image.fromarray(arr)
    img_pil = img_pil.resize((img_size, img_size), Image.LANCZOS)
    return np.array(img_pil)


def _step_to_mesh(step_path: str, linear_deflection: float = 0.05):
    """Load STEP → tessellate → normalize to [0,1]³ → (verts, tris).

    Falls back to mesh.stl (same dir) if OCC tessellation fails.
    """
    import cadquery as cq
    from pathlib import Path as _Path
    from OCP.TopoDS import (TopoDS_Shape, TopoDS_Face, TopoDS_Edge,
                             TopoDS_Vertex, TopoDS_Wire, TopoDS_Shell,
                             TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid)
    for _cls in [TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
                 TopoDS_Wire, TopoDS_Shell, TopoDS_Solid,
                 TopoDS_Compound, TopoDS_CompSolid]:
        if not hasattr(_cls, "HashCode"):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub

    def _try_tessellate():
        shape = cq.importers.importStep(str(step_path))
        solid = shape.val()
        if solid is None:
            solids = shape.solids().vals()
            if not solids:
                raise ValueError(f"No solids found in {step_path}")
            solid = solids[0]
        return solid.tessellate(linear_deflection)

    try:
        verts_raw, tris_raw = _try_tessellate()
    except Exception:
        # Fall back to mesh.stl in same directory
        stl_path = _Path(step_path).with_name("mesh.stl")
        if not stl_path.exists():
            raise ValueError(f"Tessellation failed and no mesh.stl found at {stl_path}")
        import trimesh as _trimesh
        m = _trimesh.load(str(stl_path), force="mesh")
        verts = np.array(m.vertices, dtype=np.float64)
        tris = np.array(m.faces, dtype=np.int64)
        if len(verts) == 0 or len(tris) == 0:
            raise ValueError(f"Empty mesh in {stl_path}")
        bb_min, bb_max = verts.min(axis=0), verts.max(axis=0)
        center = (bb_min + bb_max) / 2.0
        longest = (bb_max - bb_min).max()
        verts = (verts - center) / longest + 0.5
        return verts, tris

    verts = np.array([[v.x, v.y, v.z] for v in verts_raw], dtype=np.float64)
    tris  = np.array([[t[0], t[1], t[2]] for t in tris_raw], dtype=np.int64)

    if len(verts) == 0 or len(tris) == 0:
        raise ValueError(f"Empty tessellation for {step_path}")

    # Normalize: center → [0.5,0.5,0.5], longest axis → [0,1]³
    bb_min, bb_max = verts.min(axis=0), verts.max(axis=0)
    center = (bb_min + bb_max) / 2.0
    longest = (bb_max - bb_min).max()
    verts = (verts - center) / longest + 0.5  # → [0,1]³

    return verts, tris


# ── public API ────────────────────────────────────────────────────────────────

def render_step_normalized(
    step_path: str,
    out_dir: str,
    size: int = IMG_SIZE,
    prefix: str = "",
    linear_deflection: float = 0.05,
) -> dict:
    """
    Render a STEP file to a 4-view composite PNG matching Cadrille reference.

    Returns dict with keys: composite, view_0, view_1, view_2, view_3
    """
    from PIL import Image, ImageOps

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    verts, tris = _step_to_mesh(step_path, linear_deflection)

    imgs = []
    for front in CAMERA_FRONTS:
        arr = _mesh_to_image_vtk(verts, tris, front, img_size=size)
        img = ImageOps.expand(Image.fromarray(arr), border=BORDER, fill="black")
        imgs.append(img)

    composite = Image.fromarray(np.vstack((
        np.hstack((np.array(imgs[0]), np.array(imgs[1]))),
        np.hstack((np.array(imgs[2]), np.array(imgs[3]))),
    )))

    paths = {}
    for i, img in enumerate(imgs):
        p = out_dir / f"{prefix}view_{i}.png"
        img.save(str(p))
        paths[f"view_{i}"] = str(p)

    cp = out_dir / f"{prefix}composite.png"
    composite.save(str(cp))
    paths["composite"] = str(cp)
    return paths


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Normalized STEP multi-view renderer")
    ap.add_argument("--step", required=True)
    ap.add_argument("--out",  required=True)
    ap.add_argument("--size", type=int, default=IMG_SIZE)
    ap.add_argument("--prefix", default="")
    args = ap.parse_args()
    paths = render_step_normalized(args.step, args.out, size=args.size, prefix=args.prefix)
    print(f"composite: {paths['composite']}")


if __name__ == "__main__":
    main()
