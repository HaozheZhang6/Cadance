"""Base interface for parametric CadQuery part families."""

from abc import ABC, abstractmethod

from ..pipeline.builder import Program, build_from_program, render_program_to_code

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
