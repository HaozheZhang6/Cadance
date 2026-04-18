"""Integration tests for CadQuery execution via gateway.

These tests require the CadQuery venv to be available.
Run with: pytest -m integration tests/test_tools/test_cadquery/test_integration.py

Skip integration tests with: pytest -m "not integration"
"""

import pytest


@pytest.mark.integration
class TestRealCadQueryExecution:
    """Integration tests using real SubprocessCadQueryBackend."""

    def test_simple_box_execution(self, real_gateway):
        """Real CadQuery execution produces geometry properties."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 5)
"""
        result = real_gateway.execute("cadquery", code)

        assert result.success is True
        assert result.geometry_props is not None
        assert result.geometry_props.get("volume") is not None
        # Box volume should be 10 * 20 * 5 = 1000
        assert abs(result.geometry_props["volume"] - 1000.0) < 1.0
        assert result.geometry_props.get("face_count") == 6

    def test_cylinder_execution(self, real_gateway):
        """Real cylinder execution."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").cylinder(10, 5)  # height=10, radius=5
"""
        result = real_gateway.execute("cadquery", code)

        assert result.success is True
        assert result.geometry_props.get("volume") is not None
        # Cylinder volume = pi * r^2 * h = pi * 25 * 10 = ~785
        volume = result.geometry_props["volume"]
        assert 780 < volume < 790

    def test_box_with_hole(self, real_gateway):
        """Box with hole - tests feature operations."""
        code = """
import cadquery as cq
result = (
    cq.Workplane("XY")
    .box(20, 20, 10)
    .faces(">Z")
    .workplane()
    .hole(5)
)
"""
        result = real_gateway.execute("cadquery", code)

        assert result.success is True
        # Volume should be box minus cylinder
        # 20*20*10 - pi*2.5^2*10 = 4000 - ~196 = ~3804
        volume = result.geometry_props["volume"]
        assert 3800 < volume < 3810

    def test_syntax_error(self, real_gateway):
        """Syntax error returns failure."""
        code = "result = cq.box(10, 10,"  # Incomplete

        result = real_gateway.execute("cadquery", code)

        assert result.success is False
        assert "SyntaxError" in (result.error_message or "")

    def test_no_result_variable(self, real_gateway):
        """Missing result variable returns failure."""
        code = """
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
"""
        result = real_gateway.execute("cadquery", code)

        assert result.success is False
        assert "result" in (result.error_message or "").lower()

    def test_step_file_generated(self, real_gateway):
        """STEP file is generated and path returned."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        result = real_gateway.execute("cadquery", code)

        assert result.success is True
        assert result.step_path is not None

        # Verify STEP file exists and has content
        from pathlib import Path

        step_path = Path(result.step_path)
        assert step_path.exists()
        assert step_path.stat().st_size > 0

        # Verify STEP header
        content = step_path.read_text()
        assert "ISO-10303-21" in content


@pytest.mark.integration
class TestCadQueryToolIntegration:
    """Integration tests for CadQueryTool with real gateway."""

    def test_tool_execute_real(self, real_cadquery_tool):
        """CadQueryTool with real gateway executes code."""
        result = real_cadquery_tool.execute({"code": """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""})

        assert result.success is True
        assert result.data["volume"] is not None
        assert abs(result.data["volume"] - 1000.0) < 1.0

    def test_tool_execute_real_failure(self, real_cadquery_tool):
        """CadQueryTool with real gateway handles errors."""
        result = real_cadquery_tool.execute({"code": "result = undefined_var"})

        assert result.success is False
        assert "NameError" in (result.error or "")


@pytest.mark.integration
class TestCADExecutorIntegration:
    """Integration tests for CADExecutor with real gateway."""

    def test_executor_with_real_gateway(self, real_gateway):
        """CADExecutor with real gateway executes code."""
        from src.cad.intent_decomposition.execution.executor import CADExecutor

        executor = CADExecutor(gateway=real_gateway)
        result = executor.execute("""
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
""")

        assert result.success is True
        assert result.geometry_properties.get("volume") is not None
        assert abs(result.geometry_properties["volume"] - 1000.0) < 1.0

    def test_executor_step_path_available(self, real_gateway):
        """CADExecutor returns step_path from gateway."""
        from src.cad.intent_decomposition.execution.executor import CADExecutor

        executor = CADExecutor(gateway=real_gateway)
        result = executor.execute("""
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
""")

        assert result.success is True
        assert result.step_path is not None
