"""Tests for wall thickness extraction from ops programs.

Per Phase 3 requirement:
- Wall thickness should be extracted from shell operations in ops programs
- Feature should have min_wall_thickness field
- DFM check should be able to validate against threshold
"""

import json


class TestShellFeatureExtraction:
    """Tests for shell feature extraction from ops programs."""

    def test_shell_operation_extracted(self, tmp_path):
        """Shell operation with thickness is extracted as feature."""
        from mech_verify.mds.builder import MDSBuilder

        # Create ops program with shell operation
        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [
                        {"name": "thickness", "value": 2.5, "unit": "mm"},
                    ],
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        # Create minimal MDS
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # Should have shell feature with wall thickness
        assert len(mds["features"]) == 1
        feature = mds["features"][0]
        assert feature["feature_type"] == "shell"
        assert feature["feature_id"] == "shell_0"
        assert feature["min_wall_thickness"] == 2.5
        assert feature["from_ops_program"] is True
        assert feature["op_index"] == 0

    def test_shell_without_thickness_skipped(self, tmp_path):
        """Shell operation without thickness parameter is skipped."""
        from mech_verify.mds.builder import MDSBuilder

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [],  # No thickness
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # No feature extracted
        assert len(mds["features"]) == 0

    def test_multiple_shell_operations(self, tmp_path):
        """Multiple shell operations are extracted with unique IDs."""
        from mech_verify.mds.builder import MDSBuilder

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [{"name": "thickness", "value": 2.0, "unit": "mm"}],
                },
                {
                    "primitive": "shell",
                    "parameters": [{"name": "thickness", "value": 3.0, "unit": "mm"}],
                },
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        assert len(mds["features"]) == 2
        assert mds["features"][0]["feature_id"] == "shell_0"
        assert mds["features"][0]["min_wall_thickness"] == 2.0
        assert mds["features"][1]["feature_id"] == "shell_1"
        assert mds["features"][1]["min_wall_thickness"] == 3.0

    def test_shell_object_ref_format(self, tmp_path):
        """Shell feature has correct object_ref format."""
        from mech_verify.mds.builder import MDSBuilder

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

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [
                {"part_id": "my_part_id", "object_ref": "mech://part/my_part_id"}
            ],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        feature = mds["features"][0]
        assert (
            feature["object_ref"] == "mech://part/my_part_id/feature/shell/shell_0"
        ), "object_ref should reference part and feature_type and feature_id"


class TestMixedFeatureExtraction:
    """Tests for extracting multiple feature types together."""

    def test_holes_fillets_and_shells_together(self, tmp_path):
        """Holes, fillets, and shells are all extracted."""
        from mech_verify.mds.builder import MDSBuilder

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "hole",
                    "parameters": [
                        {"name": "diameter", "value": 5.0, "unit": "mm"},
                        {"name": "depth", "value": 10.0, "unit": "mm"},
                    ],
                },
                {
                    "primitive": "fillet",
                    "parameters": [{"name": "radius", "value": 2.0, "unit": "mm"}],
                },
                {
                    "primitive": "shell",
                    "parameters": [{"name": "thickness", "value": 3.0, "unit": "mm"}],
                },
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # Should have all three features (sorted by type then id)
        assert len(mds["features"]) == 3

        # Features are sorted: fillet, hole, shell (alphabetical by type)
        types = [f["feature_type"] for f in mds["features"]]
        assert types == sorted(types), "Features should be sorted by type"

        # Check each feature type exists
        feature_types = {f["feature_type"] for f in mds["features"]}
        assert feature_types == {"hole", "fillet", "shell"}

    def test_feature_sorting_with_shells(self, tmp_path):
        """Features are sorted by type (fillet, hole, shell)."""
        from mech_verify.mds.builder import MDSBuilder

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [{"name": "thickness", "value": 2.0, "unit": "mm"}],
                },
                {
                    "primitive": "hole",
                    "parameters": [{"name": "diameter", "value": 5.0, "unit": "mm"}],
                },
                {
                    "primitive": "fillet",
                    "parameters": [{"name": "radius", "value": 1.0, "unit": "mm"}],
                },
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # Should be sorted: fillet, hole, shell
        types = [f["feature_type"] for f in mds["features"]]
        assert types == ["fillet", "hole", "shell"]


class TestWallThicknessDFMCheck:
    """Tests for DFM check using extracted wall thickness."""

    def test_thin_wall_produces_warning(self, tmp_path):
        """Wall thickness below threshold produces WARN finding."""
        from mech_verify.mds.builder import MDSBuilder
        from mech_verify.tier0_dfm import check_wall_thickness

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [
                        {"name": "thickness", "value": 0.5, "unit": "mm"}
                    ],  # Below default 1.0mm
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # Run DFM check
        results = check_wall_thickness(mds)

        # Should have WARN finding
        findings = [r for r in results if hasattr(r, "severity")]
        assert len(findings) == 1
        assert findings[0].rule_id == "mech.tier0.wall_thickness"
        assert findings[0].severity.value == "WARN"
        assert findings[0].measured_value["min_wall_thickness"] == 0.5

    def test_adequate_wall_passes(self, tmp_path):
        """Wall thickness above threshold produces no finding."""
        from mech_verify.mds.builder import MDSBuilder
        from mech_verify.tier0_dfm import check_wall_thickness

        ops_program = {
            "schema_version": "ops.v1",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [
                        {"name": "thickness", "value": 2.5, "unit": "mm"}
                    ],  # Above default 1.0mm
                }
            ],
        }
        ops_path = tmp_path / "ops.json"
        ops_path.write_text(json.dumps(ops_program))

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # Run DFM check
        results = check_wall_thickness(mds)

        # Should have no findings
        findings = [r for r in results if hasattr(r, "severity")]
        assert len(findings) == 0

    def test_wall_thickness_custom_threshold(self, tmp_path):
        """Wall thickness check uses custom threshold from config."""
        from mech_verify.config import MechVerifyConfig
        from mech_verify.mds.builder import MDSBuilder
        from mech_verify.tier0_dfm import check_wall_thickness

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

        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [],
            "parts": [{"part_id": "test_part", "object_ref": "mech://part/test_part"}],
            "features": [],
        }

        builder = MDSBuilder()
        mds = builder.merge_ops_program(mds, ops_path)

        # Run with custom threshold of 2.0mm
        config = MechVerifyConfig(min_wall_thickness_mm=2.0)
        results = check_wall_thickness(mds, config)

        # 1.5mm should fail against 2.0mm threshold
        findings = [r for r in results if hasattr(r, "severity")]
        assert len(findings) == 1
        assert findings[0].limit["min_wall_thickness_mm"] == 2.0
