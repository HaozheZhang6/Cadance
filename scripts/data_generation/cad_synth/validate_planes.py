"""
Validate plane augmentation: same params on XY/YZ/XZ → IoU after analytical alignment.

Analytical rotations (derived from CadQuery workplane coordinate systems):
  YZ→XY: box(L,W,H) on YZ puts L on world-Y, W on world-Z, H on world-X.
          To align to XY (L→X, W→Y, H→Z): rotate (x,y,z)→(y,z,x)
          R_YZ = [[0,1,0],[0,0,1],[1,0,0]]

  XZ→XY: box(L,W,H) on XZ puts L on world-X, W on world-(-Z), H on world-Y.
          To align to XY: rotate (x,y,z)→(x,-z,y)
          R_XZ = [[1,0,0],[0,0,-1],[0,1,0]]

Pass threshold: IoU >= 0.85 (voxel rasterisation noise at 24³).
"""

import sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "data_generation"))

DIFFS      = ["easy", "medium", "hard"]
N_TRIALS   = 5        # seeds tried to find valid params
RESOLUTION = 24       # voxel grid
PASS_THR   = 0.85
XY_ONLY    = {"pipe_elbow"}

# Analytical alignment transforms
# YZ→XY: box(L,W,H) on YZ gives world (H,L,W); on XY gives (L,W,H)
#         proper rotation (det=+1): (x,y,z)→(y,z,x)
R_YZ = np.array([[0,1,0],[0,0,1],[1,0,0]], dtype=float)

# XZ→XY: box(L,W,H) on XZ gives world (L,H,W); on XY gives (L,W,H)
#         requires y↔z swap → reflection (det=-1), fine for shape equivalence check
R_XZ_reflect = np.array([[1,0,0],[0,0,1],[0,1,0]], dtype=float)  # (x,y,z)→(x,z,y)
# Also try proper rotations for symmetric shapes
R_XZ_rx90  = np.array([[1,0,0],[0,0,-1],[0,1,0]], dtype=float)   # (x,y,z)→(x,-z,y)
R_XZ_rx270 = np.array([[1,0,0],[0,0,1],[0,-1,0]], dtype=float)   # (x,y,z)→(x,z,-y)

PLANE_ROTS = {
    "YZ": [R_YZ, R_YZ.T],
    "XZ": [R_XZ_reflect, R_XZ_rx90, R_XZ_rx270, R_XZ_reflect.T],
}


# ---------------------------------------------------------------------------
# Voxel helpers
# ---------------------------------------------------------------------------
def _wp_to_voxels(wp) -> np.ndarray | None:
    import trimesh
    try:
        verts, tris = wp.val().tessellate(0.1, 0.1)
        v = np.array([(p.x, p.y, p.z) for p in verts], dtype=np.float64)
        f = np.array(tris, dtype=np.int64)
    except Exception:
        return None
    if len(v) == 0 or len(f) == 0:
        return None
    mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
    lo, hi = mesh.bounds
    scale = (hi - lo).max()
    if scale < 1e-6:
        return None
    mesh.vertices = (mesh.vertices - (lo + hi) / 2.0) / scale
    pitch  = 1.2 / RESOLUTION
    origin = np.full(3, -0.6)
    try:
        vox = mesh.voxelized(pitch=pitch).fill()
    except Exception:
        return None
    dense = np.zeros((RESOLUTION,) * 3, dtype=bool)
    idx = np.round((vox.points - origin) / pitch).astype(int)
    valid = np.all((idx >= 0) & (idx < RESOLUTION), axis=1)
    idx = idx[valid]
    if len(idx):
        dense[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return dense


def _rotate_grid(grid: np.ndarray, R: np.ndarray) -> np.ndarray:
    n = grid.shape[0]
    idx = np.argwhere(grid)
    if len(idx) == 0:
        return np.zeros_like(grid)
    pts   = (idx.astype(float) + 0.5) / n - 0.5   # centres in [-0.5,0.5]
    pts_r = pts @ R.T
    idx_r = np.floor((pts_r + 0.5) * n).astype(int)
    new   = np.zeros_like(grid)
    valid = np.all((idx_r >= 0) & (idx_r < n), axis=1)
    idx_r = idx_r[valid]
    if len(idx_r):
        new[idx_r[:, 0], idx_r[:, 1], idx_r[:, 2]] = True
    return new


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = int((a & b).sum())
    union = int((a | b).sum())
    return inter / union if union > 0 else 0.0


def _best_iou(ref: np.ndarray, other: np.ndarray, rots) -> float:
    return max(_iou(ref, _rotate_grid(other, R)) for R in rots)


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------
def _build(fam, params, plane):
    from scripts.data_generation.cad_synth.pipeline.builder import build_from_program
    p = {**params, "base_plane": plane}
    prog = fam.make_program(p)
    prog.base_plane = plane
    return build_from_program(prog)


def _sample_valid(fam, diff):
    for trial in range(N_TRIALS):
        seed = hash((fam.name, diff, trial)) & 0xFFFFFFFF
        rng  = np.random.default_rng(seed)
        try:
            p = fam.sample_params(diff, rng)
            if fam.validate_params(p):
                return p
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    from scripts.data_generation.cad_synth.pipeline.registry import list_families, get_family

    families = sorted(list_families())
    print(f"Validating {len(families)} families | res={RESOLUTION}³ | threshold={PASS_THR}", flush=True)
    print(f"{'Family':<28} {'Plane':<5} {'easy':>6} {'med':>6} {'hard':>6}  status", flush=True)
    print("-" * 65, flush=True)

    all_pass, fail, skip = [], [], []

    for fam_name in families:
        if fam_name in XY_ONLY:
            print(f"{fam_name:<28} XY-only (skip)", flush=True)
            skip.append(fam_name)
            continue

        fam = get_family(fam_name)
        fam_ok = True

        for plane in ["YZ", "XZ"]:
            rots = PLANE_ROTS[plane]
            cells, plane_ok = [], True

            for diff in DIFFS:
                params = _sample_valid(fam, diff)
                if params is None:
                    cells.append("  N/A")
                    continue

                try:
                    wp_xy = _build(fam, params, "XY")
                    ref   = _wp_to_voxels(wp_xy)
                except Exception:
                    ref = None

                if ref is None or ref.sum() == 0:
                    cells.append(" ERR")
                    plane_ok = False
                    continue

                try:
                    wp_t = _build(fam, params, plane)
                    tgt  = _wp_to_voxels(wp_t)
                except Exception:
                    tgt = None

                if tgt is None or tgt.sum() == 0:
                    cells.append(" 0.00")
                    plane_ok = False
                    continue

                iou = _best_iou(ref, tgt, rots)
                cells.append(f"{iou:.3f}")
                if iou < PASS_THR:
                    plane_ok = False

            status = "✓" if plane_ok else "✗"
            if not plane_ok:
                fam_ok = False
            print(f"{fam_name:<28} {plane:<5} {cells[0]:>6} {cells[1]:>6} {cells[2]:>6}  {status}", flush=True)

        (all_pass if fam_ok else fail).append(fam_name)

    print("\n" + "=" * 65, flush=True)
    print(f"PASS ({len(all_pass)}): {all_pass}")
    print(f"FAIL ({len(fail)}): {fail}")
    print(f"SKIP ({len(skip)}): {skip}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"\nTotal: {time.time()-t0:.1f}s")
