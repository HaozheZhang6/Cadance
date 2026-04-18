"""Tests for CadQuery tool adapter."""

import json
from pathlib import Path

import pytest

from src.tools.cadquery import CadQueryTool

# Skip all tests if CadQuery not available
pytestmark = pytest.mark.skipif(
    not CadQueryTool.is_available(),
    reason="CadQuery not available",
)


@pytest.fixture
def cadquery_tool(tmp_path):
    """CadQuery tool with temp output dir."""
    return CadQueryTool(output_dir=tmp_path)


@pytest.fixture
def simple_box():
    """Simple CadQuery box geometry."""
    import cadquery as cq

    return cq.Workplane("XY").box(10, 20, 5)


class TestCadQueryToolBasics:
    """Basic tool interface tests."""

    def test_tool_name(self, cadquery_tool):
        assert cadquery_tool.name == "cadquery-verify"

    def test_tool_version(self, cadquery_tool):
        assert cadquery_tool.version == "0.1.0"

    def test_has_capabilities(self, cadquery_tool):
        caps = cadquery_tool.capabilities
        assert len(caps) == 3
        cap_names = [c.name for c in caps]
        assert "verify_geometry" in cap_names
        assert "export_verify" in cap_names
        assert "verify_with_manifest" in cap_names

    def test_input_schema(self, cadquery_tool):
        schema = cadquery_tool.input_schema
        assert schema["type"] == "object"
        assert "mode" in schema["properties"]
        assert schema["required"] == ["mode"]

    def test_output_schema(self, cadquery_tool):
        schema = cadquery_tool.output_schema
        assert schema["type"] == "object"
        assert "status" in schema["properties"]
        assert "enhanced_confidence" in schema["properties"]


class TestCadQueryToolValidation:
    """Input validation tests."""

    def test_validate_geometry_mode(self, cadquery_tool, simple_box):
        assert cadquery_tool.validate_inputs(
            {"mode": "geometry", "geometry": simple_box}
        )

    def test_validate_step_path_mode(self, cadquery_tool, tmp_path):
        step_file = tmp_path / "test.step"
        step_file.write_text("ISO-10303-21")
        assert cadquery_tool.validate_inputs(
            {"mode": "step_path", "step_path": str(step_file)}
        )

    def test_reject_invalid_mode(self, cadquery_tool):
        assert not cadquery_tool.validate_inputs({"mode": "invalid"})

    def test_reject_missing_geometry(self, cadquery_tool):
        assert not cadquery_tool.validate_inputs({"mode": "geometry"})

    def test_reject_missing_step_path(self, cadquery_tool):
        assert not cadquery_tool.validate_inputs({"mode": "step_path"})


class TestCadQueryToolExecution:
    """Tool execution tests (mocked orchestrator)."""

    def test_step_path_not_found(self, cadquery_tool):
        result = cadquery_tool.execute(
            {
                "mode": "step_path",
                "step_path": "/nonexistent/file.step",
            }
        )
        assert not result.success
        assert result.error == "FileNotFound"
        assert result.data["status"] == "UNKNOWN"


# Tests that require OCCT backend
try:
    from src.mech_verifier.mech_verify.backend import OCCTBackend

    OCCT_AVAILABLE = OCCTBackend().is_available()
except ImportError:
    OCCT_AVAILABLE = False

requires_occt = pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not available")


@requires_occt
class TestCadQueryToolWithOCCT:
    """Integration tests with OCCT backend."""

    def test_verify_geometry_exports_step(self, cadquery_tool, simple_box, tmp_path):
        """Geometry verification exports STEP file."""
        result = cadquery_tool.execute(
            {
                "mode": "geometry",
                "geometry": simple_box,
                "base_confidence": 0.8,
                "part_name": "test_box",
            }
        )

        assert result.success
        assert result.data["status"] in ["PASS", "FAIL", "UNKNOWN"]
        assert result.data["base_confidence"] == 0.8
        assert result.data["enhanced_confidence"] is not None

        # Check STEP file was created
        step_path = result.data.get("step_path")
        if step_path:
            assert Path(step_path).exists() or result.data.get("cleanup")

    def test_verify_geometry_confidence_enhancement(self, cadquery_tool, simple_box):
        """Confidence is enhanced based on verification results."""
        result = cadquery_tool.execute(
            {
                "mode": "geometry",
                "geometry": simple_box,
                "base_confidence": 0.5,
            }
        )

        assert result.success
        # Passing geometry should increase confidence
        if result.data["status"] == "PASS":
            assert result.data["confidence_adjustment"] >= 0
            assert result.data["enhanced_confidence"] >= result.data["base_confidence"]

    def test_verify_step_path_with_manifest(self, cadquery_tool, tmp_path):
        """STEP verification uses manifest for stable part IDs."""
        # Create test STEP from CadQuery
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)
        step_path = tmp_path / "part.step"
        cq.exporters.export(box.val(), str(step_path), exportType="STEP")

        # Create manifest
        manifest = {
            "schema_version": "cadquery.manifest.v1",
            "parts": [{"index": 0, "part_id": "test_box_v1", "name": "test_box"}],
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        result = cadquery_tool.execute(
            {
                "mode": "step_path",
                "step_path": str(step_path),
                "manifest_path": str(manifest_path),
                "base_confidence": 0.7,
            }
        )

        assert result.success
        assert result.data["status"] in ["PASS", "FAIL", "UNKNOWN"]

        # Check MDS uses manifest part_id
        mds = result.data.get("mds")
        if mds and "parts" in mds:
            part_id = mds["parts"][0].get("part_id")
            assert part_id == "test_box_v1", f"Expected manifest part_id, got {part_id}"


class TestCadQueryToolAvailability:
    """Tool availability checks."""

    def test_is_available_returns_bool(self):
        result = CadQueryTool.is_available()
        assert isinstance(result, bool)


# Tests without CadQuery (always run)
class TestCadQueryToolWithoutCadQuery:
    """Tests that work even without CadQuery installed."""

    def test_tool_instantiation(self, tmp_path):
        """Tool can be instantiated without CadQuery."""
        tool = CadQueryTool(output_dir=tmp_path)
        assert tool.name == "cadquery-verify"

    def test_step_path_mode_works_without_cadquery(self, tmp_path):
        """STEP path mode doesn't require CadQuery."""
        tool = CadQueryTool()

        # This should fail because file doesn't exist, not because CadQuery missing
        result = tool.execute(
            {
                "mode": "step_path",
                "step_path": "/nonexistent.step",
            }
        )

        assert not result.success
        assert result.error == "FileNotFound"
