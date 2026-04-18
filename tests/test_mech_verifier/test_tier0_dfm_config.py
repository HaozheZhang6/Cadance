"""Tests for configurable DFM checks.

Verifies that parameter overrides change thresholds in findings.
"""

from mech_verify.config import MechVerifyConfig
from mech_verify.tier0_dfm import (
    check_fillet_min_radius,
    check_hole_ld_ratio,
    check_hole_min_diameter,
    check_wall_thickness,
)
from verifier_core.models import Finding, Severity, Unknown


class TestHoleMinDiameterConfig:
    """Tests for configurable hole minimum diameter."""

    def test_default_threshold_1mm(self):
        """Default config uses 1.0mm minimum diameter."""
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 0.8,
                }
            ]
        }
        config = MechVerifyConfig()  # Default: 1.0mm
        results = check_hole_min_diameter(mds, config)

        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].severity == Severity.ERROR
        assert "0.80mm below minimum 1.00mm" in results[0].message

    def test_override_threshold_0_5mm(self):
        """Overriding min_hole_diameter_mm changes threshold."""
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 0.8,
                }
            ]
        }
        config = MechVerifyConfig(min_hole_diameter_mm=0.5)
        results = check_hole_min_diameter(mds, config)

        # 0.8mm passes with 0.5mm threshold
        assert len(results) == 0

    def test_override_threshold_2mm(self):
        """Higher threshold produces finding for previously passing hole."""
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 1.5,
                }
            ]
        }
        config_default = MechVerifyConfig()  # 1.0mm - passes
        config_strict = MechVerifyConfig(min_hole_diameter_mm=2.0)  # 2.0mm - fails

        results_default = check_hole_min_diameter(mds, config_default)
        results_strict = check_hole_min_diameter(mds, config_strict)

        assert len(results_default) == 0
        assert len(results_strict) == 1
        assert isinstance(results_strict[0], Finding)
        assert "1.50mm below minimum 2.00mm" in results_strict[0].message


class TestSourceSpecIdsInFindings:
    """Tests for source_spec_ids threading from features into findings."""

    def test_hole_min_diameter_finding_carries_spec_ids(self):
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 0.3,
                    "source_spec_ids": ["S1.1.1"],
                }
            ]
        }
        results = check_hole_min_diameter(mds)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].source_spec_ids == ["S1.1.1"]

    def test_hole_ld_ratio_finding_carries_spec_ids(self):
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 2.0,
                    "depth": 25.0,
                    "source_spec_ids": ["S1.1.2"],
                }
            ]
        }
        results = check_hole_ld_ratio(mds)
        findings = [r for r in results if isinstance(r, Finding)]
        assert len(findings) == 1
        assert findings[0].source_spec_ids == ["S1.1.2"]

    def test_fillet_min_radius_finding_carries_spec_ids(self):
        mds = {
            "features": [
                {
                    "feature_id": "fillet1",
                    "feature_type": "fillet",
                    "object_ref": "mech://feature/fillet1",
                    "radius": 0.1,
                    "source_spec_ids": ["S2.1"],
                }
            ]
        }
        results = check_fillet_min_radius(mds)
        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].source_spec_ids == ["S2.1"]

    def test_wall_thickness_finding_carries_spec_ids(self):
        mds = {
            "features": [
                {
                    "feature_id": "shell1",
                    "feature_type": "shell",
                    "object_ref": "mech://feature/shell1",
                    "min_wall_thickness": 0.5,
                    "source_spec_ids": ["S3.1"],
                }
            ]
        }
        results = check_wall_thickness(mds)
        findings = [r for r in results if isinstance(r, Finding)]
        assert len(findings) == 1
        assert findings[0].source_spec_ids == ["S3.1"]

    def test_no_spec_ids_default_empty(self):
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 0.3,
                }
            ]
        }
        results = check_hole_min_diameter(mds)
        assert len(results) == 1
        assert results[0].source_spec_ids == []

    def test_wall_thickness_unknown_carries_spec_ids(self):
        mds = {
            "features": [
                {
                    "feature_id": "shell1",
                    "feature_type": "shell",
                    "object_ref": "mech://feature/shell1",
                    "source_spec_ids": ["S3.1"],
                }
            ]
        }
        results = check_wall_thickness(mds)
        unknowns = [r for r in results if isinstance(r, Unknown)]
        assert len(unknowns) == 1
        assert unknowns[0].source_spec_ids == ["S3.1"]


class TestHoleLdRatioConfig:
    """Tests for configurable hole L/D ratio."""

    def test_default_threshold_10(self):
        """Default config uses 10.0 max L/D ratio."""
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 2.0,
                    "depth": 25.0,  # L/D = 12.5
                }
            ]
        }
        config = MechVerifyConfig()  # Default: 10.0
        results = check_hole_ld_ratio(mds, config)

        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].severity == Severity.WARN
        assert "12.50 exceeds maximum 10.00" in results[0].message

    def test_override_threshold_15(self):
        """Overriding max_hole_ld_ratio changes threshold."""
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "diameter": 2.0,
                    "depth": 25.0,  # L/D = 12.5
                }
            ]
        }
        config = MechVerifyConfig(max_hole_ld_ratio=15.0)
        results = check_hole_ld_ratio(mds, config)

        # L/D 12.5 passes with 15.0 threshold
        assert len(results) == 0

    def test_uses_precomputed_ld_ratio(self):
        """Uses precomputed ld_ratio field if available."""
        mds = {
            "features": [
                {
                    "feature_id": "hole1",
                    "feature_type": "hole",
                    "object_ref": "mech://feature/hole1",
                    "ld_ratio": 12.5,
                }
            ]
        }
        config = MechVerifyConfig()  # Default: 10.0
        results = check_hole_ld_ratio(mds, config)

        assert len(results) == 1
        assert isinstance(results[0], Finding)


class TestFilletMinRadiusConfig:
    """Tests for configurable fillet minimum radius."""

    def test_default_threshold_0_2mm(self):
        """Default config uses 0.2mm minimum radius."""
        mds = {
            "features": [
                {
                    "feature_id": "fillet1",
                    "feature_type": "fillet",
                    "object_ref": "mech://feature/fillet1",
                    "radius": 0.1,
                }
            ]
        }
        config = MechVerifyConfig()  # Default: 0.2mm
        results = check_fillet_min_radius(mds, config)

        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].severity == Severity.WARN
        assert "0.10mm below minimum 0.20mm" in results[0].message

    def test_override_threshold_0_5mm(self):
        """Overriding min_fillet_radius_mm changes threshold."""
        mds = {
            "features": [
                {
                    "feature_id": "fillet1",
                    "feature_type": "fillet",
                    "object_ref": "mech://feature/fillet1",
                    "radius": 0.3,
                }
            ]
        }
        config_lenient = MechVerifyConfig(min_fillet_radius_mm=0.2)  # Passes
        config_strict = MechVerifyConfig(min_fillet_radius_mm=0.5)  # Fails

        results_lenient = check_fillet_min_radius(mds, config_lenient)
        results_strict = check_fillet_min_radius(mds, config_strict)

        assert len(results_lenient) == 0
        assert len(results_strict) == 1


class TestWallThicknessConfig:
    """Tests for configurable wall thickness."""

    def test_default_threshold_1mm(self):
        """Default config uses 1.0mm minimum wall thickness."""
        mds = {
            "features": [
                {
                    "feature_id": "shell1",
                    "feature_type": "shell",
                    "object_ref": "mech://feature/shell1",
                    "min_wall_thickness": 0.5,
                }
            ]
        }
        config = MechVerifyConfig()  # Default: 1.0mm
        results = check_wall_thickness(mds, config)

        assert len(results) == 1
        assert isinstance(results[0], Finding)
        assert results[0].severity == Severity.WARN
        assert "0.50mm below minimum 1.00mm" in results[0].message

    def test_override_threshold_2mm(self):
        """Overriding min_wall_thickness_mm changes threshold."""
        mds = {
            "features": [
                {
                    "feature_id": "pocket1",
                    "feature_type": "pocket",
                    "object_ref": "mech://feature/pocket1",
                    "min_wall_thickness": 1.5,
                }
            ]
        }
        config_default = MechVerifyConfig()  # 1.0mm - passes
        config_strict = MechVerifyConfig(min_wall_thickness_mm=2.0)  # 2.0mm - fails

        results_default = check_wall_thickness(mds, config_default)
        results_strict = check_wall_thickness(mds, config_strict)

        assert len(results_default) == 0
        assert len(results_strict) == 1

    def test_only_warns_for_shell_when_missing(self):
        """Only creates Unknown for shell features missing thickness."""
        mds = {
            "features": [
                {
                    "feature_id": "shell1",
                    "feature_type": "shell",
                    "object_ref": "mech://feature/shell1",
                },
                {
                    "feature_id": "pocket1",
                    "feature_type": "pocket",
                    "object_ref": "mech://feature/pocket1",
                },
            ]
        }
        config = MechVerifyConfig()
        results = check_wall_thickness(mds, config)

        # Only shell creates Unknown
        unknowns = [r for r in results if isinstance(r, Unknown)]
        assert len(unknowns) == 1
        assert "shell1" in unknowns[0].summary
