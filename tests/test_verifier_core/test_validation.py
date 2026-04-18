"""Tests for verifier_core.validation module."""

import pytest

from verifier_core.validation import (
    SCHEMA_DIR,
    is_valid,
    load_schema,
    validate_evidence,
    validate_finding,
    validate_unknown,
    validate_verification_report,
    validate_verification_request,
)


class TestSchemaFilesExist:
    """Verify schema files exist."""

    def test_main_schema_exists(self):
        """Main verifier.schema.json should exist."""
        path = SCHEMA_DIR / "verifier.schema.json"
        assert path.exists(), f"Main schema not found: {path}"

    def test_finding_schema_exists(self):
        """finding.schema.json should exist."""
        path = SCHEMA_DIR / "finding.schema.json"
        assert path.exists()

    def test_evidence_schema_exists(self):
        """evidence.schema.json should exist."""
        path = SCHEMA_DIR / "evidence.schema.json"
        assert path.exists()

    def test_unknown_schema_exists(self):
        """unknown.schema.json should exist."""
        path = SCHEMA_DIR / "unknown.schema.json"
        assert path.exists()

    def test_verification_request_schema_exists(self):
        """verification_request.schema.json should exist."""
        path = SCHEMA_DIR / "verification_request.schema.json"
        assert path.exists()

    def test_verification_report_schema_exists(self):
        """verification_report.schema.json should exist."""
        path = SCHEMA_DIR / "verification_report.schema.json"
        assert path.exists()

    def test_rulepack_schema_exists(self):
        """rulepack.schema.json should exist."""
        path = SCHEMA_DIR / "rulepack.schema.json"
        assert path.exists()


class TestValidateFinding:
    """Tests for Finding validation."""

    def test_valid_finding_passes(self):
        """Valid Finding should pass validation."""
        finding = {
            "rule_id": "test_rule",
            "severity": "ERROR",
            "message": "Test message",
        }
        errors = validate_finding(finding)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_finding_with_all_fields(self):
        """Finding with all optional fields should pass."""
        finding = {
            "finding_id": "f123",
            "rule_id": "test_rule",
            "severity": "WARN",
            "message": "Test message",
            "object_ref": "eda://board/U1",
            "object_refs": ["eda://board/U1", "eda://board/U2"],
            "measured_value": 10.5,
            "limit": {"value": 10.0, "unit": "mm"},
            "suggested_fix": "Check connection",
            "tags": ["design", "critical"],
            "evidence_ids": ["e1", "e2"],
        }
        errors = validate_finding(finding)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_missing_required_field_fails(self):
        """Finding missing required field should fail."""
        finding = {
            "rule_id": "test_rule",
            # missing severity and message
        }
        errors = validate_finding(finding)
        assert len(errors) > 0

    def test_invalid_severity_fails(self):
        """Invalid severity value should fail."""
        finding = {
            "rule_id": "test_rule",
            "severity": "INVALID",
            "message": "Test",
        }
        errors = validate_finding(finding)
        assert len(errors) > 0


class TestValidateEvidence:
    """Tests for Evidence validation."""

    def test_valid_evidence_passes(self):
        """Valid Evidence should pass validation."""
        evidence = {
            "evidence_id": "ev123",
            "kind": "simulation",
            "provenance": {
                "tool_name": "kicad",
                "tool_version": "7.0.0",
            },
        }
        errors = validate_evidence(evidence)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_missing_provenance_fails(self):
        """Evidence without provenance should fail."""
        evidence = {
            "evidence_id": "ev123",
            "kind": "simulation",
            # missing provenance
        }
        errors = validate_evidence(evidence)
        assert len(errors) > 0


class TestValidateUnknown:
    """Tests for Unknown validation."""

    def test_valid_unknown_passes(self):
        """Valid Unknown should pass validation."""
        unknown = {
            "summary": "Missing footprint data",
            "impact": "Cannot verify pad dimensions",
            "resolution_plan": "Add footprint to library",
        }
        errors = validate_unknown(unknown)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_unknown_with_optional_fields(self):
        """Unknown with optional fields should pass."""
        unknown = {
            "unknown_id": "u123",
            "summary": "Test",
            "impact": "Test impact",
            "resolution_plan": "Test plan",
            "blocking": True,
            "object_ref": "eda://board/U1",
            "created_by_rule_id": "rule_1",
            "escalation_tier": 2,
        }
        errors = validate_unknown(unknown)
        assert len(errors) == 0, f"Unexpected errors: {errors}"


class TestValidateVerificationRequest:
    """Tests for VerificationRequest validation."""

    def test_valid_request_passes(self):
        """Valid VerificationRequest should pass validation."""
        request = {
            "domain": "eda",
            "tier": 0,
            "artifacts": [{"kind": "board", "path": "/path/to/board.kicad_pcb"}],
        }
        errors = validate_verification_request(request)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_invalid_domain_fails(self):
        """Invalid domain should fail."""
        request = {
            "domain": "invalid_domain",
            "tier": 0,
            "artifacts": [{"kind": "board", "path": "/path"}],
        }
        errors = validate_verification_request(request)
        assert len(errors) > 0

    def test_invalid_tier_fails(self):
        """Tier out of range should fail."""
        request = {
            "domain": "eda",
            "tier": 99,  # out of range (0-9)
            "artifacts": [{"kind": "board", "path": "/path"}],
        }
        errors = validate_verification_request(request)
        assert len(errors) > 0


class TestValidateVerificationReport:
    """Tests for VerificationReport validation."""

    def test_valid_report_passes(self):
        """Valid VerificationReport should pass validation."""
        report = {
            "request": {
                "domain": "eda",
                "tier": 0,
                "artifacts": [{"kind": "board", "path": "/path"}],
            },
            "status": "PASS",
            "findings": [],
            "unknowns": [],
            "evidence": [],
        }
        errors = validate_verification_report(report)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_report_with_findings(self):
        """Report with findings should pass."""
        report = {
            "request": {
                "domain": "mech",
                "tier": 1,
                "artifacts": [{"kind": "step", "uri": "file:///model.step"}],
            },
            "status": "FAIL",
            "findings": [
                {
                    "rule_id": "stress_check",
                    "severity": "ERROR",
                    "message": "Stress exceeds limit",
                }
            ],
            "unknowns": [],
            "evidence": [
                {
                    "evidence_id": "ev1",
                    "kind": "fea_result",
                    "provenance": {"tool_name": "ansys"},
                }
            ],
        }
        errors = validate_verification_report(report)
        assert len(errors) == 0, f"Unexpected errors: {errors}"


class TestIsValid:
    """Tests for is_valid helper function."""

    def test_is_valid_true(self):
        """Valid instance returns True."""
        finding = {
            "rule_id": "test",
            "severity": "WARN",
            "message": "Test",
        }
        assert is_valid(finding, schema_name="finding") is True

    def test_is_valid_false(self):
        """Invalid instance returns False."""
        finding = {"rule_id": "test"}  # missing required fields
        assert is_valid(finding, schema_name="finding") is False


class TestLoadSchema:
    """Tests for load_schema function."""

    def test_load_existing_schema(self):
        """Should load existing schema."""
        schema = load_schema("finding")
        assert schema is not None

    def test_load_nonexistent_schema(self):
        """Should raise for nonexistent schema."""
        with pytest.raises(FileNotFoundError):
            load_schema("nonexistent_schema")
