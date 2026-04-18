"""Integration tests for evaluation harness with real CadQuery execution.

These tests verify the complete integration:
1. EvaluationHarness discovers test cases
2. CadQueryTool with gateway backend executes code
3. GeometricComparator validates results
4. Results match expected geometry properties

Run with: pytest -m integration tests/test_tools/test_cadquery/test_evaluation_integration.py
"""

import tempfile
from pathlib import Path

import pytest


@pytest.mark.integration
class TestEvaluationHarnessIntegration:
    """Integration tests for evaluation harness with real CadQuery."""

    def test_harness_discovers_train_cases(self, real_cadquery_tool):
        """Harness discovers training test cases."""
        from tests.test_tools.test_cadquery.harness.runner import EvaluationHarness

        harness = EvaluationHarness(tool=real_cadquery_tool)
        cases = harness.discover_test_cases(split="train")

        assert len(cases) > 0
        # Should find at least level 1 cases
        level1_cases = [c for c in cases if "level_1" in str(c)]
        assert len(level1_cases) > 0

    def test_single_train_case_execution(self, real_cadquery_tool):
        """Single train case executes successfully with real CadQuery."""
        from tests.test_tools.test_cadquery.harness.runner import EvaluationHarness

        harness = EvaluationHarness(tool=real_cadquery_tool)
        train_cases = harness.discover_test_cases(split="train")

        # Find L1_01_simple_box (should exist and be reliable)
        simple_box_cases = [c for c in train_cases if "L1_01" in c.name]

        if not simple_box_cases:
            pytest.skip("L1_01 test case not found")

        result = harness.run_single(simple_box_cases[0])

        # Should execute successfully
        assert result.error is None or "success" in str(result).lower()
        # May or may not match spec exactly, but should execute
        assert result.attempts > 0

    def test_level1_train_execution(self, real_cadquery_tool):
        """Level 1 train cases execute with real CadQuery."""
        from tests.test_tools.test_cadquery.harness.runner import EvaluationHarness

        harness = EvaluationHarness(tool=real_cadquery_tool)
        results = harness.run_level(level=1, split="train")

        # Should have results
        assert len(results) > 0

        # At least some should succeed (execution, not necessarily spec match)
        executed_ok = [r for r in results if r.error is None]
        assert (
            len(executed_ok) > 0
        ), f"No cases executed successfully. Errors: {[r.error for r in results]}"

    def test_gateway_produces_geometry_props(self, real_cadquery_tool):
        """Gateway-backed tool produces geometry properties for comparison."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 5)
"""
        result = real_cadquery_tool.execute({"code": code})

        assert result.success is True
        assert "volume" in result.data
        # Box volume should be 10 * 20 * 5 = 1000
        assert abs(result.data["volume"] - 1000.0) < 1.0


@pytest.mark.integration
class TestMechVerifierNoConflict:
    """Verify mech_verifier still works (no numpy conflicts in main process)."""

    def test_mech_verifier_imports(self):
        """mech_verifier imports without errors."""
        # These imports would fail if numpy version conflicts
        from src.mech_verifier.mech_verify.orchestrator import (
            VerificationOrchestrator,
        )
        from verifier_core.models import Finding

        assert Finding is not None
        assert VerificationOrchestrator is not None

    def test_ocp_imports(self):
        """OCP (pythonocc) imports without errors."""
        try:
            from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        except ImportError:
            pytest.skip("pythonocc-core not installed")

        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()
        assert box is not None

    def test_mech_verifier_simple_verification(self):
        """mech_verifier can verify OCP-generated geometry."""
        try:
            from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        except ImportError:
            pytest.skip("pythonocc-core not installed")

        from src.cad.verification_adapter import export_to_step
        from src.mech_verifier.mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        # Create simple box
        box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

        with tempfile.TemporaryDirectory() as tmpdir:
            step_path = Path(tmpdir) / "box.step"
            export_to_step(box, step_path)

            # Run verification
            config = VerificationConfig(
                validate_schema=False,
                require_pmi=False,
                use_external_tools=False,
            )
            orchestrator = VerificationOrchestrator(config=config)
            report = orchestrator.verify([step_path])

            assert report.status in ["PASS", "FAIL", "UNKNOWN"]


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow: CadQuery execution -> STEP -> verification."""

    def test_gateway_to_verification_workflow(self, real_gateway):
        """Complete workflow: gateway execution -> STEP file -> verification."""
        from src.cad.verification_adapter import VerificationAdapter

        # Execute code via gateway
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        exec_result = real_gateway.execute("cadquery", code)
        assert exec_result.success is True
        assert exec_result.step_path is not None

        # Verify the STEP file
        adapter = VerificationAdapter()
        verify_result = adapter.verify_from_step(
            exec_result.step_path,
            base_confidence=0.8,
        )

        assert verify_result.success is True
        assert verify_result.verification_status in ["PASS", "FAIL", "UNKNOWN"]
        assert 0.0 <= verify_result.enhanced_confidence <= 1.0
