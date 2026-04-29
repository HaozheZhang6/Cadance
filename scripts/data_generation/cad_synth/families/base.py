"""Base interface for parametric CadQuery part families."""

import math
from abc import ABC, abstractmethod

from ..pipeline.builder import Program, build_from_program, render_program_to_code

# Float-valued dimension keys that may be scaled by a uniform factor.
# Excludes ints (counts), enums, bools, and discrete ISO sizes.
_SCALABLE_EXACT = {
    "length",
    "width",
    "height",
    "depth",
    "thickness",
    "radius",
    "diameter",
    "chamfer",
    "fillet",
    "edge_size",
    "pitch",
}
_SCALABLE_SUFFIXES = (
    "_length",
    "_width",
    "_height",
    "_depth",
    "_thickness",
    "_radius",
    "_diameter",
)


def _is_scalable(key: str, value) -> bool:
    if isinstance(value, bool) or not isinstance(value, float):
        return False
    if key in _SCALABLE_EXACT:
        return True
    return any(key.endswith(s) for s in _SCALABLE_SUFFIXES)


def scale_params(params: dict, rng, lo: float = 0.8, hi: float = 1.2) -> dict:
    """Multiply whitelisted float dim keys by ONE uniform[lo, hi] factor (per call).

    Single factor preserves relative proportions (e.g. radius < width/2 stays
    valid). Per-key sampling broke geometric constraints. Caller must re-validate.
    """
    factor = float(rng.uniform(lo, hi))
    out = dict(params)
    for k, v in params.items():
        if _is_scalable(k, v):
            out[k] = round(v * factor, 2)
    return out


# DIN 6885A Form A — (bore_d_min, bore_d_max, key_width_b, key_height_h) mm
_DIN6885A_KEYWAY = [
    (6, 8, 2, 2),
    (8, 10, 3, 3),
    (10, 12, 4, 4),
    (12, 17, 5, 5),
    (17, 22, 6, 6),
    (22, 30, 8, 7),
    (30, 38, 10, 8),
    (38, 44, 12, 8),
    (44, 50, 14, 9),
    (50, 58, 16, 10),
    (58, 65, 18, 11),
    (65, 75, 20, 12),
    (75, 85, 22, 14),
    (85, 95, 25, 14),
    (95, 110, 28, 16),
    (110, 130, 32, 18),
]


def din6885a_keyway(bore_d: float) -> tuple[float, float]:
    """Return (key_width_b, shaft_seat_depth_t1) for bore_d per DIN 6885A."""
    for d_min, d_max, b, h in _DIN6885A_KEYWAY:
        if d_min <= bore_d < d_max:
            return float(b), round(h / 2.0, 1)
    # Outside table range: proportional fallback
    b = round(bore_d * 0.25, 0)
    return b, round(b * 0.5, 1)


def iso606_sprocket_profile(
    num_teeth: int, pitch: float, roller_diam: float, n_arc_pts: int = 8
) -> list[tuple[float, float]]:
    """Continuous CCW polyline of an ISO 606 roller-chain sprocket outline.

    Each tooth gap = circular root seating arc + straight tooth flank +
    tip-circle midpoint. Adjacent gaps share their tip midpoint, giving a
    single closed wire — extrude in one shot to avoid boolean-cut crashes.

    Reference: ISO 606:2015 §8.2 (tooth form), DIN 8187:1996.
    """
    dp = pitch / math.sin(math.pi / num_teeth)
    do = dp + 0.6 * roller_diam
    ri = 0.505 * roller_diam
    beta_half = math.radians(140 - 90 / num_teeth) / 2

    pts: list[tuple[float, float]] = []
    for i in range(num_teeth):
        base = i * (2 * math.pi / num_teeth)
        cos_g = math.cos(base)
        sin_g = math.sin(base)

        right_half: list[tuple[float, float]] = []
        for j in range(n_arc_pts):
            alpha = math.pi - (j / (n_arc_pts - 1)) * beta_half
            right_half.append((dp / 2 + ri * math.cos(alpha), ri * math.sin(alpha)))

        x_re, y_re = right_half[-1]
        theta_re = math.atan2(y_re, x_re)
        delta = 0.2 * pitch / do
        theta_tip = max((math.pi / num_teeth) - delta, theta_re + 0.01)
        right_half.append(
            ((do / 2) * math.cos(theta_tip), (do / 2) * math.sin(theta_tip))
        )
        right_half.append(
            (
                (do / 2) * math.cos(math.pi / num_teeth),
                (do / 2) * math.sin(math.pi / num_teeth),
            )
        )

        left_half = [(x, -y) for x, y in reversed(right_half)]
        gap_pts = left_half[:-1] + right_half

        for x, y in gap_pts[:-1]:
            rx = x * cos_g - y * sin_g
            ry = x * sin_g + y * cos_g
            pts.append((round(rx, 4), round(ry, 4)))

    return pts


class BaseFamily(ABC):
    """Base interface for all parametric CadQuery part families."""

    name: str = ""
    standard: str = "N/A"  # ISO/DIN/ASME standard, e.g. "DIN 950", "ISO 4032"

    @abstractmethod
    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample a valid parameter dict for the requested difficulty."""
        raise NotImplementedError

    @abstractmethod
    def validate_params(self, params: dict) -> bool:
        """Return True if params satisfy all hard constraints."""
        raise NotImplementedError

    @abstractmethod
    def make_program(self, params: dict) -> Program:
        """Return the structured build plan. Single source of truth."""
        raise NotImplementedError

    def build(self, params: dict):
        """Build CadQuery object by executing the structured program."""
        prog = self.make_program(params)
        prog.base_plane = params.get("base_plane", "XY")
        return build_from_program(prog)

    def export_code(self, params: dict) -> str:
        """Render executable CadQuery source from the structured program."""
        prog = self.make_program(params)
        prog.base_plane = params.get("base_plane", "XY")
        return render_program_to_code(prog)

    def compute_tags(self, params: dict) -> dict:
        """Return metadata tags (delegates to make_program)."""
        return self.make_program(params).feature_tags
