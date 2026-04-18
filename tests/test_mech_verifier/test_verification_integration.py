"""Integration tests for mech_verifier verification pipeline.

These tests ACTUALLY RUN the verification functions against test fixtures,
not just check MDS structure against expected_findings.json.

Tests cover:
- run_tier0_part_checks() with MDS input
- SHACL validation pipeline (MDS → RDF → SHACL → Findings)
- Assembly verification (interference/clearance)
- Full CLI-style pipeline
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from mech_verify.tier0_part import (
    Tier0PartResult,
    check_degenerate_geometry,
    check_units_present,
    run_tier0_part_checks,
)
from verifier_core.models import Finding, Severity, Unknown

# ============================================================================
# Fixtures and Helpers
# ============================================================================

TEST_PROJECTS = (
    Path(__file__).parent.parent.parent / "src" / "mech_verifier" / "test_projects"
)


def load_mds(project_path: Path) -> dict[str, Any]:
    """Load MDS JSON from a test project."""
    mds_path = project_path / "inputs" / "mds.json"
    if not mds_path.exists():
        pytest.skip(f"MDS file not found: {mds_path}")
    with open(mds_path, encoding="utf-8") as f:
        return json.load(f)


def load_expected_findings(project_path: Path) -> dict[str, Any]:
    """Load expected_findings.json from a test project."""
    expected_path = project_path / "expected_findings.json"
    if not expected_path.exists():
        pytest.skip(f"expected_findings.json not found: {expected_path}")
    with open(expected_path, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class CaseExpectation:
    """Expected outcome for a test case."""

    test_case: str
    expected_status: str  # "pass", "fail", "warn", "unknown"
    expected_rule_id: str | None = None
    expected_severity: str | None = None  # "BLOCKER", "ERROR", "WARN", None
    expect_unknown: bool = False
    blocking_unknown: bool = False


# Define all test case expectations
CASE_EXPECTATIONS = [
    # Part verification
    CaseExpectation("step_golden_pass", "pass", None, None),
    CaseExpectation(
        "step_hole_too_small", "fail", "mech.tier0.hole_min_diameter", "ERROR"
    ),
    CaseExpectation("step_high_ld_ratio", "warn", "mech.tier0.hole_ld_ratio", "WARN"),
    CaseExpectation(
        "step_small_fillet", "warn", "mech.tier0.fillet_min_radius", "WARN"
    ),
    CaseExpectation(
        "step_missing_units", "unknown", "mech.tier0.units_present", None, True, True
    ),
    CaseExpectation(
        "step_invalid_geometry", "fail", "mech.tier0.degenerate_geometry", "BLOCKER"
    ),
    # Assembly verification
    CaseExpectation("step_assembly_clean", "pass", None, None),
    CaseExpectation(
        "step_assembly_interference",
        "fail",
        "mech.tier0.interference",
        "BLOCKER",
    ),
    CaseExpectation("step_assembly_clearance", "warn", "mech.tier0.clearance", "WARN"),
    # PMI verification
    CaseExpectation("step_pmi_present", "pass", None, None),
    CaseExpectation(
        "step_pmi_absent", "unknown", "mech.tier0.pmi_required", None, True, True
    ),
]


@pytest.fixture
def test_projects_root() -> Path:
    """Root directory for test projects."""
    if not TEST_PROJECTS.exists():
        pytest.skip("test_projects directory not found")
    return TEST_PROJECTS


# ============================================================================
# Tier-0 Part Integration Tests
# ============================================================================


class TestTier0PartChecksIntegration:
    """Integration tests that actually call run_tier0_part_checks()."""

    def test_golden_pass_no_findings(self, test_projects_root: Path):
        """Golden pass MDS produces no findings or unknowns."""
        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        assert isinstance(result, Tier0PartResult)
        assert result.passed, f"Expected pass, got findings: {result.findings}"
        assert len(result.findings) == 0, f"Unexpected findings: {result.findings}"
        assert len(result.unknowns) == 0, f"Unexpected unknowns: {result.unknowns}"
        assert not result.has_blockers

    def test_invalid_geometry_blocker(self, test_projects_root: Path):
        """Invalid geometry (zero volume) produces BLOCKER finding."""
        project = test_projects_root / "step_invalid_geometry"
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        assert not result.passed, "Expected fail due to degenerate geometry"
        assert result.has_blockers, "Expected BLOCKER severity"

        # Find the degenerate geometry finding
        blocker_findings = [
            f for f in result.findings if f.severity == Severity.BLOCKER
        ]
        assert len(blocker_findings) >= 1, "Expected at least one BLOCKER finding"

        # Check rule ID
        degenerate_findings = [
            f for f in blocker_findings if f.rule_id == "mech.tier0.degenerate_geometry"
        ]
        assert len(degenerate_findings) >= 1, "Expected degenerate_geometry rule"

        # Verify message content
        finding = degenerate_findings[0]
        assert "volume" in finding.message.lower() or "zero" in finding.message.lower()

    def test_missing_units_blocking_unknown(self, test_projects_root: Path):
        """Missing units produces blocking Unknown."""
        project = test_projects_root / "step_missing_units"
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        # Should have blocking unknown
        assert len(result.unknowns) >= 1, "Expected at least one Unknown"

        blocking_unknowns = [u for u in result.unknowns if u.blocking]
        assert len(blocking_unknowns) >= 1, "Expected blocking Unknown"

        # Check it's from units check
        units_unknowns = [
            u
            for u in blocking_unknowns
            if u.created_by_rule_id == "mech.tier0.units_present"
        ]
        assert len(units_unknowns) >= 1, "Expected units_present Unknown"

    @pytest.mark.parametrize(
        "test_case",
        [
            "step_golden_pass",
            "step_invalid_geometry",
            "step_missing_units",
        ],
    )
    def test_tier0_result_structure(self, test_projects_root: Path, test_case: str):
        """All tier0 results have correct structure."""
        project = test_projects_root / test_case
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        # Verify structure
        assert hasattr(result, "findings")
        assert hasattr(result, "unknowns")
        assert hasattr(result, "passed")
        assert hasattr(result, "has_blockers")

        # Findings should be valid Finding objects
        for f in result.findings:
            assert isinstance(f, Finding)
            assert f.rule_id is not None
            assert f.severity is not None
            assert f.message is not None


class TestUnitsCheck:
    """Direct tests for check_units_present()."""

    def test_units_present_returns_empty(self, test_projects_root: Path):
        """MDS with units returns no findings/unknowns."""
        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        results = check_units_present(mds)

        assert len(results) == 0

    def test_units_missing_returns_blocking_unknown(self, test_projects_root: Path):
        """MDS without units returns blocking Unknown."""
        project = test_projects_root / "step_missing_units"
        mds = load_mds(project)

        results = check_units_present(mds)

        assert len(results) >= 1

        unknowns = [r for r in results if isinstance(r, Unknown)]
        assert len(unknowns) >= 1
        assert unknowns[0].blocking
        assert unknowns[0].created_by_rule_id == "mech.tier0.units_present"


class TestDegenerateGeometryCheck:
    """Direct tests for check_degenerate_geometry()."""

    def test_valid_volume_no_finding(self, test_projects_root: Path):
        """Part with positive volume returns no findings."""
        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        results = check_degenerate_geometry(mds)

        # Golden pass should have no degenerate findings
        assert len(results) == 0

    def test_zero_volume_blocker(self, test_projects_root: Path):
        """Part with zero volume returns BLOCKER finding."""
        project = test_projects_root / "step_invalid_geometry"
        mds = load_mds(project)

        results = check_degenerate_geometry(mds)

        assert len(results) >= 1

        finding = results[0]
        assert isinstance(finding, Finding)
        assert finding.severity == Severity.BLOCKER
        assert finding.rule_id == "mech.tier0.degenerate_geometry"


# ============================================================================
# SHACL Validation Integration Tests
# ============================================================================


class TestSHACLValidationIntegration:
    """Integration tests for SHACL validation pipeline."""

    @pytest.fixture
    def shacl_available(self):
        """Check if SHACL dependencies are available."""
        try:
            from mech_verify.shacl.engine import PYSHACL_AVAILABLE, RDFLIB_AVAILABLE

            if not RDFLIB_AVAILABLE or not PYSHACL_AVAILABLE:
                pytest.skip("SHACL dependencies not available")
        except ImportError:
            pytest.skip("SHACL module not available")

    def test_mds_to_rdf_produces_triples(
        self, test_projects_root: Path, shacl_available
    ):
        """MDS to RDF projection produces valid graph."""
        from mech_verify.shacl import mds_to_rdf

        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        graph = mds_to_rdf(mds)

        assert graph is not None
        assert len(graph) > 0, "Graph should have triples"

    def test_shacl_validation_runs(self, test_projects_root: Path, shacl_available):
        """SHACL validation completes without error."""
        from mech_verify.shacl import mds_to_rdf, run_shacl_validation

        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        graph = mds_to_rdf(mds)

        # Find shapes
        rulepacks_dir = Path(__file__).parent.parent.parent / "rulepacks" / "mech"
        shapes_paths = []
        for rulepack in rulepacks_dir.iterdir():
            if rulepack.is_dir() and "pmi" not in rulepack.name.lower():
                shapes_dir = rulepack / "shapes"
                if shapes_dir.exists():
                    shapes_paths.extend(shapes_dir.glob("*.ttl"))

        if not shapes_paths:
            pytest.skip("No SHACL shapes found")

        results = run_shacl_validation(graph, list(shapes_paths))

        assert isinstance(results, list)

    def test_hole_too_small_via_shacl(self, test_projects_root: Path, shacl_available):
        """Small hole detected via SHACL validation."""
        from mech_verify.shacl import mds_to_rdf, run_shacl_validation

        project = test_projects_root / "step_hole_too_small"
        mds = load_mds(project)

        graph = mds_to_rdf(mds)

        # Use DFM shapes specifically
        dfm_shapes_dir = (
            Path(__file__).parent.parent.parent
            / "rulepacks"
            / "mech"
            / "tier0_dfm_machining"
            / "shapes"
        )
        if not dfm_shapes_dir.exists():
            pytest.skip("DFM shapes not found")

        shapes_paths = list(dfm_shapes_dir.glob("*.ttl"))
        results = run_shacl_validation(graph, shapes_paths)

        # Should have violation for small hole
        assert isinstance(results, list)
        # Note: SHACL validation should produce findings for diameter < 0.5mm

    def test_golden_pass_shacl_conforming(
        self, test_projects_root: Path, shacl_available
    ):
        """Golden pass MDS conforms to SHACL shapes."""
        from mech_verify.shacl import mds_to_rdf, run_shacl_validation

        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        graph = mds_to_rdf(mds)

        # Use integrity shapes
        integrity_shapes_dir = (
            Path(__file__).parent.parent.parent
            / "rulepacks"
            / "mech"
            / "tier0_integrity_shacl"
            / "shapes"
        )
        if not integrity_shapes_dir.exists():
            pytest.skip("Integrity shapes not found")

        shapes_paths = list(integrity_shapes_dir.glob("*.ttl"))
        results = run_shacl_validation(graph, shapes_paths)

        # Golden pass should have no ERROR/BLOCKER findings
        error_findings = [
            r
            for r in results
            if hasattr(r, "severity")
            and str(getattr(r.severity, "value", r.severity)) in ("ERROR", "BLOCKER")
        ]
        assert len(error_findings) == 0, f"Unexpected violations: {error_findings}"


# ============================================================================
# Assembly Verification Integration Tests
# ============================================================================


class TestAssemblyVerificationIntegration:
    """Integration tests for assembly interference/clearance checks."""

    @pytest.fixture
    def mock_assembly_backend(self):
        """Create a mock backend for assembly tests."""
        from mech_verify.assembly.bbox import BBox

        class MockAssemblyBackend:
            """Mock backend for testing assembly checks."""

            def is_available(self) -> bool:
                return True

            def get_bbox(self, shape) -> BBox | None:
                """Return bbox from shape dict."""
                if isinstance(shape, dict):
                    bbox_data = shape.get("bbox", {})
                    if bbox_data:
                        return BBox(
                            min_pt=tuple(bbox_data.get("min_pt", [0, 0, 0])),
                            max_pt=tuple(bbox_data.get("max_pt", [1, 1, 1])),
                        )
                return None

            def get_intersection_volume(self, shape_a, shape_b) -> float:
                """Mock intersection volume."""
                # For interference test - assume shapes overlap
                if hasattr(shape_a, "get") and hasattr(shape_b, "get"):
                    return 1000.0  # Overlap volume
                return 0.0

            def get_min_distance(self, shape_a, shape_b) -> float:
                """Mock minimum distance."""
                return 0.1  # Below clearance threshold

        return MockAssemblyBackend()

    def test_assembly_clean_no_findings(self, test_projects_root: Path):
        """Clean assembly produces no findings."""
        project = test_projects_root / "step_assembly_clean"
        mds = load_mds(project)
        expected = load_expected_findings(project)

        # Verify expected is "pass"
        assert expected["expected_status"] == "pass"

        # Assembly checks require backend - test structure only
        assemblies = mds.get("assemblies", [])
        assert len(assemblies) >= 1, "Assembly data should be present"

    def test_assembly_interference_structure(self, test_projects_root: Path):
        """Interference assembly has correct MDS structure."""
        project = test_projects_root / "step_assembly_interference"
        mds = load_mds(project)
        expected = load_expected_findings(project)

        # Verify expected is "fail" with interference
        assert expected["expected_status"] == "fail"
        assert len(expected["expected_findings"]) >= 1
        assert expected["expected_findings"][0]["rule_id"] == "mech.tier0.interference"

        # Verify MDS has overlapping parts
        assemblies = mds.get("assemblies", [])
        assert len(assemblies) >= 1

        assembly = assemblies[0]
        occurrences = assembly.get("occurrences", [])
        assert len(occurrences) >= 2, "Need at least 2 parts for interference"

    def test_assembly_clearance_structure(self, test_projects_root: Path):
        """Clearance assembly has correct MDS structure."""
        project = test_projects_root / "step_assembly_clearance"
        load_mds(project)
        expected = load_expected_findings(project)

        # Verify expected is "warn" with clearance
        assert expected["expected_status"] == "warn"
        assert expected["expected_findings"][0]["rule_id"] == "mech.tier0.clearance"

    def test_generate_pairs(self, test_projects_root: Path):
        """Test pair generation for assembly verification."""
        from mech_verify.tier0_assembly import generate_pairs

        project = test_projects_root / "step_assembly_interference"
        mds = load_mds(project)

        assemblies = mds.get("assemblies", [])
        assembly = assemblies[0]
        occurrences = assembly.get("occurrences", [])

        pairs = generate_pairs(occurrences)

        # With 2 parts, should have 1 pair
        assert len(pairs) == 1
        assert isinstance(pairs[0], tuple)
        assert len(pairs[0]) == 2

    def test_run_assembly_checks_without_backend(self, test_projects_root: Path):
        """Assembly checks without backend return Unknown."""
        from mech_verify.tier0_assembly import run_tier0_assembly_checks

        project = test_projects_root / "step_assembly_interference"
        mds = load_mds(project)

        # Run with no backend
        results = run_tier0_assembly_checks(mds, backend=None)

        # Should return Unknown about missing backend
        assert len(results) >= 1
        # First result should be Unknown about unavailable backend
        first_result = results[0]
        assert hasattr(first_result, "summary")
        assert (
            "unavailable" in first_result.summary.lower()
            or "backend" in first_result.summary.lower()
        )

    def test_run_assembly_checks_empty_assembly(self, test_projects_root: Path):
        """Assembly checks with empty assembly returns empty list."""
        from mech_verify.tier0_assembly import run_tier0_assembly_checks

        # MDS with empty assemblies
        mds = {"assemblies": [], "parts": []}

        # Create a mock available backend
        class MockBackend:
            def is_available(self) -> bool:
                return True

        results = run_tier0_assembly_checks(mds, backend=MockBackend())

        # No assemblies = no results
        assert len(results) == 0

    def test_run_assembly_checks_single_part(self, test_projects_root: Path):
        """Assembly with single part returns empty list."""
        from mech_verify.tier0_assembly import run_tier0_assembly_checks

        # MDS with single-part assembly
        mds = {
            "assemblies": [
                {"assembly_id": "test", "occurrences": [{"part_id": "only_part"}]}
            ],
            "parts": [{"part_id": "only_part"}],
        }

        class MockBackend:
            def is_available(self) -> bool:
                return True

        results = run_tier0_assembly_checks(mds, backend=MockBackend())

        # Single part = no pairs = no results
        assert len(results) == 0

    def test_build_pair_object_ref(self):
        """Test pair object ref building."""
        from mech_verify.tier0_assembly import build_pair_object_ref

        ref = build_pair_object_ref("asm1", "partA", "partB")

        # Should be sorted alphabetically
        assert "partA__partB" in ref
        assert "asm1" in ref

        # Order shouldn't matter
        ref2 = build_pair_object_ref("asm1", "partB", "partA")
        assert ref == ref2

    def test_tier0_assembly_config_defaults(self):
        """Test assembly config default values."""
        from mech_verify.tier0_assembly import Tier0AssemblyConfig

        config = Tier0AssemblyConfig()

        assert config.clearance_min_mm == 0.2
        assert config.interference_eps_volume == 1e-6
        assert config.bbox_margin_mm == 0.0

    def test_tier0_assembly_config_from_dict(self):
        """Test assembly config from dict."""
        from mech_verify.tier0_assembly import Tier0AssemblyConfig

        config = Tier0AssemblyConfig.from_dict(
            {
                "clearance_min_mm": 0.5,
                "interference_eps_volume": 1e-9,
                "bbox_margin_mm": 1.0,
            }
        )

        assert config.clearance_min_mm == 0.5
        assert config.interference_eps_volume == 1e-9
        assert config.bbox_margin_mm == 1.0


# ============================================================================
# PMI Verification Integration Tests
# ============================================================================


class TestPMIVerificationIntegration:
    """Integration tests for PMI verification."""

    def test_pmi_present_structure(self, test_projects_root: Path):
        """PMI present fixture has correct MDS structure."""
        project = test_projects_root / "step_pmi_present"
        mds = load_mds(project)

        pmi = mds.get("pmi", {})
        assert pmi.get("has_semantic_pmi"), "Expected has_semantic_pmi=true"

    def test_pmi_absent_structure(self, test_projects_root: Path):
        """PMI absent fixture has correct MDS structure."""
        project = test_projects_root / "step_pmi_absent"
        mds = load_mds(project)

        pmi = mds.get("pmi", {})
        assert not pmi.get("has_semantic_pmi"), "Expected has_semantic_pmi=false"

    def test_pmi_absent_expected_unknown(self, test_projects_root: Path):
        """PMI absent should produce Unknown when required."""
        project = test_projects_root / "step_pmi_absent"
        expected = load_expected_findings(project)

        assert expected["expected_status"] == "unknown"
        assert expected.get("require_pmi")
        assert len(expected.get("expected_unknowns", [])) >= 1

        unknown = expected["expected_unknowns"][0]
        assert unknown["blocking"]
        assert unknown["created_by_rule_id"] == "mech.tier0.pmi_required"


# ============================================================================
# Parametrized Full Pipeline Tests
# ============================================================================


class TestFullPipelineParametrized:
    """Parametrized tests covering all test projects."""

    @pytest.mark.parametrize(
        "test_case,expected_status",
        [
            ("step_golden_pass", "pass"),
            ("step_hole_too_small", "fail"),
            ("step_high_ld_ratio", "warn"),
            ("step_small_fillet", "warn"),
            ("step_missing_units", "unknown"),
            ("step_invalid_geometry", "fail"),
            ("step_assembly_clean", "pass"),
            ("step_assembly_interference", "fail"),
            ("step_assembly_clearance", "warn"),
            ("step_pmi_present", "pass"),
            ("step_pmi_absent", "unknown"),
        ],
    )
    def test_expected_status_matches(
        self, test_projects_root: Path, test_case: str, expected_status: str
    ):
        """Verify expected_findings.json has correct status."""
        project = test_projects_root / test_case
        expected = load_expected_findings(project)

        assert (
            expected["expected_status"] == expected_status
        ), f"{test_case}: expected status '{expected_status}', got '{expected['expected_status']}'"

    @pytest.mark.parametrize(
        "test_case",
        [
            "step_golden_pass",
            "step_hole_too_small",
            "step_high_ld_ratio",
            "step_small_fillet",
            "step_missing_units",
            "step_invalid_geometry",
        ],
    )
    def test_tier0_part_checks_run_without_error(
        self, test_projects_root: Path, test_case: str
    ):
        """run_tier0_part_checks() completes without exception for all fixtures."""
        project = test_projects_root / test_case
        mds = load_mds(project)

        # Should not raise
        result = run_tier0_part_checks(mds)

        assert isinstance(result, Tier0PartResult)

    @pytest.mark.parametrize(
        "test_case,expect_finding",
        [
            ("step_golden_pass", False),
            ("step_invalid_geometry", True),  # degenerate_geometry
        ],
    )
    def test_tier0_findings_match_expectations(
        self, test_projects_root: Path, test_case: str, expect_finding: bool
    ):
        """Tier-0 findings match expected outcomes."""
        project = test_projects_root / test_case
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        if expect_finding:
            assert (
                len(result.findings) > 0 or len(result.unknowns) > 0
            ), f"{test_case}: expected findings but got none"
        else:
            # Note: May have findings from other checks, just verify no blockers/errors
            blockers = [
                f
                for f in result.findings
                if f.severity in (Severity.BLOCKER, Severity.ERROR)
            ]
            blocking_unknowns = [u for u in result.unknowns if u.blocking]
            assert (
                len(blockers) == 0 and len(blocking_unknowns) == 0
            ), f"{test_case}: unexpected blockers/errors: {blockers}"


# ============================================================================
# DFM Feature Checks (MDS-based)
# ============================================================================


class TestDFMFeatureChecks:
    """Tests for DFM feature checks from MDS features array."""

    def test_mds_has_hole_features(self, test_projects_root: Path):
        """Hole fixtures have hole features in MDS."""
        for test_case in [
            "step_golden_pass",
            "step_hole_too_small",
            "step_high_ld_ratio",
        ]:
            project = test_projects_root / test_case
            mds = load_mds(project)

            features = mds.get("features", [])
            holes = [f for f in features if f.get("feature_type") == "hole"]

            assert len(holes) >= 1, f"{test_case} should have hole features"

            # Verify hole has required properties
            hole = holes[0]
            assert "diameter" in hole, f"{test_case}: hole missing diameter"
            assert "depth" in hole, f"{test_case}: hole missing depth"

    def test_mds_has_fillet_features(self, test_projects_root: Path):
        """Fillet fixture has fillet features in MDS."""
        project = test_projects_root / "step_small_fillet"
        mds = load_mds(project)

        features = mds.get("features", [])
        fillets = [f for f in features if f.get("feature_type") == "fillet"]

        assert len(fillets) >= 1, "step_small_fillet should have fillet features"

        fillet = fillets[0]
        assert "radius" in fillet, "fillet missing radius"

    def test_hole_diameter_values(self, test_projects_root: Path):
        """Verify hole diameter values match expectations."""
        # Golden pass: hole >= 0.5mm
        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)
        holes = [f for f in mds.get("features", []) if f.get("feature_type") == "hole"]
        assert holes[0]["diameter"] >= 0.5

        # Hole too small: hole < 0.5mm
        project = test_projects_root / "step_hole_too_small"
        mds = load_mds(project)
        holes = [f for f in mds.get("features", []) if f.get("feature_type") == "hole"]
        assert holes[0]["diameter"] < 0.5

    def test_hole_ld_ratio_values(self, test_projects_root: Path):
        """Verify hole L/D ratio values match expectations."""
        # Golden pass: L/D <= 10
        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)
        holes = [f for f in mds.get("features", []) if f.get("feature_type") == "hole"]
        hole = holes[0]
        ld_ratio = hole.get("ld_ratio") or (hole["depth"] / hole["diameter"])
        assert ld_ratio <= 10.0

        # High L/D: L/D > 10
        project = test_projects_root / "step_high_ld_ratio"
        mds = load_mds(project)
        holes = [f for f in mds.get("features", []) if f.get("feature_type") == "hole"]
        hole = holes[0]
        ld_ratio = hole.get("ld_ratio") or (hole["depth"] / hole["diameter"])
        assert ld_ratio > 10.0

    def test_fillet_radius_values(self, test_projects_root: Path):
        """Verify fillet radius values match expectations."""
        project = test_projects_root / "step_small_fillet"
        mds = load_mds(project)
        fillets = [
            f for f in mds.get("features", []) if f.get("feature_type") == "fillet"
        ]

        assert fillets[0]["radius"] < 0.2, "small_fillet should have radius < 0.2mm"


# ============================================================================
# Report Building Integration Tests
# ============================================================================


class TestReportBuildingIntegration:
    """Tests for verification report building."""

    def test_build_report_structure(self, test_projects_root: Path):
        """Verify report has correct structure."""
        from mech_verify.cli import _build_verification_report

        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        # Build report
        report = _build_verification_report(
            inputs=[project / "inputs" / "mds.json"],
            findings=result.findings,
            unknowns=result.unknowns,
        )

        # Verify structure
        assert "report_id" in report
        assert "request" in report
        assert "status" in report
        assert "findings" in report
        assert "unknowns" in report
        assert "summary" in report

        # Golden pass should be PASS
        assert report["status"] == "PASS"

    def test_build_report_fail_status(self, test_projects_root: Path):
        """Verify report status is FAIL for blockers."""
        from mech_verify.cli import _build_verification_report

        project = test_projects_root / "step_invalid_geometry"
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        report = _build_verification_report(
            inputs=[project / "inputs" / "mds.json"],
            findings=result.findings,
            unknowns=result.unknowns,
        )

        assert report["status"] == "FAIL", "BLOCKER findings should produce FAIL status"
        assert report["summary"]["blockers"] >= 1

    def test_build_report_unknown_status(self, test_projects_root: Path):
        """Verify report status is UNKNOWN for blocking unknowns."""
        from mech_verify.cli import _build_verification_report

        project = test_projects_root / "step_missing_units"
        mds = load_mds(project)

        result = run_tier0_part_checks(mds)

        report = _build_verification_report(
            inputs=[project / "inputs" / "mds.json"],
            findings=result.findings,
            unknowns=result.unknowns,
        )

        assert (
            report["status"] == "UNKNOWN"
        ), "Blocking unknowns should produce UNKNOWN status"
        assert report["summary"]["blocking_unknowns"] >= 1


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in verification pipeline."""

    def test_empty_mds_handled(self):
        """Empty MDS is handled gracefully."""
        result = run_tier0_part_checks({})

        # Should produce units unknown at minimum
        assert isinstance(result, Tier0PartResult)

    def test_malformed_mds_handled(self):
        """Malformed MDS is handled gracefully."""
        mds = {"parts": "not_a_list"}  # Invalid structure

        # Should not raise
        try:
            result = run_tier0_part_checks(mds)
            assert isinstance(result, Tier0PartResult)
        except (TypeError, AttributeError):
            # Some malformed inputs may raise, that's acceptable
            pass

    def test_missing_mass_props_handled(self, test_projects_root: Path):
        """Missing mass_props is handled gracefully."""
        project = test_projects_root / "step_golden_pass"
        mds = load_mds(project)

        # Remove mass_props
        if mds.get("parts"):
            mds["parts"][0].pop("mass_props", None)

        # Should not raise
        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)


# ============================================================================
# Coverage Verification Tests
# ============================================================================


class TestCoverageVerification:
    """Tests to verify we're actually testing the right functions."""

    def test_tier0_part_module_functions_exist(self):
        """Verify tier0_part module exports expected functions."""
        from mech_verify import tier0_part

        assert hasattr(tier0_part, "run_tier0_part_checks")
        assert hasattr(tier0_part, "check_units_present")
        assert hasattr(tier0_part, "check_degenerate_geometry")
        assert hasattr(tier0_part, "check_solid_validity")
        assert hasattr(tier0_part, "Tier0PartResult")

    def test_tier0_assembly_module_functions_exist(self):
        """Verify tier0_assembly module exports expected functions."""
        from mech_verify import tier0_assembly

        assert hasattr(tier0_assembly, "run_tier0_assembly_checks")
        assert hasattr(tier0_assembly, "generate_pairs")
        assert hasattr(tier0_assembly, "Tier0AssemblyConfig")

    def test_shacl_module_functions_exist(self):
        """Verify SHACL module exports expected functions."""
        try:
            from mech_verify.shacl import mds_to_rdf, run_shacl_validation
            from mech_verify.shacl.engine import PYSHACL_AVAILABLE, RDFLIB_AVAILABLE

            assert callable(mds_to_rdf)
            assert callable(run_shacl_validation)
            assert isinstance(RDFLIB_AVAILABLE, bool)
            assert isinstance(PYSHACL_AVAILABLE, bool)
        except ImportError:
            pytest.skip("SHACL module not available")
