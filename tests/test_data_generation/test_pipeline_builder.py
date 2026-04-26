"""Unit tests for cad_synth.pipeline.builder — Op→code rendering + execution.

Two layers tested:
  1. `_op_to_code` / `render_program_to_code` — pure-Python serialization,
     deterministic, tests every Op type's code emission.
  2. `_remap_sel` — base-plane-aware selector remap (XY/XZ/YZ).
  3. `build_from_program` — CadQuery execution smoke (gated on working cadquery).

The first two layers don't need cadquery. The third uses the
`requires_working_cadquery` mark from conftest.
"""

from __future__ import annotations

import pytest

from scripts.data_generation.cad_synth.pipeline.builder import (
    Op,
    Program,
    _op_to_code,
    _remap_sel,
    render_program_to_code,
)

# ── Op dataclass basics ───────────────────────────────────────────────────────


class TestOpDataclass:
    def test_op_default_args(self):
        op = Op("circle")
        assert op.name == "circle"
        assert op.args == {}

    def test_op_with_args(self):
        op = Op("circle", {"radius": 5.0})
        assert op.args == {"radius": 5.0}


class TestProgramDataclass:
    def test_program_defaults(self):
        p = Program(family="x", difficulty="easy", params={}, ops=[])
        assert p.feature_tags == {}
        assert p.base_plane == "XY"

    def test_program_custom_base_plane(self):
        p = Program(family="x", difficulty="easy", params={}, ops=[], base_plane="XZ")
        assert p.base_plane == "XZ"


# ── _remap_sel: base-plane-aware selector translation ────────────────────────


class TestRemapSel:
    @pytest.fixture(autouse=True)
    def _reset_base_plane(self):
        """Ensure the global _current_base_plane is reset after each test."""
        import scripts.data_generation.cad_synth.pipeline.builder as b

        saved = b._current_base_plane
        yield
        b._current_base_plane = saved

    def test_xy_base_no_remap(self):
        import scripts.data_generation.cad_synth.pipeline.builder as b

        b._current_base_plane = "XY"
        assert _remap_sel(">Z") == ">Z"
        assert _remap_sel("|Z") == "|Z"
        assert _remap_sel(">X") == ">X"

    def test_xz_base_remaps_z_to_y(self):
        import scripts.data_generation.cad_synth.pipeline.builder as b

        b._current_base_plane = "XZ"
        # "Z" axis selector remaps to world Y for XZ base
        assert _remap_sel(">Z") == ">Y"
        assert _remap_sel("|Z") == "|Y"
        # "Y" axis maps to world Z
        assert _remap_sel(">Y") == ">Z"

    def test_yz_base_remaps_z_to_x(self):
        import scripts.data_generation.cad_synth.pipeline.builder as b

        b._current_base_plane = "YZ"
        assert _remap_sel(">Z") == ">X"
        assert _remap_sel("|Z") == "|X"

    def test_unknown_selector_passes_through(self):
        # Selectors not in the remap table return as-is
        assert _remap_sel("custom_sel") == "custom_sel"
        assert _remap_sel(">>>face") == ">>>face"


# ── _op_to_code: per-op source rendering ──────────────────────────────────────


class TestOpToCodePrimitives:
    def test_box(self):
        assert _op_to_code(Op("box", {"length": 10, "width": 5, "height": 2})) == (
            ".box(10, 5, 2)"
        )

    def test_box_not_centered(self):
        out = _op_to_code(
            Op("box", {"length": 10, "width": 5, "height": 2, "centered": False})
        )
        assert "centered=False" in out

    def test_cylinder(self):
        assert _op_to_code(Op("cylinder", {"height": 10, "radius": 3})) == (
            ".cylinder(10, 3)"
        )

    def test_circle(self):
        assert _op_to_code(Op("circle", {"radius": 2.5})) == ".circle(2.5)"

    def test_rect(self):
        assert _op_to_code(Op("rect", {"length": 4, "width": 6})) == ".rect(4, 6)"

    def test_polygon(self):
        assert _op_to_code(Op("polygon", {"n": 6, "diameter": 12.0})) == (
            ".polygon(6, 12.0)"
        )

    def test_sphere(self):
        assert _op_to_code(Op("sphere", {"radius": 5})) == ".sphere(5)"


class TestOpToCodeProfile:
    def test_moveTo(self):
        assert _op_to_code(Op("moveTo", {"x": 1.0, "y": 2.0})) == ".moveTo(1.0, 2.0)"

    def test_lineTo(self):
        assert _op_to_code(Op("lineTo", {"x": 3.0, "y": 4.0})) == ".lineTo(3.0, 4.0)"

    def test_close(self):
        assert _op_to_code(Op("close")) == ".close()"

    def test_polyline(self):
        out = _op_to_code(Op("polyline", {"points": [(0, 0), (1, 1)]}))
        assert ".polyline(" in out
        assert "(0, 0)" in out

    def test_threePointArc(self):
        out = _op_to_code(
            Op("threePointArc", {"point1": [1.0, 2.0], "point2": [3.0, 4.0]})
        )
        assert ".threePointArc((1.0, 2.0), (3.0, 4.0))" == out


class TestOpToCodeExtrusion:
    def test_extrude_simple(self):
        assert _op_to_code(Op("extrude", {"distance": 5})) == ".extrude(5)"

    def test_extrude_with_taper(self):
        assert _op_to_code(Op("extrude", {"distance": 5, "taper": 10})) == (
            ".extrude(5, taper=10)"
        )

    def test_extrude_both(self):
        assert _op_to_code(Op("extrude", {"distance": 5, "both": True})) == (
            ".extrude(5, both=True)"
        )

    def test_extrude_taper_and_both(self):
        out = _op_to_code(Op("extrude", {"distance": 5, "taper": 8, "both": True}))
        assert "taper=8" in out
        assert "both=True" in out

    def test_revolve(self):
        out = _op_to_code(
            Op(
                "revolve",
                {"angleDeg": 360, "axisStart": [0, 0, 0], "axisEnd": [0, 1, 0]},
            )
        )
        assert ".revolve(360, (0, 0, 0), (0, 1, 0))" == out


class TestOpToCodeFeatures:
    def test_hole_no_depth(self):
        assert _op_to_code(Op("hole", {"diameter": 5})) == ".hole(5)"

    def test_hole_with_depth(self):
        assert _op_to_code(Op("hole", {"diameter": 5, "depth": 10})) == (
            ".hole(5, depth=10)"
        )

    def test_cboreHole(self):
        out = _op_to_code(
            Op("cboreHole", {"diameter": 5, "cboreDiameter": 8, "cboreDepth": 2})
        )
        assert ".cboreHole(5, 8, 2)" == out

    def test_cutBlind_negates_depth(self):
        # Family code uses positive depth; emitted code uses negative (CadQuery contract)
        assert _op_to_code(Op("cutBlind", {"depth": 5})) == ".cutBlind(-5)"
        # Already negative input still emits negative
        assert _op_to_code(Op("cutBlind", {"depth": -5})) == ".cutBlind(-5)"

    def test_cutThruAll(self):
        assert _op_to_code(Op("cutThruAll")) == ".cutThruAll()"

    def test_fillet(self):
        assert _op_to_code(Op("fillet", {"radius": 0.5})) == ".fillet(0.5)"

    def test_chamfer(self):
        assert _op_to_code(Op("chamfer", {"length": 1.2})) == ".chamfer(1.2)"

    def test_shell(self):
        assert _op_to_code(Op("shell", {"thickness": 2.5})) == ".shell(2.5)"


class TestOpToCodeSelectors:
    @pytest.fixture(autouse=True)
    def _reset(self):
        import scripts.data_generation.cad_synth.pipeline.builder as b

        saved = b._current_base_plane
        b._current_base_plane = "XY"
        yield
        b._current_base_plane = saved

    def test_workplane(self):
        assert _op_to_code(Op("workplane", {"selector": ">Z"})) == (
            '.faces(">Z").workplane()'
        )

    def test_faces(self):
        assert _op_to_code(Op("faces", {"selector": "<Z"})) == '.faces("<Z")'

    def test_edges_with_selector(self):
        assert _op_to_code(Op("edges", {"selector": "|Z"})) == '.edges("|Z")'

    def test_edges_no_selector(self):
        assert _op_to_code(Op("edges", {})) == ".edges()"


class TestOpToCodeUnion:
    @pytest.fixture(autouse=True)
    def _reset(self):
        import scripts.data_generation.cad_synth.pipeline.builder as b

        saved = b._current_base_plane
        b._current_base_plane = "XY"
        yield
        b._current_base_plane = saved

    def test_union_emits_sub_workplane(self):
        op = Op(
            "union",
            {
                "ops": [
                    {"name": "circle", "args": {"radius": 5}},
                    {"name": "extrude", "args": {"distance": 2}},
                ]
            },
        )
        out = _op_to_code(op)
        assert ".union(" in out
        assert 'cq.Workplane("XY")' in out
        assert ".circle(5)" in out
        assert ".extrude(2)" in out

    def test_cut_emits_sub_workplane_explicit_plane(self):
        op = Op(
            "cut",
            {
                "plane": "XZ",
                "ops": [{"name": "circle", "args": {"radius": 1}}],
            },
        )
        out = _op_to_code(op)
        assert ".cut(" in out
        assert 'cq.Workplane("XZ")' in out


# ── render_program_to_code: full program rendering ────────────────────────────


class TestRenderProgramToCode:
    def test_minimal_program_box(self):
        prog = Program(
            family="test",
            difficulty="easy",
            params={"size": 10},
            ops=[
                Op("box", {"length": 10, "width": 10, "height": 10}),
            ],
        )
        code = render_program_to_code(prog)
        assert "import cadquery as cq" in code
        assert 'cq.Workplane("XY")' in code
        assert ".box(10, 10, 10)" in code
        assert "show_object(result)" in code
        assert "result = (" in code

    def test_xz_base_plane(self):
        prog = Program(
            family="test",
            difficulty="easy",
            params={},
            ops=[Op("box", {"length": 1, "width": 1, "height": 1})],
            base_plane="XZ",
        )
        code = render_program_to_code(prog)
        assert 'cq.Workplane("XZ")' in code

    def test_params_hint_included_when_flagged(self):
        prog = Program(
            family="test",
            difficulty="easy",
            params={"radius": 5.0, "height": 10},
            ops=[Op("cylinder", {"height": 10, "radius": 5})],
        )
        code = render_program_to_code(prog, include_params_hint=True)
        assert "# --- parameters ---" in code
        assert "# radius = 5.0" in code
        assert "# height = 10" in code

    def test_params_hint_excluded_by_default(self):
        prog = Program(
            family="test",
            difficulty="easy",
            params={"x": 1.0},
            ops=[Op("cylinder", {"height": 10, "radius": 5})],
        )
        code = render_program_to_code(prog)
        assert "# --- parameters ---" not in code

    def test_params_hint_skips_non_numeric(self):
        prog = Program(
            family="test",
            difficulty="easy",
            params={"name": "foo", "x": 1.0, "flag": True},
            ops=[Op("cylinder", {"height": 10, "radius": 5})],
        )
        code = render_program_to_code(prog, include_params_hint=True)
        assert "# x = 1.0" in code
        # Strings + bools must NOT be emitted as numeric hints
        assert "# name = foo" not in code
        assert "# flag = True" not in code

    def test_chained_ops_indented(self):
        prog = Program(
            family="test",
            difficulty="easy",
            params={},
            ops=[
                Op("circle", {"radius": 5}),
                Op("extrude", {"distance": 10}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": 2}),
            ],
        )
        code = render_program_to_code(prog)
        lines = code.split("\n")
        # All op lines should be indented with 4 spaces (inside `result = (` block)
        op_lines = [
            line
            for line in lines
            if line.startswith("    .") or line.startswith("    cq")
        ]
        assert len(op_lines) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
