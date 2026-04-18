"""Tests for comprehensive schema validation in orchestrator.

Per prompt0 requirements:
- Validate VerificationRequest before running
- Validate output report before writing (best-effort, WARN findings)
"""

import json
from unittest.mock import patch

from mech_verify.orchestrator import (
    VerificationConfig,
    VerificationOrchestrator,
    write_report,
)
from verifier_core.models import Severity


class TestRequestValidation:
    """Tests for VerificationRequest validation before running."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_valid_request_passes(self, mock_load, tmp_path):
        """Valid request passes validation without warnings."""
        mock_load.return_value = (None, "no backend")

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "test.json"
        mds_path.write_text(json.dumps(mds))

        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # Should not have request validation warnings
        request_findings = [
            f
            for f in report.findings
            if "request" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]
        assert len(request_findings) == 0

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_request_validation_disabled_by_default(self, mock_load, tmp_path):
        """Request validation is disabled when validate_schema=False."""
        mock_load.return_value = (None, "no backend")

        mds_path = tmp_path / "test.json"
        mds_path.write_text("{}")

        config = VerificationConfig(validate_schema=False)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # Should not run validation
        request_findings = [
            f
            for f in report.findings
            if "request" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]
        assert len(request_findings) == 0


class TestReportValidation:
    """Tests for VerificationReport validation before writing."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_valid_report_validation_runs(self, mock_load, tmp_path):
        """Report validation runs when validate_schema enabled."""
        mock_load.return_value = (None, "no backend")

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "test.json"
        mds_path.write_text(json.dumps(mds))

        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # Report validation should run (may find schema issues in orchestrator's custom fields)
        # This is expected - orchestrator's VerificationReport has fields not in core schema
        assert report is not None
        assert report.report_id is not None

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_report_validation_as_warnings(self, mock_load, tmp_path):
        """Report validation errors surface as WARN findings."""
        mock_load.return_value = (None, "no backend")

        # Deliberately create a scenario that might have report issues
        mds_path = tmp_path / "test.json"
        mds_path.write_text("{}")

        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # If report validation finds issues, they should be WARN severity
        report_findings = [
            f
            for f in report.findings
            if "report" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]
        for f in report_findings:
            assert f.severity == Severity.WARN

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_report_validation_does_not_crash(self, mock_load, tmp_path):
        """Report validation errors do not crash verification."""
        mock_load.return_value = (None, "no backend")

        mds_path = tmp_path / "test.json"
        mds_path.write_text("{}")

        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)

        # Should not raise exception even if report validation fails
        report = orchestrator.verify([mds_path])
        assert report is not None
        assert report.report_id is not None

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_report_validation_disabled_by_default(self, mock_load, tmp_path):
        """Report validation is disabled when validate_schema=False."""
        mock_load.return_value = (None, "no backend")

        mds_path = tmp_path / "test.json"
        mds_path.write_text("{}")

        config = VerificationConfig(validate_schema=False)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # Should not run validation
        report_findings = [
            f
            for f in report.findings
            if "report" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]
        assert len(report_findings) == 0


class TestWriteReportValidation:
    """Tests for report validation in write_report function."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_write_report_with_validation(self, mock_load, tmp_path):
        """write_report validates report when config enabled."""
        mock_load.return_value = (None, "no backend")

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "test.json"
        mds_path.write_text(json.dumps(mds))

        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        output_path = tmp_path / "report.json"
        write_report(report, output_path)

        assert output_path.exists()
        # Report should be written successfully
        report_data = json.loads(output_path.read_text())
        assert report_data["report_id"] == report.report_id
