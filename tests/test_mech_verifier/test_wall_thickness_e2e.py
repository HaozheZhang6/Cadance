"""End-to-end tests for wall thickness verification.

Verifies that wall thickness extraction and validation work through
the full orchestrator pipeline.
"""

import json
from pathlib import Path

import pytest

from .conftest import requires_occt

pytestmark = requires_occt


class TestWallThicknessE2E:
    """End-to-end wall thickness verification tests."""

    def test_orchestrator_validates_wall_thickness(
        self, tmp_path, golden_pass_fixture: Path
    ):
        """Orchestrator validates wall thickness from ops program."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        # Create ops program with thin wall
        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [
                        {"name": "thickness", "value": 0.8, "unit": "mm"}
                    ],  # Below 1.0mm default
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        config = VerificationConfig(ops_program=ops_path)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # Should have wall thickness warning
        wall_findings = [
            f for f in report.findings if f.rule_id == "mech.tier0.wall_thickness"
        ]
        assert len(wall_findings) == 1
        assert wall_findings[0].severity.value == "WARN"
        # WARN findings don't change status to FAIL (only BLOCKER/ERROR do)
        assert report.status in ("PASS", "WARN")

    def test_orchestrator_passes_adequate_wall(
        self, tmp_path, golden_pass_fixture: Path
    ):
        """Orchestrator passes with adequate wall thickness."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        # Create ops program with adequate wall
        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [
                        {"name": "thickness", "value": 2.5, "unit": "mm"}
                    ],  # Above 1.0mm default
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        config = VerificationConfig(ops_program=ops_path)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # Should have no wall thickness findings
        wall_findings = [
            f for f in report.findings if f.rule_id == "mech.tier0.wall_thickness"
        ]
        assert len(wall_findings) == 0

    def test_mds_contains_shell_features(self, tmp_path, golden_pass_fixture: Path):
        """MDS output contains shell features from ops program."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [{"name": "thickness", "value": 1.5, "unit": "mm"}],
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        config = VerificationConfig(ops_program=ops_path)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # MDS should have shell feature
        assert report.mds is not None
        features = report.mds.get("features", [])
        shell_features = [f for f in features if f["feature_type"] == "shell"]
        assert len(shell_features) == 1
        assert shell_features[0]["min_wall_thickness"] == 1.5
        assert shell_features[0]["from_ops_program"] is True
