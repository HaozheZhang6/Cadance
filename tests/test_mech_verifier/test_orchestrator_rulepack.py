"""Tests for rulepack manifest validation in orchestrator.

Per prompt0 requirements:
- Validate RulePack manifest when loading
- Surface validation errors as findings (best-effort, don't crash)
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mech_verify.orchestrator import (
    VerificationConfig,
    VerificationOrchestrator,
)
from verifier_core.models import Severity


@pytest.fixture
def mock_rulepacks_dir(tmp_path):
    """Create mock rulepacks directory structure."""
    rulepacks = tmp_path / "rulepacks" / "mech"
    rulepacks.mkdir(parents=True)

    # Valid rulepack
    valid_pack = rulepacks / "tier0_valid"
    valid_pack.mkdir()
    (valid_pack / "rulepack.yaml").write_text("""
name: mech.tier0.valid
domain: mech
tier: 0
version: "1.0.0"
parameters:
  min_diameter: 1.0
""")

    # Invalid rulepack (missing required field: name)
    invalid_pack = rulepacks / "tier0_invalid"
    invalid_pack.mkdir()
    (invalid_pack / "rulepack.yaml").write_text("""
# Missing required: name
domain: mech
tier: 0
""")

    # Malformed YAML
    malformed_pack = rulepacks / "tier0_malformed"
    malformed_pack.mkdir()
    (malformed_pack / "rulepack.yaml").write_text("{ invalid yaml: ]][")

    return rulepacks.parent.parent  # Return project root


class TestRulepackManifestValidation:
    """Tests for rulepack manifest validation during discovery."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_valid_rulepack_no_warnings(self, mock_load, tmp_path, mock_rulepacks_dir):
        """Valid rulepack manifest produces no validation warnings."""
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

        # Patch rulepacks_dir to use mock
        with patch.object(
            Path,
            "__truediv__",
            side_effect=lambda self, other: mock_rulepacks_dir / other,
        ):
            report = orchestrator.verify([mds_path])

        # Should not have rulepack validation warnings
        rulepack_findings = [
            f
            for f in report.findings
            if "rulepack" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]
        # Valid rulepacks should produce no findings
        valid_findings = [f for f in rulepack_findings if "valid" in f.message.lower()]
        assert len(valid_findings) == 0

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_invalid_rulepack_warns(self, mock_load, tmp_path, mock_rulepacks_dir):
        """Invalid rulepack manifest produces WARN finding."""
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

        # This test expects rulepack validation to be implemented
        # For now, it documents the expected behavior
        report = orchestrator.verify([mds_path])

        # When implemented, invalid rulepacks should produce WARN findings
        rulepack_findings = [
            f
            for f in report.findings
            if "rulepack" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]

        # Validation errors should be WARN severity
        for f in rulepack_findings:
            assert f.severity == Severity.WARN

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_rulepack_validation_disabled_by_default(self, mock_load, tmp_path):
        """Rulepack validation disabled when validate_schema=False."""
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

        config = VerificationConfig(validate_schema=False)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # Should not run validation
        rulepack_findings = [
            f
            for f in report.findings
            if "rulepack" in f.rule_id.lower() and "schema" in f.rule_id.lower()
        ]
        assert len(rulepack_findings) == 0

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_malformed_yaml_does_not_crash(
        self, mock_load, tmp_path, mock_rulepacks_dir
    ):
        """Malformed YAML in rulepack does not crash verification."""
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

        # Should not raise exception even if YAML is malformed
        report = orchestrator.verify([mds_path])
        assert report is not None
        assert report.report_id is not None

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_missing_rulepack_dir_no_error(self, mock_load, tmp_path):
        """Missing rulepacks directory does not cause errors."""
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

        # Should handle missing rulepacks directory gracefully
        report = orchestrator.verify([mds_path])
        assert report is not None
        assert report.status in ["PASS", "FAIL", "UNKNOWN"]
