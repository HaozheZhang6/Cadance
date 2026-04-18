"""Plane-aware coordinate helpers for multi-plane family code.

All families are built on one of three base planes: "XY", "XZ", "YZ".
Each plane has:
  - A normal/axial direction (the build/extrude direction)
  - Two lateral directions (in-plane)

CadQuery's `transformed(offset, rotate)` uses LOCAL workplane coordinates.
For all base planes, the local axes map to the same conceptual directions:
  local_x → first lateral axis
  local_y → second lateral axis
  local_z → axial (normal) axis

Because `transformed` is always in local coords, these helpers are
plane-independent: the same values work on XY, XZ, and YZ.

Coordinate mapping  (u=first_lateral, v=second_lateral, w=axial → world XYZ):
  XY:  u→X, v→Y, w→Z    (normal = Z)
  XZ:  u→X, v→Z, w→Y    (normal = Y)
  YZ:  u→Y, v→Z, w→X    (normal = X)

Face selectors for the axial direction:
  XY: >Z  <Z  |Z
  XZ: >Y  <Y  |Y
  YZ: >X  <X  |X
"""

# ---------------------------------------------------------------------------
# Axial face selectors
# ---------------------------------------------------------------------------

AXIAL_TOP = {"XY": ">Z", "XZ": ">Y", "YZ": ">X"}
AXIAL_BOT = {"XY": "<Z", "XZ": "<Y", "YZ": "<X"}
AXIAL_PAR = {"XY": "|Z", "XZ": "|Y", "YZ": "|X"}  # edges parallel to axis


def axial_top(base_plane: str) -> str:
    return AXIAL_TOP.get(base_plane, ">Z")


def axial_bot(base_plane: str) -> str:
    return AXIAL_BOT.get(base_plane, "<Z")


# ---------------------------------------------------------------------------
# Rotation around plane normal
# ---------------------------------------------------------------------------

def plane_rot(base_plane: str, angle: float) -> list:
    """Euler rotation [rx,ry,rz] to spin `angle` degrees around the plane normal.

    CadQuery's `transformed(rotate=...)` uses LOCAL workplane coordinates.
    The normal is always local_z, so in-plane rotation is always [0, 0, angle]
    regardless of base_plane.
    """
    return [0.0, 0.0, float(angle)]


# ---------------------------------------------------------------------------
# World-coordinate offset from plane-relative (u, v, w)
# ---------------------------------------------------------------------------

def plane_offset(base_plane: str, u: float, v: float, w: float) -> list:
    """Convert plane-relative (u, v, w) to a vector for `transformed(offset=...)`.

    u = displacement along first lateral axis
    v = displacement along second lateral axis
    w = displacement along normal (axial)

    CadQuery's `transformed(offset=...)` uses LOCAL workplane coordinates where
    local_x=first_lateral, local_y=second_lateral, local_z=axial for every plane.
    Therefore this function always returns [u, v, w] — plane-independent.
    """
    return [float(u), float(v), float(w)]


# ---------------------------------------------------------------------------
# Cylinder-axis rotation for sub-workplane cylinders
# ---------------------------------------------------------------------------
# Cylinders built on a sub-Workplane(_current_base_plane) have their axis
# along the plane normal (local_z) by default.  Use these rotations to tilt
# the axis to one of the in-plane directions instead.
#
# Since `transformed(rotate=...)` uses LOCAL workplane coordinates and the
# local axes are conceptually consistent across all planes, the rotations
# are plane-independent.

def cylinder_rot_to_lateral1(base_plane: str) -> list:
    """Rotate a base-plane cylinder so its axis aligns with the first lateral.

    Tilts local_z (normal/cylinder-axis) toward local_x (first lateral):
    rotate local_y by -90° → [0, -90, 0] for all base planes.
    """
    return [0.0, -90.0, 0.0]


def cylinder_rot_to_lateral2(base_plane: str) -> list:
    """Rotate a base-plane cylinder so its axis aligns with the second lateral.

    Tilts local_z (normal/cylinder-axis) toward local_y (second lateral):
    rotate local_x by -90° → [-90, 0, 0] for all base planes.
    """
    return [-90.0, 0.0, 0.0]
