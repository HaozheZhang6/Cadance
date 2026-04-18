"""Tests for mech Tier-0 verification rules."""

import json
from pathlib import Path

import pytest

from verifier_core.adapters.mech import MechOperation, OpParameter, OpsProgram
from verifier_core.models import Finding, Severity
from verifier_core.rulepack.mech_tier0 import (
    MechTier0Config,
    check_fillet_min_radius,
    check_hole_ld_ratio,
    check_hole_min_diameter,
    check_slot_width,
    check_wall_thickness,
    normalize_findings,
    run_mech_tier0,
)


def _has_no_violations(results: list) -> bool:
    """Check that results contain no violations (only INFO findings)."""
    for r in results:
        if isinstance(r, Finding) and r.severity != Severity.INFO:
            return False
    return True


def _count_violations(results: list) -> int:
    """Count non-INFO findings (actual violations)."""
    return sum(
        1 for r in results if isinstance(r, Finding) and r.severity != Severity.INFO
    )


TEST_PROJECTS_DIR = (
    Path(__file__).parent.parent.parent / "src" / "verifier_core" / "test_projects"
)


class TestMechTier0Config:
    """Tests for rule configuration."""

    def test_defaults(self):
        cfg = MechTier0Config()
        assert cfg.min_hole_diameter_mm == 0.5
        assert cfg.max_hole_ld_ratio == 10.0
        assert cfg.min_fillet_radius_mm == 0.2

    def test_from_dict(self):
        d = {"min_hole_diameter_mm": 1.0, "max_hole_ld_ratio": 5.0}
        cfg = MechTier0Config.from_dict(d)
        assert cfg.min_hole_diameter_mm == 1.0
        assert cfg.max_hole_ld_ratio == 5.0
        assert cfg.min_fillet_radius_mm == 0.2  # default


class TestCheckHoleMinDiameter:
    """Tests for hole minimum diameter check."""

    def test_pass_above_min(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[OpParameter(name="diameter", value=1.0, unit="mm")],
                )
            ]
        )
        results = check_hole_min_diameter(prog, MechTier0Config())
        assert _has_no_violations(results)  # Only INFO findings

    def test_fail_below_min(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[OpParameter(name="diameter", value=0.3, unit="mm")],
                )
            ],
        )
        results = check_hole_min_diameter(prog, MechTier0Config())
        assert len(results) == 1
        finding = results[0]
        assert isinstance(finding, Finding)
        assert finding.rule_id == "mech.hole_min_diameter"
        assert finding.severity == Severity.ERROR

    def test_missing_diameter_creates_unknown(self):
        prog = OpsProgram(operations=[MechOperation(primitive="hole", parameters=[])])
        results = check_hole_min_diameter(prog, MechTier0Config())
        assert len(results) == 1
        from verifier_core.models import Unknown

        assert isinstance(results[0], Unknown)

    def test_unit_conversion_inches(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[OpParameter(name="diameter", value=0.5, unit="in")],
                )
            ]
        )
        # 0.5 inch = 12.7mm, should pass
        results = check_hole_min_diameter(prog, MechTier0Config())
        assert _has_no_violations(results)

    def test_hole_diameter_alias(self):
        """hole_diameter alias should work for diameter check."""
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="hole_diameter", value=2.0, unit="mm")
                    ],
                )
            ]
        )
        results = check_hole_min_diameter(prog, MechTier0Config())
        assert _has_no_violations(results)  # Should pass

    def test_counterbore_hole(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="hole_counterbore",
                    parameters=[
                        OpParameter(name="diameter", value=0.2, unit="mm"),
                        OpParameter(name="counterbore_diameter", value=5.0, unit="mm"),
                    ],
                )
            ],
        )
        results = check_hole_min_diameter(prog, MechTier0Config())
        # Should check primary diameter (0.2mm < 0.5mm)
        assert len(results) == 1
        assert results[0].rule_id == "mech.hole_min_diameter"


class TestCheckHoleLdRatio:
    """Tests for hole L/D ratio check."""

    def test_pass_good_ratio(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="diameter", value=5.0, unit="mm"),
                        OpParameter(name="depth", value=20.0, unit="mm"),
                    ],
                )
            ]
        )
        # L/D = 20/5 = 4, should pass
        results = check_hole_ld_ratio(prog, MechTier0Config())
        assert _has_no_violations(results)

    def test_fail_high_ratio(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="diameter", value=2.0, unit="mm"),
                        OpParameter(name="depth", value=60.0, unit="mm"),
                    ],
                )
            ],
        )
        # L/D = 60/2 = 30 > 10
        results = check_hole_ld_ratio(prog, MechTier0Config())
        assert len(results) == 1
        finding = results[0]
        assert finding.rule_id == "mech.hole_max_ld_ratio"
        assert finding.severity == Severity.WARN

    def test_hole_depth_alias(self):
        """hole_depth alias should work for L/D ratio check."""
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="hole_diameter", value=2.0, unit="mm"),
                        OpParameter(name="hole_depth", value=60.0, unit="mm"),
                    ],
                )
            ],
        )
        # L/D = 60/2 = 30 > 10, should fail with WARN
        results = check_hole_ld_ratio(prog, MechTier0Config())
        assert len(results) == 1
        assert results[0].rule_id == "mech.hole_max_ld_ratio"

    def test_skip_missing_depth(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[OpParameter(name="diameter", value=5.0, unit="mm")],
                )
            ]
        )
        results = check_hole_ld_ratio(prog, MechTier0Config())
        assert _has_no_violations(results)  # Skip, don't error


class TestCheckWallThickness:
    """Tests for wall thickness check."""

    def test_pass_good_thickness(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="shell",
                    parameters=[OpParameter(name="thickness", value=2.0, unit="mm")],
                )
            ]
        )
        results = check_wall_thickness(prog, MechTier0Config())
        assert _has_no_violations(results)

    def test_fail_thin_wall(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="shell",
                    parameters=[OpParameter(name="thickness", value=0.5, unit="mm")],
                )
            ],
        )
        results = check_wall_thickness(prog, MechTier0Config())
        assert len(results) == 1
        assert results[0].rule_id == "mech.wall_thickness"

    def test_shell_with_non_thickness_params_skipped(self):
        """Shell ops with non-thickness params (like deburring) should be skipped."""
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="shell",
                    parameters=[
                        OpParameter(name="max_burr_height", value=0.1, unit="mm")
                    ],
                )
            ]
        )
        results = check_wall_thickness(prog, MechTier0Config())
        # Should skip, not create unknown
        assert _has_no_violations(results)


class TestCheckSlotWidth:
    """Tests for slot width check."""

    def test_pass_good_width(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="slot",
                    parameters=[OpParameter(name="width", value=2.0, unit="mm")],
                )
            ]
        )
        results = check_slot_width(prog, MechTier0Config())
        assert _has_no_violations(results)

    def test_fail_narrow_slot(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="slot",
                    parameters=[OpParameter(name="width", value=0.3, unit="mm")],
                )
            ],
        )
        # 0.3mm < 0.5mm min
        results = check_slot_width(prog, MechTier0Config())
        assert len(results) == 1
        assert results[0].rule_id == "mech.slot_width"

    def test_slot_width_alias(self):
        """slot_width alias should work for slot check."""
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="slot",
                    parameters=[OpParameter(name="slot_width", value=2.0, unit="mm")],
                )
            ]
        )
        results = check_slot_width(prog, MechTier0Config())
        assert _has_no_violations(results)  # Should pass with alias

    def test_groove_width_alias(self):
        """groove_width alias should work for groove check."""
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="groove",
                    parameters=[OpParameter(name="groove_width", value=0.3, unit="mm")],
                )
            ],
        )
        # 0.3mm < 0.5mm min
        results = check_slot_width(prog, MechTier0Config())
        assert len(results) == 1
        assert results[0].rule_id == "mech.slot_width"


class TestCheckFilletMinRadius:
    """Tests for fillet minimum radius check."""

    def test_pass_good_radius(self):
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="fillet",
                    parameters=[OpParameter(name="radius", value=2.0, unit="mm")],
                )
            ]
        )
        results = check_fillet_min_radius(prog, MechTier0Config())
        assert _has_no_violations(results)

    def test_fail_small_radius(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="fillet",
                    parameters=[OpParameter(name="radius", value=0.1, unit="mm")],
                )
            ],
        )
        results = check_fillet_min_radius(prog, MechTier0Config())
        assert len(results) == 1
        assert results[0].rule_id == "mech.fillet_min_radius"

    def test_missing_radius_creates_unknown(self):
        prog = OpsProgram(operations=[MechOperation(primitive="fillet", parameters=[])])
        results = check_fillet_min_radius(prog, MechTier0Config())
        assert len(results) == 1
        from verifier_core.models import Unknown

        assert isinstance(results[0], Unknown)

    def test_corner_radius_alias(self):
        """corner_radius alias should work for fillet check."""
        prog = OpsProgram(
            operations=[
                MechOperation(
                    primitive="fillet",
                    parameters=[
                        OpParameter(name="corner_radius", value=2.0, unit="mm")
                    ],
                )
            ]
        )
        results = check_fillet_min_radius(prog, MechTier0Config())
        assert _has_no_violations(results)  # Should pass, no unknown

    def test_edge_break_alias(self):
        """edge_break alias should work for fillet check."""
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="fillet",
                    parameters=[OpParameter(name="edge_break", value=0.1, unit="mm")],
                )
            ],
        )
        results = check_fillet_min_radius(prog, MechTier0Config())
        # 0.1mm < 0.2mm min, should create finding
        assert len(results) == 1
        assert results[0].rule_id == "mech.fillet_min_radius"


class TestRunMechTier0:
    """Tests for running all Tier-0 rules."""

    def test_all_pass(self):
        prog = OpsProgram(
            operations=[
                MechOperation(primitive="box"),
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="diameter", value=5.0, unit="mm"),
                        OpParameter(name="depth", value=10.0, unit="mm"),
                    ],
                ),
                MechOperation(
                    primitive="fillet",
                    parameters=[OpParameter(name="radius", value=2.0, unit="mm")],
                ),
            ]
        )
        result = run_mech_tier0(prog)
        assert result.passed
        assert _count_violations(result.findings) == 0  # Only INFO findings
        assert len(result.unknowns) == 0

    def test_multiple_failures(self):
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="diameter", value=0.3, unit="mm"),
                        OpParameter(name="depth", value=10.0, unit="mm"),
                    ],
                ),
                MechOperation(
                    primitive="fillet",
                    parameters=[OpParameter(name="radius", value=0.1, unit="mm")],
                ),
            ],
        )
        result = run_mech_tier0(prog)
        assert not result.passed
        # Should have findings for hole diameter and fillet radius
        rule_ids = {f.rule_id for f in result.findings}
        assert "mech.hole_min_diameter" in rule_ids
        assert "mech.fillet_min_radius" in rule_ids


class TestNormalizeFindings:
    """Tests for findings normalization."""

    def test_sort_by_severity(self):
        findings = [
            Finding(rule_id="rule1", severity=Severity.WARN, message="Warning"),
            Finding(rule_id="rule2", severity=Severity.ERROR, message="Error"),
        ]
        normalized = normalize_findings(findings)
        assert normalized[0]["rule_id"] == "rule2"  # ERROR first
        assert normalized[1]["rule_id"] == "rule1"  # WARN second

    def test_sort_by_rule_id(self):
        findings = [
            Finding(rule_id="rule_z", severity=Severity.ERROR, message="Z"),
            Finding(rule_id="rule_a", severity=Severity.ERROR, message="A"),
        ]
        normalized = normalize_findings(findings)
        assert normalized[0]["rule_id"] == "rule_a"
        assert normalized[1]["rule_id"] == "rule_z"

    def test_strips_finding_id(self):
        findings = [Finding(rule_id="rule1", severity=Severity.ERROR, message="Test")]
        normalized = normalize_findings(findings)
        assert "finding_id" not in normalized[0]

    def test_rounds_numeric_values(self):
        findings = [
            Finding(
                rule_id="rule1",
                severity=Severity.ERROR,
                message="Test",
                measured_value={"value": 0.123456789},
            )
        ]
        normalized = normalize_findings(findings)
        assert normalized[0]["measured_value"]["value"] == 0.1235


class TestTestProjectsRegression:
    """Regression tests using test_projects fixtures."""

    @pytest.fixture
    def test_projects(self):
        """Load all test project paths."""
        if not TEST_PROJECTS_DIR.exists():
            pytest.skip("test_projects directory not found")
        projects = {}
        for proj_dir in TEST_PROJECTS_DIR.iterdir():
            if proj_dir.is_dir() and proj_dir.name.startswith("mech_"):
                ops_file = proj_dir / "ops_program.json"
                expected_file = proj_dir / "expected_findings.json"
                if ops_file.exists() and expected_file.exists():
                    projects[proj_dir.name] = {
                        "ops_file": ops_file,
                        "expected_file": expected_file,
                    }
        return projects

    def test_mech_hole_too_small(self, test_projects):
        if "mech_hole_too_small" not in test_projects:
            pytest.skip("mech_hole_too_small fixture not found")

        proj = test_projects["mech_hole_too_small"]
        prog = OpsProgram.from_file(proj["ops_file"])
        result = run_mech_tier0(prog)

        with open(proj["expected_file"]) as f:
            expected = json.load(f)

        # Check status
        if expected["expected_status"] == "fail":
            assert not result.passed
        else:
            assert result.passed

        # Check rule IDs
        expected_rules = set(expected["expected_findings"]["rule_ids"])
        actual_rules = {f.rule_id for f in result.findings}
        assert expected_rules <= actual_rules

    def test_mech_golden_pass(self, test_projects):
        if "mech_golden_pass" not in test_projects:
            pytest.skip("mech_golden_pass fixture not found")

        proj = test_projects["mech_golden_pass"]
        prog = OpsProgram.from_file(proj["ops_file"])
        result = run_mech_tier0(prog)

        assert result.passed
        assert _count_violations(result.findings) == 0  # Only INFO findings

    def test_mech_high_ld_ratio(self, test_projects):
        if "mech_high_ld_ratio" not in test_projects:
            pytest.skip("mech_high_ld_ratio fixture not found")

        proj = test_projects["mech_high_ld_ratio"]
        prog = OpsProgram.from_file(proj["ops_file"])
        result = run_mech_tier0(prog)

        with open(proj["expected_file"]) as f:
            expected = json.load(f)

        # L/D ratio produces warnings, so part still passes
        assert result.passed
        # But there should be warning findings
        expected_rules = set(expected["expected_findings"]["rule_ids"])
        actual_rules = {f.rule_id for f in result.findings}
        assert expected_rules <= actual_rules
        # Verify it's a warning
        for f in result.findings:
            if f.rule_id == "mech.hole_max_ld_ratio":
                assert f.severity == Severity.WARN

    def test_mech_small_fillet(self, test_projects):
        if "mech_small_fillet" not in test_projects:
            pytest.skip("mech_small_fillet fixture not found")

        proj = test_projects["mech_small_fillet"]
        prog = OpsProgram.from_file(proj["ops_file"])
        result = run_mech_tier0(prog)

        with open(proj["expected_file"]) as f:
            expected = json.load(f)

        # Fillet produces warnings, so part still passes
        assert result.passed
        # But there should be warning findings
        expected_rules = set(expected["expected_findings"]["rule_ids"])
        actual_rules = {f.rule_id for f in result.findings}
        assert expected_rules <= actual_rules
        # Verify it's a warning
        for f in result.findings:
            if f.rule_id == "mech.fillet_min_radius":
                assert f.severity == Severity.WARN

    def test_mech_missing_units(self, test_projects):
        if "mech_missing_units" not in test_projects:
            pytest.skip("mech_missing_units fixture not found")

        proj = test_projects["mech_missing_units"]
        prog = OpsProgram.from_file(proj["ops_file"])
        result = run_mech_tier0(prog)

        with open(proj["expected_file"]) as f:
            expected = json.load(f)

        # Should pass - default mm assumed
        if expected["expected_status"] == "pass":
            assert result.passed
            assert _count_violations(result.findings) == 0  # Only INFO findings


class TestFindingsDeterminism:
    """Tests for deterministic findings output."""

    def test_findings_determinism(self):
        """Run twice, compare normalized results."""
        proj_dir = TEST_PROJECTS_DIR / "mech_hole_too_small"
        if not proj_dir.exists():
            pytest.skip("mech_hole_too_small fixture not found")

        ops_file = proj_dir / "ops_program.json"
        prog = OpsProgram.from_file(ops_file)

        result1 = run_mech_tier0(prog)
        result2 = run_mech_tier0(prog)

        norm1 = normalize_findings(result1.findings)
        norm2 = normalize_findings(result2.findings)

        assert norm1 == norm2

    def test_findings_determinism_multiple_findings(self):
        """Determinism with multiple findings."""
        prog = OpsProgram(
            part_id="test",
            operations=[
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="diameter", value=0.3, unit="mm"),
                        OpParameter(name="depth", value=10.0, unit="mm"),
                    ],
                ),
                MechOperation(
                    primitive="hole",
                    parameters=[
                        OpParameter(name="diameter", value=0.4, unit="mm"),
                        OpParameter(name="depth", value=100.0, unit="mm"),
                    ],
                ),
                MechOperation(
                    primitive="fillet",
                    parameters=[OpParameter(name="radius", value=0.1, unit="mm")],
                ),
            ],
        )

        result1 = run_mech_tier0(prog)
        result2 = run_mech_tier0(prog)

        norm1 = normalize_findings(result1.findings)
        norm2 = normalize_findings(result2.findings)

        assert norm1 == norm2
        # Should have multiple findings
        assert len(norm1) >= 3
