"""Base interface for parametric CadQuery part families."""

from abc import ABC, abstractmethod

from ..pipeline.builder import Program, build_from_program, render_program_to_code


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
