"""Tests for MDS schema validation."""

from pathlib import Path

import jsonschema
import pytest

from mech_verify.mds.io import read_mds
from mech_verify.mds.validator import (
    MDSValidationError,
    _load_schema,
    is_valid_mds,
    validate_mds,
    validate_mds_strict,
)


class TestSchemaLoading:
    """Tests for schema loading via importlib.resources."""

    def test_schema_loads_successfully(self):
        """Schema should load from package data using importlib.resources."""
        schema = _load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "type" in schema
        assert schema["type"] == "object"

    def test_schema_has_required_fields(self):
        """Schema should define required core fields."""
        schema = _load_schema()
        assert "required" in schema
        required_fields = schema["required"]
        assert "schema_version" in required_fields
        assert "domain" in required_fields
        assert "units" in required_fields

    def test_schema_caching_works(self):
        """Schema should be cached after first load."""
        schema1 = _load_schema()
        schema2 = _load_schema()
        # Should be the same object (cached)
        assert schema1 is schema2


class TestValidateMds:
    """Tests for validate_mds."""

    def test_valid_minimal_mds(self):
        """Minimal valid MDS should pass validation."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
        }
        errors = validate_mds(mds)
        assert errors == []

    def test_valid_full_mds(self):
        """Full valid MDS should pass validation."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [{"path": "/test.step", "kind": "step_part"}],
            "parts": [
                {
                    "part_id": "test_part",
                    "name": "Test Part",
                    "object_ref": "mech://part/test_part",
                    "mass_props": {
                        "volume": 1000.0,
                        "surface_area": 600.0,
                        "center_of_mass": [5.0, 5.0, 5.0],
                        "bbox": {
                            "min_pt": [0.0, 0.0, 0.0],
                            "max_pt": [10.0, 10.0, 10.0],
                            "dimensions": [10.0, 10.0, 10.0],
                        },
                    },
                }
            ],
            "assemblies": [],
            "features": [
                {
                    "feature_id": "hole_0",
                    "feature_type": "hole",
                    "object_ref": "mech://part/test_part/feature/hole_0",
                    "diameter": 5.0,
                    "depth": 10.0,
                }
            ],
            "pmi": {
                "has_semantic_pmi": False,
                "has_graphical_pmi": False,
            },
        }
        errors = validate_mds(mds)
        assert errors == []

    def test_missing_schema_version(self):
        """Missing schema_version should fail."""
        mds = {
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0
        assert any("schema_version" in e for e in errors)

    def test_missing_domain(self):
        """Missing domain should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "parts": [],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0
        assert any("domain" in e for e in errors)

    def test_wrong_schema_version(self):
        """Wrong schema_version should fail."""
        mds = {
            "schema_version": "wrong.version",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0

    def test_wrong_domain(self):
        """Wrong domain should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "wrong",
            "units": {"length": "mm"},
            "parts": [],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0

    def test_invalid_unit(self):
        """Invalid unit should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "invalid_unit"},
            "parts": [],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0

    def test_invalid_feature_type(self):
        """Invalid feature type should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
            "features": [
                {
                    "feature_id": "feat_0",
                    "feature_type": "invalid_type",
                    "object_ref": "mech://part/test/feature/feat_0",
                }
            ],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0

    def test_invalid_center_of_mass_length(self):
        """Center of mass with wrong length should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [
                {
                    "part_id": "test",
                    "object_ref": "mech://part/test",
                    "mass_props": {
                        "center_of_mass": [1.0, 2.0],  # Should be 3 elements
                    },
                }
            ],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0

    def test_extra_properties_fail(self):
        """Extra properties should fail (additionalProperties: false)."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
            "unknown_field": "should_fail",
        }
        errors = validate_mds(mds)
        assert len(errors) > 0

    def test_raise_on_error(self):
        """raise_on_error=True should raise ValidationError."""
        mds = {"invalid": "mds"}

        with pytest.raises(jsonschema.ValidationError):
            validate_mds(mds, raise_on_error=True)


class TestIsValidMds:
    """Tests for is_valid_mds."""

    def test_valid_returns_true(self):
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
        }
        assert is_valid_mds(mds) is True

    def test_invalid_returns_false(self):
        mds = {"invalid": "mds"}
        assert is_valid_mds(mds) is False


class TestValidateMdsStrict:
    """Tests for validate_mds_strict."""

    def test_valid_passes(self):
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [],
        }
        # Should not raise
        validate_mds_strict(mds)

    def test_invalid_raises(self):
        mds = {"invalid": "mds"}
        with pytest.raises(MDSValidationError) as exc_info:
            validate_mds_strict(mds)
        assert len(exc_info.value.errors) > 0

    def test_error_message_contains_all_errors(self):
        mds = {}  # Missing all required fields
        with pytest.raises(MDSValidationError) as exc_info:
            validate_mds_strict(mds)
        message = str(exc_info.value)
        assert "schema_version" in message
        assert "domain" in message


class TestAssemblyValidation:
    """Tests for assembly validation including occurrences."""

    def test_valid_assembly_with_occurrences(self):
        """Assembly with occurrences should pass."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [
                {"part_id": "part_a", "object_ref": "mech://part/part_a"},
                {"part_id": "part_b", "object_ref": "mech://part/part_b"},
            ],
            "assemblies": [
                {
                    "assembly_id": "asm_1",
                    "name": "Test Assembly",
                    "object_ref": "mech://assembly/asm_1",
                    "occurrences": [
                        {
                            "occurrence_id": "occ_0",
                            "part_id": "part_a",
                            "transform": [
                                1.0,
                                0.0,
                                0.0,
                                0.0,
                                0.0,
                                1.0,
                                0.0,
                                0.0,
                                0.0,
                                0.0,
                                1.0,
                                0.0,
                                0.0,
                                0.0,
                                0.0,
                                1.0,
                            ],
                        },
                        {
                            "occurrence_id": "occ_1",
                            "part_id": "part_b",
                            "transform": [
                                1.0,
                                0.0,
                                0.0,
                                10.0,
                                0.0,
                                1.0,
                                0.0,
                                0.0,
                                0.0,
                                0.0,
                                1.0,
                                0.0,
                                0.0,
                                0.0,
                                0.0,
                                1.0,
                            ],
                        },
                    ],
                }
            ],
        }
        errors = validate_mds(mds)
        assert errors == []

    def test_occurrence_missing_required_field(self):
        """Occurrence missing occurrence_id should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [{"part_id": "part_a", "object_ref": "mech://part/part_a"}],
            "assemblies": [
                {
                    "assembly_id": "asm_1",
                    "occurrences": [
                        {
                            "part_id": "part_a",
                            # Missing occurrence_id
                        }
                    ],
                }
            ],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0
        assert any("occurrence_id" in e for e in errors)

    def test_occurrence_transform_wrong_length(self):
        """Occurrence transform with wrong length should fail."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm"},
            "parts": [{"part_id": "part_a", "object_ref": "mech://part/part_a"}],
            "assemblies": [
                {
                    "assembly_id": "asm_1",
                    "occurrences": [
                        {
                            "occurrence_id": "occ_0",
                            "part_id": "part_a",
                            "transform": [1.0, 0.0, 0.0],  # Should be 16 elements
                        }
                    ],
                }
            ],
        }
        errors = validate_mds(mds)
        assert len(errors) > 0


class TestTestProjectsValidation:
    """Validate all MDS files in test_projects."""

    # Files that are intentionally invalid for testing error handling
    INTENTIONALLY_INVALID = {
        "step_missing_units",  # Tests missing units handling
    }

    # Files in old schema format (not current schema)
    OLD_SCHEMA_FILES = {
        "expected_mds.json",  # Old 0.1.0 schema format
    }

    @pytest.fixture
    def test_projects_path(self):
        """Get the path to test_projects."""
        return (
            Path(__file__).parent.parent.parent
            / "src"
            / "mech_verifier"
            / "test_projects"
        )

    def test_all_test_projects_mds_valid(self, test_projects_path):
        """All MDS input files in test_projects should validate (except intentionally invalid)."""
        mds_files = list(test_projects_path.rglob("inputs/mds.json"))

        assert len(mds_files) > 0, "No MDS files found in test_projects"

        failed = []
        for mds_file in mds_files:
            # Skip intentionally invalid test cases
            if any(invalid in str(mds_file) for invalid in self.INTENTIONALLY_INVALID):
                continue

            mds = read_mds(mds_file)
            errors = validate_mds(mds)
            if errors:
                failed.append((mds_file, errors))

        if failed:
            msg = "MDS validation failures:\n"
            for path, errors in failed:
                msg += f"\n{path}:\n"
                for e in errors:
                    msg += f"  - {e}\n"
            pytest.fail(msg)

    def test_intentionally_invalid_files_are_invalid(self, test_projects_path):
        """Verify that intentionally invalid MDS files actually fail validation."""
        for invalid_dir in self.INTENTIONALLY_INVALID:
            mds_file = test_projects_path / invalid_dir / "inputs" / "mds.json"
            if mds_file.exists():
                mds = read_mds(mds_file)
                errors = validate_mds(mds)
                assert (
                    len(errors) > 0
                ), f"{mds_file} should be invalid but passed validation"
