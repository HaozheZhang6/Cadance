"""Unit tests for CadQuery executor geometry extraction logic."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

cq = pytest.importorskip("cadquery", reason="CadQuery not installed")

# Load executor module directly from tools/cadquery/executor.py
# without relying on package structure (it's a standalone script)
# Path: test_executor.py -> test_cadquery -> test_tools -> tests -> cadance
_EXECUTOR_PATH = (
    Path(__file__).resolve().parents[3] / "tools" / "cadquery" / "executor.py"
)
_spec = importlib.util.spec_from_file_location("executor", _EXECUTOR_PATH)
_executor = importlib.util.module_from_spec(_spec)
sys.modules["executor"] = _executor
_spec.loader.exec_module(_executor)

extract_geometry_props = _executor.extract_geometry_props
execute_code = _executor.execute_code


def make_box(x: float, y: float, z: float):
    """Create a simple box workplane for testing."""
    return cq.Workplane("XY").box(x, y, z)


class TestExtractGeometryProps:
    """Tests for extract_geometry_props function."""

    def test_volume_extraction(self):
        """extract_geometry_props returns correct volume for box."""
        workplane = make_box(10, 20, 30)
        props = extract_geometry_props(workplane)

        # 10 * 20 * 30 = 6000
        assert props["volume"] == 6000.0

    def test_face_count(self):
        """extract_geometry_props returns correct face count for box."""
        workplane = make_box(10, 20, 30)
        props = extract_geometry_props(workplane)

        # Box has 6 faces
        assert props["face_count"] == 6

    def test_edge_count(self):
        """extract_geometry_props returns correct edge count for box."""
        workplane = make_box(10, 20, 30)
        props = extract_geometry_props(workplane)

        # Box has 12 edges
        assert props["edge_count"] == 12

    def test_vertex_count(self):
        """extract_geometry_props returns correct vertex count for box."""
        workplane = make_box(10, 20, 30)
        props = extract_geometry_props(workplane)

        # Box has 8 vertices
        assert props["vertex_count"] == 8

    def test_bounding_box(self):
        """extract_geometry_props returns correct bounding box dimensions."""
        workplane = make_box(10, 20, 30)
        props = extract_geometry_props(workplane)

        bb = props["bounding_box"]
        assert bb["xlen"] == 10.0
        assert bb["ylen"] == 20.0
        assert bb["zlen"] == 30.0

    def test_rounding(self):
        """extract_geometry_props rounds floats to 2 decimal places."""
        # Use dimensions that may produce floating point artifacts
        workplane = cq.Workplane("XY").sphere(1.5)
        props = extract_geometry_props(workplane)

        # Check that volume is rounded (sphere vol = 4/3 * pi * r^3)
        # For r=1.5: ~14.137
        assert isinstance(props["volume"], float)
        # Verify it's rounded (2 decimal places means no more precision)
        assert props["volume"] == round(props["volume"], 2)


class TestExecuteCode:
    """Tests for execute_code function error handling."""

    def test_syntax_error_returns_syntax_category(self):
        """Syntax errors return error_category='syntax'."""
        result = execute_code("def broken(")

        assert result["success"] is False
        assert result["error_category"] == "syntax"
        assert "SyntaxError" in result["error_message"]

    def test_missing_result_returns_validation_category(self):
        """Missing 'result' variable returns error_category='validation'."""
        result = execute_code("x = 1 + 1")

        assert result["success"] is False
        assert result["error_category"] == "validation"
        assert "result" in result["error_message"]

    def test_runtime_error_returns_crash_category(self):
        """Runtime errors return error_category='crash'."""
        result = execute_code("result = 1 / 0")

        assert result["success"] is False
        assert result["error_category"] == "crash"
        assert "ZeroDivisionError" in result["error_message"]

    def test_successful_execution(self):
        """Valid code returns success with geometry props."""
        code = "result = cq.Workplane('XY').box(10, 20, 30)"
        result = execute_code(code)

        assert result["success"] is True
        assert result["error_category"] == "none"
        assert result["geometry_props"]["volume"] == 6000.0
        assert result["execution_time_ms"] > 0
