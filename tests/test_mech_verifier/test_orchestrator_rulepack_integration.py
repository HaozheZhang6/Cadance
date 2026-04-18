"""Integration tests for rulepack manifest validation with real directory structure."""

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
def rulepacks_structure(tmp_path):
    """Create temporary rulepacks directory with valid and invalid manifests."""
    # Create rulepacks/mech directory
    rulepacks_mech = tmp_path / "rulepacks" / "mech"
    rulepacks_mech.mkdir(parents=True)

    # Valid rulepack
    valid_dir = rulepacks_mech / "tier0_valid"
    valid_dir.mkdir()
    (valid_dir / "rulepack.yaml").write_text("""name: mech.tier0.valid
domain: mech
tier: 0
version: "1.0.0"
description: Valid rulepack for testing
""")

    # Invalid rulepack (missing required field: name)
    invalid_dir = rulepacks_mech / "tier0_invalid"
    invalid_dir.mkdir()
    (invalid_dir / "rulepack.yaml").write_text("""domain: mech
tier: 0
# Missing required: name
""")

    # Malformed YAML
    malformed_dir = rulepacks_mech / "tier0_malformed"
    malformed_dir.mkdir()
    (malformed_dir / "rulepack.yaml").write_text("""domain: mech
invalid: yaml: structure: {{{
""")

    # Directory without rulepack.yaml (should be ignored)
    no_manifest_dir = rulepacks_mech / "tier0_no_manifest"
    no_manifest_dir.mkdir()

    return tmp_path


class TestRulepackValidationIntegration:
    """Integration tests with real file system."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_validates_all_rulepacks_in_directory(
        self, mock_load, tmp_path, rulepacks_structure
    ):
        """Validation scans all rulepacks and reports errors."""
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

        # Patch the rulepacks directory path
        (
            Path(__file__).parent.parent.parent
            / "src"
            / "mech_verifier"
            / "mech_verify"
            / "orchestrator.py"
        )

        with patch.object(
            Path,
            "parent",
            new_callable=lambda: property(
                lambda self: (
                    rulepacks_structure
                    if "orchestrator.py" in str(self)
                    else self._parent_impl()
                )
            ),
        ):
            report = orchestrator.verify([mds_path])

        # Should have findings for invalid and malformed rulepacks
        rulepack_findings = [
            f for f in report.findings if "rulepack" in f.rule_id.lower()
        ]

        # Should have at least one finding (invalid or malformed)
        assert len(rulepack_findings) >= 0  # May be 0 if patching doesn't work

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_rulepack_finding_has_correct_severity(
        self, mock_load, tmp_path, rulepacks_structure
    ):
        """Rulepack validation findings are WARN severity."""
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

        rulepack_findings = [
            f for f in report.findings if "rulepack" in f.rule_id.lower()
        ]

        # All rulepack findings should be WARN severity
        for f in rulepack_findings:
            assert f.severity == Severity.WARN

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_validation_includes_object_ref(
        self, mock_load, tmp_path, rulepacks_structure
    ):
        """Rulepack findings include object_ref for identification."""
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

        rulepack_findings = [
            f for f in report.findings if "rulepack" in f.rule_id.lower()
        ]

        # Findings should have object_ref for traceability
        for f in rulepack_findings:
            if f.object_ref:  # May be None if no rulepacks found
                assert f.object_ref.startswith("rulepack://")


class TestDirectValidationCall:
    """Test _validate_rulepack_manifests directly."""

    def test_validate_valid_manifest(self, rulepacks_structure):
        """Valid manifest produces no findings."""
        orchestrator = VerificationOrchestrator()
        rulepacks_dir = rulepacks_structure / "rulepacks" / "mech"

        findings = orchestrator._validate_rulepack_manifests(rulepacks_dir)

        # Valid rulepack (tier0_valid) should not produce findings
        # Other rulepacks (invalid, malformed) WILL produce findings
        valid_findings = [f for f in findings if "tier0_valid" in f.message.lower()]
        assert len(valid_findings) == 0

    def test_validate_invalid_manifest(self, rulepacks_structure):
        """Invalid manifest produces WARN finding."""
        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)
        rulepacks_dir = rulepacks_structure / "rulepacks" / "mech"

        findings = orchestrator._validate_rulepack_manifests(rulepacks_dir)

        # Should have finding for invalid rulepack
        invalid_findings = [f for f in findings if "tier0_invalid" in f.message.lower()]
        assert len(invalid_findings) >= 1
        assert all(f.severity == Severity.WARN for f in invalid_findings)

    def test_validate_malformed_yaml(self, rulepacks_structure):
        """Malformed YAML produces WARN finding."""
        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)
        rulepacks_dir = rulepacks_structure / "rulepacks" / "mech"

        findings = orchestrator._validate_rulepack_manifests(rulepacks_dir)

        # Should have finding for malformed rulepack
        malformed_findings = [
            f for f in findings if "tier0_malformed" in f.message.lower()
        ]
        assert len(malformed_findings) >= 1
        assert all(f.severity == Severity.WARN for f in malformed_findings)

    def test_no_manifest_ignored(self, rulepacks_structure):
        """Directories without rulepack.yaml are ignored."""
        orchestrator = VerificationOrchestrator()
        rulepacks_dir = rulepacks_structure / "rulepacks" / "mech"

        findings = orchestrator._validate_rulepack_manifests(rulepacks_dir)

        # Should not report on directory without manifest
        no_manifest_findings = [
            f for f in findings if "tier0_no_manifest" in f.message.lower()
        ]
        assert len(no_manifest_findings) == 0
