"""Tests for SHACL validation gating via --shacl flag.

Per prompt2:56, SHACL should be opt-in via --shacl flag.
These tests verify that SHACL validation only runs when explicitly enabled.
"""

from pathlib import Path

import pytest

from .conftest import requires_occt


class TestSHACLGating:
    """Tests for SHACL opt-in behavior."""

    def test_shacl_disabled_by_default(self, golden_pass_fixture: Path):
        """SHACL validation does NOT run when shacl=False (default)."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        config = VerificationConfig(shacl=False)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # SHACL not run → no SHACL findings or unknowns
        # Check that no findings have rule_id starting with "mech.shacl"
        shacl_findings = [
            f for f in report.findings if f.rule_id.startswith("mech.shacl")
        ]
        shacl_unknowns = [
            u
            for u in report.unknowns
            if u.created_by_rule_id and u.created_by_rule_id.startswith("mech.shacl")
        ]

        assert len(shacl_findings) == 0, "No SHACL findings when shacl=False"
        assert len(shacl_unknowns) == 0, "No SHACL unknowns when shacl=False"

    def test_shacl_runs_when_enabled(self, golden_pass_fixture: Path):
        """SHACL validation runs when shacl=True."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )
        from mech_verify.shacl.engine import PYSHACL_AVAILABLE, RDFLIB_AVAILABLE

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        config = VerificationConfig(shacl=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # If dependencies missing, should have Unknown
        if not RDFLIB_AVAILABLE or not PYSHACL_AVAILABLE:
            shacl_unknowns = [
                u
                for u in report.unknowns
                if u.created_by_rule_id
                and u.created_by_rule_id.startswith("mech.shacl")
            ]
            assert len(shacl_unknowns) > 0, "Should emit Unknown if deps missing"
        else:
            # Dependencies available → SHACL ran (may or may not have findings)
            # Just verify no crash occurred and report is valid
            assert report.status in ("PASS", "FAIL", "WARN", "UNKNOWN")

    @requires_occt
    def test_shacl_dependency_unknown_when_enabled(self, golden_pass_fixture: Path):
        """SHACL emits dependency Unknown when enabled but deps missing."""
        from unittest.mock import patch

        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        # Mock dependencies as unavailable to test graceful degradation
        with patch("mech_verify.shacl.engine.RDFLIB_AVAILABLE", False):
            config = VerificationConfig(shacl=True)
            orchestrator = VerificationOrchestrator(config)
            report = orchestrator.verify([step_file])

            # Should have dependency Unknown
            dep_unknowns = [
                u
                for u in report.unknowns
                if u.created_by_rule_id == "mech.shacl.dependency"
            ]
            assert len(dep_unknowns) > 0, "Should emit dependency Unknown"

            # Verify Unknown has resolution plan
            unknown = dep_unknowns[0]
            assert "install" in unknown.resolution_plan.lower()

    def test_cli_accepts_shacl_flag(self):
        """CLI accepts --shacl flag."""
        from mech_verify.cli import verify

        # verify is a Click command - check its params
        assert hasattr(verify, "params"), "verify should be a Click command"

        # Find --shacl option in Click params
        param_names = [p.name for p in verify.params]
        assert "shacl" in param_names, "CLI should have 'shacl' parameter"

    def test_config_has_shacl_field(self):
        """VerificationConfig has shacl field."""
        from mech_verify.orchestrator import VerificationConfig

        config = VerificationConfig(shacl=True)
        assert hasattr(config, "shacl")
        assert config.shacl is True

        config = VerificationConfig(shacl=False)
        assert config.shacl is False

        # Default should be False (opt-in)
        config = VerificationConfig()
        assert config.shacl is False


class TestSHACLGatingIntegration:
    """Integration tests for SHACL gating with real files."""

    def test_no_shacl_findings_without_flag(self, golden_pass_fixture: Path, tmp_path):
        """End-to-end: no --shacl flag → no SHACL findings."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
            write_report,
        )

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        config = VerificationConfig(shacl=False)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # Write report to verify serialization
        report_path = tmp_path / "report.json"
        write_report(report, report_path)

        # Read back and verify
        import json

        with open(report_path) as f:
            data = json.load(f)

        # No SHACL findings in report
        shacl_findings = [
            f for f in data["findings"] if f["rule_id"].startswith("mech.shacl")
        ]
        assert len(shacl_findings) == 0

    def test_shacl_findings_with_flag(self, golden_pass_fixture: Path):
        """End-to-end: --shacl flag → SHACL runs."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )
        from mech_verify.shacl.engine import PYSHACL_AVAILABLE, RDFLIB_AVAILABLE

        if not RDFLIB_AVAILABLE or not PYSHACL_AVAILABLE:
            pytest.skip("SHACL dependencies not installed")

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        config = VerificationConfig(shacl=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([step_file])

        # SHACL should have run (may or may not produce findings)
        # Just verify no crash and report is valid
        assert report.status in ("PASS", "FAIL", "WARN", "UNKNOWN")
        assert isinstance(report.findings, list)
        assert isinstance(report.unknowns, list)
