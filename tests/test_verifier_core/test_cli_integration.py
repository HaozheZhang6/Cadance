"""Tests for verifier_core CLI integration with eda_verify pipeline."""

from pathlib import Path

import pytest

# Test that PipelineConfig has validate_schema field
from verifier_core.validation import (
    SCHEMA_DIR,
    validate_json,
    validate_rulepack_manifest,
)

# Path to eda_verify source
EDA_VERIFY_SRC = (
    Path(__file__).parent.parent.parent / "src" / "eda_verifier" / "eda_verify" / "src"
)


@pytest.fixture
def eda_verify_path(monkeypatch):
    """Add eda_verify to sys.path with automatic cleanup."""
    monkeypatch.syspath_prepend(str(EDA_VERIFY_SRC))
    return str(EDA_VERIFY_SRC)


class TestPipelineConfigValidateSchema:
    """Tests for validate_schema field in PipelineConfig."""

    def test_pipeline_config_has_validate_schema_field(self, eda_verify_path):
        """PipelineConfig should have validate_schema field."""
        try:
            from eda_verify.pipeline import PipelineConfig

            config = PipelineConfig()
            assert hasattr(config, "validate_schema")
            assert config.validate_schema is False  # default
        except ImportError:
            pytest.skip("eda_verify not available")

    def test_pipeline_config_validate_schema_can_be_true(self, eda_verify_path):
        """PipelineConfig should accept validate_schema=True."""
        try:
            from eda_verify.pipeline import PipelineConfig

            config = PipelineConfig(validate_schema=True)
            assert config.validate_schema is True
        except ImportError:
            pytest.skip("eda_verify not available")


class TestRulepackSchemaValidation:
    """Tests for rulepack manifest schema validation."""

    def test_valid_rulepack_manifest_passes(self):
        """Valid rulepack manifest should pass validation."""
        manifest = {
            "name": "test_pack",
            "version": "1.0.0",
            "description": "Test rulepack",
        }
        errors = validate_rulepack_manifest(manifest)
        # rulepack.schema.json is permissive for Phase0
        assert len(errors) == 0

    def test_rulepack_with_domain_tier_passes(self):
        """Rulepack with domain/tier fields should pass."""
        manifest = {
            "name": "mech_basic",
            "version": "1.0.0",
            "description": "Mechanical basic",
            "domain": "mech",
            "tier": 0,
        }
        errors = validate_rulepack_manifest(manifest)
        assert len(errors) == 0


class TestReportSchemaValidation:
    """Tests for verification report schema validation."""

    def test_valid_report_passes_validation(self):
        """Valid verification report should pass schema validation."""
        report = {
            "request": {
                "domain": "eda",
                "tier": 0,
                "artifacts": [{"kind": "board", "path": "/path/board.kicad_pcb"}],
            },
            "status": "PASS",
            "findings": [],
            "unknowns": [],
            "evidence": [],
        }
        schema_path = SCHEMA_DIR / "verification_report.schema.json"
        if schema_path.exists():
            errors = validate_json(report, schema_path=str(schema_path))
            assert len(errors) == 0, f"Unexpected errors: {errors}"
        else:
            pytest.skip("verification_report.schema.json not found")

    def test_invalid_report_fails_validation(self):
        """Invalid verification report should fail schema validation."""
        report = {
            # Missing required 'request', 'status', etc.
            "findings": [],
        }
        schema_path = SCHEMA_DIR / "verification_report.schema.json"
        if schema_path.exists():
            errors = validate_json(report, schema_path=str(schema_path))
            assert len(errors) > 0, "Expected validation errors"
        else:
            pytest.skip("verification_report.schema.json not found")


class TestSchemaValidationIntegration:
    """Integration tests for schema validation in pipeline."""

    def test_schema_warnings_collected_for_invalid_rulepack(self, eda_verify_path):
        """Pipeline should collect schema warnings for invalid rulepacks."""
        try:
            from eda_verify.pipeline import PipelineConfig, VerificationPipeline

            # Create a minimal config with validate_schema=True but no rulepacks
            config = PipelineConfig(validate_schema=True)
            pipeline = VerificationPipeline(config)

            # Should have empty schema_warnings since no rulepacks loaded
            assert hasattr(pipeline, "schema_warnings")
            assert isinstance(pipeline.schema_warnings, list)
        except ImportError:
            pytest.skip("eda_verify not available")


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_validate_schema_flag_in_parser(self, eda_verify_path):
        """CLI parser should have --validate-schema flag."""
        try:
            from eda_verify.cli import create_parser

            parser = create_parser()
            # Parse with --validate-schema flag
            args = parser.parse_args(["verify", "dummy.kicad_pro", "--validate-schema"])
            assert hasattr(args, "validate_schema")
            assert args.validate_schema is True
        except ImportError:
            pytest.skip("eda_verify not available")

    def test_validate_schema_default_false(self, eda_verify_path):
        """--validate-schema should default to False."""
        try:
            from eda_verify.cli import create_parser

            parser = create_parser()
            args = parser.parse_args(["verify", "dummy.kicad_pro"])
            assert args.validate_schema is False
        except ImportError:
            pytest.skip("eda_verify not available")
