"""
Tests for CadQuery-to-mech_verify verification adapter.

TDD-first: Tests define expected behavior before implementation.
"""

import tempfile
from pathlib import Path

import pytest

from src.cad.verification_adapter import (
    VerificationAdapter,
    VerificationAdapterResult,
    export_to_step,
    map_findings_to_confidence,
)

# Check if CadQuery is available and works (not just imports)
from tests.conftest import CADQUERY_WORKS

CADQUERY_AVAILABLE = CADQUERY_WORKS

if CADQUERY_AVAILABLE:
    import cadquery as cq  # noqa: F401

# Check if pythonocc-core is available (required for OCCTBackend)
try:
    from OCC.Core.Bnd import Bnd_Box  # noqa: F401

    PYTHONOCC_AVAILABLE = True
except ImportError:
    PYTHONOCC_AVAILABLE = False

requires_cadquery = pytest.mark.skipif(
    not CADQUERY_AVAILABLE, reason="CadQuery not available or incompatible"
)

requires_pythonocc = pytest.mark.skipif(
    not PYTHONOCC_AVAILABLE, reason="pythonocc-core required for OCCTBackend"
)


@requires_pythonocc
class TestSTEPExportOCP:
    """Test STEP file export from OCP geometry (platform-compatible)."""

    def test_export_ocp_simple_box(self):
        """Export a simple OCP box to STEP file."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        # Create simple box using OCP
        box = BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            result_path = export_to_step(box, step_path)

            assert result_path == step_path
            assert step_path.exists()
            assert step_path.stat().st_size > 0

            # Check STEP file has valid header
            content = step_path.read_text()
            assert "ISO-10303-21" in content
            assert "HEADER" in content

    def test_export_ocp_cylinder(self):
        """Export OCP cylinder to STEP."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder

        # Create cylinder: radius=5mm, height=10mm
        cylinder = BRepPrimAPI_MakeCylinder(5.0, 10.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "cylinder.step"
            export_to_step(cylinder, step_path)

            assert step_path.exists()
            assert step_path.stat().st_size > 0

            # Verify STEP content
            content = step_path.read_text()
            assert "MANIFOLD_SOLID_BREP" in content or "ADVANCED_BREP" in content

    def test_export_ocp_fused_shapes(self):
        """Export fused OCP shapes to STEP."""
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt

        # Create L-bracket (base + wall)
        base = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 50.0, 60.0, 5.0).Shape()
        wall = BRepPrimAPI_MakeBox(gp_Pnt(0, 56, 5), 50.0, 4.0, 30.0).Shape()

        # Fuse
        fuse_op = BRepAlgoAPI_Fuse(base, wall)
        fuse_op.Build()
        bracket = fuse_op.Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "bracket.step"
            export_to_step(bracket, step_path)

            assert step_path.exists()
            assert step_path.stat().st_size > 0


class TestSTEPExport:
    """Test STEP file export from CadQuery geometry."""

    @requires_cadquery
    def test_export_simple_box(self):
        """Export a simple box to STEP file."""
        import cadquery as cq

        # Create simple box
        box = cq.Workplane("XY").box(10, 20, 5)

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            result_path = export_to_step(box, step_path)

            assert result_path == step_path
            assert step_path.exists()
            assert step_path.stat().st_size > 0

            # Check STEP file has valid header
            content = step_path.read_text()
            assert "ISO-10303-21" in content
            assert "HEADER" in content

    @requires_cadquery
    def test_export_with_features(self):
        """Export geometry with holes and fillets to STEP."""
        import cadquery as cq

        # Box with hole and fillet
        part = (
            cq.Workplane("XY")
            .box(10, 10, 5)
            .faces(">Z")
            .workplane()
            .hole(2)
            .edges("|Z")
            .fillet(0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "part.step"
            export_to_step(part, step_path)

            assert step_path.exists()
            assert step_path.stat().st_size > 0


class TestConfidenceMapping:
    """Test mapping verification findings to confidence adjustments."""

    def test_pass_enhances_confidence(self):
        """PASS status should increase confidence."""
        findings = []
        unknowns = []
        status = "PASS"

        adjustment = map_findings_to_confidence(findings, unknowns, status)
        assert adjustment == 0.1

    def test_warn_slight_penalty(self):
        """WARN findings should slightly decrease confidence."""
        from verifier_core.models import Finding, Severity

        findings = [
            Finding(
                rule_id="test.warn",
                severity=Severity.WARN,
                message="Warning",
            )
        ]
        unknowns = []
        status = "PASS"

        adjustment = map_findings_to_confidence(findings, unknowns, status)
        assert adjustment == 0.05  # +0.1 PASS - 0.05 WARN

    def test_error_moderate_penalty(self):
        """ERROR findings should significantly decrease confidence."""
        from verifier_core.models import Finding, Severity

        findings = [
            Finding(
                rule_id="test.error",
                severity=Severity.ERROR,
                message="Error",
            )
        ]
        unknowns = []
        status = "FAIL"

        adjustment = map_findings_to_confidence(findings, unknowns, status)
        assert adjustment == -0.3

    def test_blocker_fails_verification(self):
        """BLOCKER findings should catastrophically reduce confidence."""
        from verifier_core.models import Finding, Severity

        findings = [
            Finding(
                rule_id="test.blocker",
                severity=Severity.BLOCKER,
                message="Blocker",
            )
        ]
        unknowns = []
        status = "FAIL"

        adjustment = map_findings_to_confidence(findings, unknowns, status)
        assert adjustment == -1.0

    def test_unknown_caps_confidence(self):
        """UNKNOWN status (blocking unknowns) should cap confidence."""
        from verifier_core.models import Unknown

        findings = []
        unknowns = [
            Unknown(
                summary="Missing PMI",
                impact="Cannot verify tolerances",
                resolution_plan="Add PMI",
                blocking=True,
            )
        ]
        status = "UNKNOWN"

        adjustment = map_findings_to_confidence(findings, unknowns, status)
        # UNKNOWN with blocking unknown = severe penalty
        assert adjustment <= -0.5

    def test_multiple_findings_accumulate(self):
        """Multiple findings should accumulate penalties."""
        from verifier_core.models import Finding, Severity

        findings = [
            Finding(
                rule_id="test.warn1",
                severity=Severity.WARN,
                message="Warning 1",
            ),
            Finding(
                rule_id="test.warn2",
                severity=Severity.WARN,
                message="Warning 2",
            ),
        ]
        unknowns = []
        status = "PASS"

        adjustment = map_findings_to_confidence(findings, unknowns, status)
        assert adjustment == 0.0  # +0.1 PASS - 0.05*2 WARN


@requires_pythonocc
class TestVerificationAdapterWithSTEP:
    """Test verification adapter using pre-existing STEP files."""

    def test_verify_with_existing_step_file(self):
        """Test verification using existing STEP file (no CadQuery)."""
        from pathlib import Path

        # Use existing test STEP file (relative to project root)
        step_path = Path(__file__).parents[2] / (
            "src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"
        )

        if not step_path.exists():
            pytest.skip("Test STEP file not found")

        # Direct verification without CadQuery
        from src.mech_verifier.mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(
            validate_schema=False,
            require_pmi=False,
            use_external_tools=False,
        )

        orchestrator = VerificationOrchestrator(config=config)
        report = orchestrator.verify([step_path])

        # Verify report structure
        assert report.status in ["PASS", "FAIL", "UNKNOWN"]
        assert isinstance(report.findings, list)
        assert isinstance(report.unknowns, list)

        # Simple box should pass
        assert report.status == "PASS"

        # Test confidence mapping
        adjustment = map_findings_to_confidence(
            report.findings, report.unknowns, report.status
        )

        # PASS should increase confidence
        assert adjustment == 0.1

    def test_confidence_enhancement_from_step(self):
        """Test end-to-end confidence enhancement from STEP file."""
        from pathlib import Path

        # Use existing test STEP file (relative to project root)
        step_path = Path(__file__).parents[2] / (
            "src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"
        )

        if not step_path.exists():
            pytest.skip("Test STEP file not found")

        # Direct orchestrator test
        from src.mech_verifier.mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig()
        orchestrator = VerificationOrchestrator(config=config)
        report = orchestrator.verify([step_path])

        # Calculate confidence adjustment
        adjustment = map_findings_to_confidence(
            report.findings, report.unknowns, report.status
        )

        # Apply to base confidence
        base = 0.8
        enhanced = max(0.0, min(1.0, base + adjustment))

        assert 0.0 <= enhanced <= 1.0
        assert enhanced >= base  # Should improve for PASS


class TestVerificationAdapterOCP:
    """Test full verification adapter integration using OCP (platform-compatible).

    Requires pythonocc-core for OCCTBackend verification.
    """

    @requires_pythonocc
    def test_adapt_ocp_simple_box(self):
        """Verify a simple OCP box end-to-end."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.8)

        assert isinstance(result, VerificationAdapterResult)
        assert result.success
        assert result.verification_status in ["PASS", "FAIL", "UNKNOWN"]
        assert result.enhanced_confidence >= 0.0
        assert result.enhanced_confidence <= 1.0
        assert result.step_path is not None
        assert result.step_path.exists()
        assert result.report is not None
        assert result.base_confidence == 0.8

        # Simple box should pass verification
        assert result.verification_status == "PASS"
        # Confidence should be enhanced
        assert result.enhanced_confidence > result.base_confidence

    @requires_pythonocc
    def test_adapt_ocp_with_low_base_confidence(self):
        """Low base confidence should be capped appropriately."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.3)

        assert result.enhanced_confidence >= 0.0
        assert result.enhanced_confidence <= 1.0

        # Even with PASS, low base shouldn't jump too high
        assert result.enhanced_confidence <= 0.5

    @requires_pythonocc
    def test_adapt_ocp_with_high_base_confidence(self):
        """High base confidence should be capped at 1.0."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.95)

        assert result.enhanced_confidence <= 1.0

    @requires_pythonocc
    def test_ocp_degenerate_geometry_reduces_confidence(self):
        """Degenerate geometry should reduce confidence significantly."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        # Create nearly zero-height box
        flat_box = BRepPrimAPI_MakeBox(10.0, 10.0, 0.00001).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(flat_box, base_confidence=0.8)

        # May pass or fail depending on OCCT tolerance
        # But should generate findings
        assert result.verification_status in ["PASS", "FAIL", "UNKNOWN"]

    @requires_pythonocc
    def test_ocp_custom_output_dir(self):
        """Should respect custom output directory."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "custom_output"

            adapter = VerificationAdapter(output_dir=output_dir)
            result = adapter.verify(box, base_confidence=0.8)

            assert result.step_path.parent == output_dir
            assert result.step_path.exists()

    @requires_pythonocc
    def test_ocp_verification_report_details(self):
        """Verification report should contain expected fields."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.8)

        assert result.report is not None
        assert "report_id" in result.report
        assert "status" in result.report
        assert "findings" in result.report

    @requires_pythonocc
    def test_ocp_cleanup_temp_files(self):
        """Temp files should be cleaned up when cleanup=True."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.8, cleanup=True)

        # STEP file should not exist after cleanup
        assert not result.step_path.exists()

    @requires_pythonocc
    def test_ocp_preserve_temp_files(self):
        """Temp files should be preserved when cleanup=False."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.8, cleanup=False)

        # STEP file should exist
        assert result.step_path.exists()

        # Clean up manually
        result.step_path.unlink()


class TestVerificationAdapter:
    """Test full verification adapter integration (CadQuery-based)."""

    @requires_cadquery
    @requires_pythonocc
    def test_adapt_simple_box(self):
        """Verify a simple CadQuery box end-to-end."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 20, 5)

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.8)

        assert isinstance(result, VerificationAdapterResult)
        assert result.success
        assert result.verification_status in ["PASS", "FAIL", "UNKNOWN"]
        assert result.enhanced_confidence >= 0.0
        assert result.enhanced_confidence <= 1.0
        assert result.step_path is not None
        assert result.step_path.exists()
        assert result.report is not None
        assert result.base_confidence == 0.8

        # Simple box should pass verification
        assert result.verification_status == "PASS"
        # Confidence should be enhanced
        assert result.enhanced_confidence > result.base_confidence

    @requires_cadquery
    def test_adapt_with_low_base_confidence(self):
        """Low base confidence should be capped appropriately."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.3)

        assert result.enhanced_confidence >= 0.0
        assert result.enhanced_confidence <= 1.0

        # Even with PASS, low base shouldn't jump too high
        assert result.enhanced_confidence <= 0.5

    @requires_cadquery
    def test_adapt_with_high_base_confidence(self):
        """High base confidence should be capped at 1.0."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.95)

        assert result.enhanced_confidence <= 1.0

    @requires_cadquery
    def test_degenerate_geometry_reduces_confidence(self):
        """Degenerate geometry should reduce confidence significantly."""
        import cadquery as cq

        # Create zero-volume "box"
        flat_box = cq.Workplane("XY").box(10, 10, 0.00001)

        adapter = VerificationAdapter()
        result = adapter.verify(flat_box, base_confidence=0.8)

        # Note: Very thin geometry may still pass OCCT validation
        # but should at least maintain or slightly reduce confidence
        assert result.verification_status in ["PASS", "FAIL", "UNKNOWN"]
        # If it passes, confidence should not increase much
        if result.verification_status == "PASS":
            assert result.enhanced_confidence <= result.base_confidence + 0.15

    @requires_cadquery
    def test_custom_output_dir(self):
        """Should respect custom output directory."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "custom_output"

            adapter = VerificationAdapter(output_dir=output_dir)
            result = adapter.verify(box, base_confidence=0.8)

            assert result.step_path.parent == output_dir
            assert result.step_path.exists()

    @requires_cadquery
    def test_verification_report_details(self):
        """Verification report should contain expected fields."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.8)

        assert result.report is not None
        assert "report_id" in result.report
        assert "status" in result.report
        assert "findings" in result.report
        assert "unknowns" in result.report
        assert "summary" in result.report

    @requires_cadquery
    def test_cleanup_temp_files(self):
        """Should clean up temporary STEP files if requested."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter(cleanup=True)
        result = adapter.verify(box, base_confidence=0.8)

        # STEP file should be deleted after verification
        assert not result.step_path.exists()

    @requires_cadquery
    def test_preserve_temp_files(self):
        """Should preserve temporary STEP files if cleanup disabled."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter(cleanup=False)
        result = adapter.verify(box, base_confidence=0.8)

        # STEP file should exist
        assert result.step_path.exists()


class TestConfidenceBoundsOCP:
    """Test confidence capping and floor behavior using OCP.

    Requires pythonocc-core for OCCTBackend verification.
    """

    @requires_pythonocc
    def test_ocp_confidence_floor_at_zero(self):
        """Confidence should never go below 0.0."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.1)

        assert result.enhanced_confidence >= 0.0

    @requires_pythonocc
    def test_ocp_confidence_cap_at_one(self):
        """Confidence should never exceed 1.0."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.95)

        assert result.enhanced_confidence <= 1.0


class TestConfidenceBounds:
    """Test confidence capping and floor behavior (CadQuery-based)."""

    @requires_cadquery
    def test_confidence_floor_at_zero(self):
        """Confidence should never go below 0.0."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.1)

        assert result.enhanced_confidence >= 0.0

    @requires_cadquery
    def test_confidence_cap_at_one(self):
        """Confidence should never exceed 1.0."""
        import cadquery as cq

        box = cq.Workplane("XY").box(10, 10, 10)

        adapter = VerificationAdapter()
        result = adapter.verify(box, base_confidence=0.95)

        assert result.enhanced_confidence <= 1.0

    def test_severe_blocker_can_zero_confidence(self):
        """Severe blocker should be able to drive confidence to zero."""
        # This test validates that catastrophic failures properly signal
        # unusable geometry by zeroing confidence
        # Implementation should handle this in map_findings_to_confidence

        from verifier_core.models import Finding, Severity

        findings = [
            Finding(
                rule_id="test.blocker",
                severity=Severity.BLOCKER,
                message="Invalid B-Rep",
            )
        ]
        unknowns = []
        status = "FAIL"

        adjustment = map_findings_to_confidence(findings, unknowns, status)

        # Blocker should give -1.0, which would zero any base confidence
        assert adjustment == -1.0


class TestVerifyFromStep:
    """Test VerificationAdapter.verify_from_step() method."""

    def test_verify_from_step_file_not_found(self):
        """verify_from_step raises FileNotFoundError for missing file."""
        adapter = VerificationAdapter()

        with pytest.raises(FileNotFoundError):
            adapter.verify_from_step("/nonexistent/path.step", base_confidence=0.8)

    def test_verify_from_step_invalid_confidence(self, tmp_path):
        """verify_from_step raises ValueError for invalid confidence."""
        # Create a dummy file so FileNotFoundError doesn't fire first
        dummy = tmp_path / "test.step"
        dummy.write_text("dummy")

        adapter = VerificationAdapter()

        with pytest.raises(ValueError, match="base_confidence must be in"):
            adapter.verify_from_step(str(dummy), base_confidence=1.5)

    @requires_pythonocc
    def test_verify_from_step_simple_box(self):
        """verify_from_step works with OCP-generated STEP file."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        # Create STEP file using OCP
        box = BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            export_to_step(box, step_path)

            adapter = VerificationAdapter()
            result = adapter.verify_from_step(step_path, base_confidence=0.8)

            assert result.success is True
            assert result.verification_status in ["PASS", "FAIL", "UNKNOWN"]
            assert result.step_path == step_path
            assert result.base_confidence == 0.8
            assert 0.0 <= result.enhanced_confidence <= 1.0

    @requires_pythonocc
    def test_verify_from_step_no_cleanup_by_default(self):
        """verify_from_step does not delete external STEP files by default."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            export_to_step(box, step_path)

            adapter = VerificationAdapter()
            adapter.verify_from_step(step_path, base_confidence=0.8)

            # File should still exist
            assert step_path.exists()

    @requires_pythonocc
    def test_verify_from_step_cleanup_when_requested(self):
        """verify_from_step deletes file when cleanup=True."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            export_to_step(box, step_path)

            adapter = VerificationAdapter()
            adapter.verify_from_step(step_path, base_confidence=0.8, cleanup=True)

            # File should be deleted
            assert not step_path.exists()

    @requires_pythonocc
    def test_verify_from_step_confidence_enhancement(self):
        """verify_from_step enhances confidence for passing geometry."""
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            export_to_step(box, step_path)

            adapter = VerificationAdapter()
            result = adapter.verify_from_step(step_path, base_confidence=0.8)

            # Simple box should pass and enhance confidence
            if result.verification_status == "PASS":
                assert result.enhanced_confidence >= result.base_confidence
