"""Tests for Tier-0 part verification checks.

These tests verify DFM (Design for Manufacturing) checks on individual parts:
- Solid validity (B-Rep integrity) - checked at runtime
- Hole minimum diameter
- Hole L/D ratio
- Fillet minimum radius
- Units presence
"""

from pathlib import Path

from .conftest import load_expected_findings, load_mds


class TestSolidValidity:
    """Tests for solid geometry validity checks."""

    def test_valid_solid_no_finding(self, golden_pass_fixture: Path):
        """Valid B-Rep produces no BLOCKER finding."""
        mds = load_mds(golden_pass_fixture)
        expected = load_expected_findings(golden_pass_fixture)

        part = mds["parts"][0]
        # New schema: volume is in mass_props, not solid_validity
        assert part["mass_props"]["volume"] > 0
        assert expected["expected_findings"] == []

    def test_invalid_solid_blocker(self, invalid_geometry_fixture: Path):
        """Invalid B-Rep produces BLOCKER finding."""
        mds = load_mds(invalid_geometry_fixture)
        expected = load_expected_findings(invalid_geometry_fixture)

        part = mds["parts"][0]
        # New schema: zero/negative volume indicates invalid geometry
        assert part["mass_props"]["volume"] <= 0

        assert expected["expected_status"] == "fail"
        assert len(expected["expected_findings"]) == 1
        finding = expected["expected_findings"][0]
        assert finding["severity"] == "BLOCKER"
        assert finding["rule_id"] == "mech.tier0.degenerate_geometry"

    def test_zero_volume_blocker(self, invalid_geometry_fixture: Path):
        """Zero volume produces BLOCKER finding."""
        mds = load_mds(invalid_geometry_fixture)
        part = mds["parts"][0]

        # New schema: volume in mass_props
        assert part["mass_props"]["volume"] == 0.0


class TestHoleMinDiameter:
    """Tests for hole minimum diameter check."""

    def test_pass_above_min(self, golden_pass_fixture: Path):
        """Hole above minimum diameter produces no finding."""
        mds = load_mds(golden_pass_fixture)
        expected = load_expected_findings(golden_pass_fixture)

        # New schema: features are top-level, not nested in parts
        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]
        if holes:
            assert holes[0]["diameter"] >= 0.5
        assert expected["expected_findings"] == []

    def test_fail_below_min(self, hole_too_small_fixture: Path):
        """Hole below minimum diameter produces ERROR finding."""
        mds = load_mds(hole_too_small_fixture)
        expected = load_expected_findings(hole_too_small_fixture)

        # New schema: features are top-level
        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]
        assert len(holes) > 0
        assert holes[0]["diameter"] < 0.5

        assert expected["expected_status"] == "fail"
        finding = expected["expected_findings"][0]
        assert finding["rule_id"] == "mech.tier0.hole_min_diameter"
        assert finding["severity"] == "ERROR"


class TestHoleLdRatio:
    """Tests for hole L/D ratio check."""

    def test_pass_good_ratio(self, golden_pass_fixture: Path):
        """Hole with acceptable L/D produces no warning."""
        mds = load_mds(golden_pass_fixture)
        expected = load_expected_findings(golden_pass_fixture)

        # New schema: features are top-level
        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]
        if holes:
            diameter = holes[0]["diameter"]
            depth = holes[0]["depth"]
            ld_ratio = depth / diameter
            assert ld_ratio <= 10.0
        assert expected["expected_findings"] == []

    def test_warn_high_ratio(self, high_ld_ratio_fixture: Path):
        """Hole with high L/D produces WARN finding."""
        mds = load_mds(high_ld_ratio_fixture)
        expected = load_expected_findings(high_ld_ratio_fixture)

        # New schema: features are top-level with ld_ratio precomputed
        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]
        assert len(holes) > 0

        # L/D can be precomputed or calculated
        if "ld_ratio" in holes[0]:
            ld_ratio = holes[0]["ld_ratio"]
        else:
            diameter = holes[0]["diameter"]
            depth = holes[0]["depth"]
            ld_ratio = depth / diameter
        assert ld_ratio > 10.0

        assert expected["expected_status"] == "warn"
        finding = expected["expected_findings"][0]
        assert finding["rule_id"] == "mech.tier0.hole_ld_ratio"
        assert finding["severity"] == "WARN"


class TestFilletMinRadius:
    """Tests for fillet minimum radius check."""

    def test_pass_good_radius(self, golden_pass_fixture: Path):
        """Fillet above minimum produces no warning."""
        expected = load_expected_findings(golden_pass_fixture)
        assert expected["expected_findings"] == []

    def test_warn_small_radius(self, small_fillet_fixture: Path):
        """Fillet below minimum produces WARN finding."""
        mds = load_mds(small_fillet_fixture)
        expected = load_expected_findings(small_fillet_fixture)

        # New schema: features are top-level
        features = mds.get("features", [])
        fillets = [f for f in features if f.get("feature_type") == "fillet"]
        assert len(fillets) > 0
        assert fillets[0]["radius"] < 0.2

        assert expected["expected_status"] == "warn"
        finding = expected["expected_findings"][0]
        assert finding["rule_id"] == "mech.tier0.fillet_min_radius"
        assert finding["severity"] == "WARN"


class TestUnitsRequired:
    """Tests for units presence check."""

    def test_pass_with_units(self, golden_pass_fixture: Path):
        """MDS with units produces no Unknown."""
        mds = load_mds(golden_pass_fixture)
        expected = load_expected_findings(golden_pass_fixture)

        # New schema: units are at root level, not in parts
        assert "units" in mds
        assert mds["units"]["length"] == "mm"
        assert expected.get("expected_unknowns", []) == []

    def test_unknown_missing_units(self, missing_units_fixture: Path):
        """MDS without units produces blocking Unknown."""
        mds = load_mds(missing_units_fixture)
        expected = load_expected_findings(missing_units_fixture)

        # New schema: check units at root level
        assert "units" not in mds or mds.get("units") is None

        assert expected["expected_status"] == "unknown"
        unknowns = expected.get("expected_unknowns", [])
        assert len(unknowns) == 1
        assert unknowns[0]["blocking"] is True
        assert unknowns[0]["created_by_rule_id"] == "mech.tier0.units_present"
