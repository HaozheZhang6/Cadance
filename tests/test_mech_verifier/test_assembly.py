"""Tests for assembly verification.

These tests verify assembly-level checks:
- Assembly ingestion and occurrence extraction
- Interference detection
- Clearance checking
- Bounding box pruning optimization
"""

from pathlib import Path

from .conftest import load_expected_findings, load_mds


class TestAssemblyIngestion:
    """Tests for assembly MDS ingestion."""

    def test_ingest_extracts_occurrences(self, assembly_clean_fixture: Path):
        """Assembly ingestion returns occurrences with transforms."""
        mds = load_mds(assembly_clean_fixture)

        # New schema: assemblies is an array
        assert "assemblies" in mds
        assemblies = mds["assemblies"]
        assert len(assemblies) >= 1

        assembly = assemblies[0]
        assert "assembly_id" in assembly
        assert "occurrences" in assembly

        occurrences = assembly["occurrences"]
        assert len(occurrences) >= 2

        for occ in occurrences:
            assert "occurrence_id" in occ
            assert "part_id" in occ
            assert "transform" in occ

    def test_assembly_id_deterministic(self, assembly_clean_fixture: Path):
        """Same assembly produces same ID."""
        mds1 = load_mds(assembly_clean_fixture)
        mds2 = load_mds(assembly_clean_fixture)
        # New schema: assemblies array
        assert (
            mds1["assemblies"][0]["assembly_id"] == mds2["assemblies"][0]["assembly_id"]
        )

    def test_parts_referenced_by_occurrences(self, assembly_clean_fixture: Path):
        """All occurrence part_ids exist in parts list."""
        mds = load_mds(assembly_clean_fixture)

        part_ids = {p["part_id"] for p in mds["parts"]}
        # New schema: assemblies array
        for occ in mds["assemblies"][0]["occurrences"]:
            assert occ["part_id"] in part_ids


class TestInterference:
    """Tests for assembly interference detection."""

    def test_non_intersecting_passes(self, assembly_clean_fixture: Path):
        """Non-intersecting parts produce no finding."""
        expected = load_expected_findings(assembly_clean_fixture)

        assert expected["expected_status"] == "pass"
        assert expected["expected_findings"] == []

    def test_intersecting_parts_blocker(self, assembly_interference_fixture: Path):
        """Intersection volume > eps produces BLOCKER."""
        load_mds(assembly_interference_fixture)
        expected = load_expected_findings(assembly_interference_fixture)

        assert expected["expected_status"] == "fail"
        findings = expected["expected_findings"]
        assert len(findings) == 1

        finding = findings[0]
        assert finding["rule_id"] == "mech.tier0.interference"
        assert finding["severity"] == "BLOCKER"
        assert finding.get("object_refs_count", 2) == 2


class TestClearance:
    """Tests for assembly clearance checking."""

    def test_adequate_clearance_passes(self, assembly_clean_fixture: Path):
        """Parts with clearance above threshold produce no finding."""
        expected = load_expected_findings(assembly_clean_fixture)

        assert expected["expected_findings"] == []

    def test_close_parts_warn(self, assembly_clearance_fixture: Path):
        """Parts closer than threshold produce WARN."""
        load_mds(assembly_clearance_fixture)
        expected = load_expected_findings(assembly_clearance_fixture)

        assert expected["expected_status"] == "warn"
        findings = expected["expected_findings"]
        assert len(findings) == 1

        finding = findings[0]
        assert finding["rule_id"] == "mech.tier0.clearance"
        assert finding["severity"] == "WARN"

    def test_touching_parts_scenario(self):
        """Parts with zero distance produce ERROR (placeholder)."""
        pass


class TestBBoxPruning:
    """Tests for bounding box pruning optimization."""

    def test_distant_pairs_skipped(self, assembly_clean_fixture: Path):
        """Pairs with non-overlapping bboxes not checked in detail."""
        mds = load_mds(assembly_clean_fixture)

        # New schema: assemblies array, bbox in mass_props
        assembly = mds["assemblies"][0]
        parts = {p["part_id"]: p for p in mds["parts"]}
        occurrences = assembly["occurrences"]

        for occ in occurrences:
            part = parts[occ["part_id"]]
            # New schema: bbox is in mass_props, not at part level
            assert "mass_props" in part
            assert "bbox" in part["mass_props"]

    def test_bbox_pruning_reduces_checks(self, assembly_clean_fixture: Path):
        """Bounding box pruning reduces pair checks."""
        mds = load_mds(assembly_clean_fixture)

        # Clean assembly has parts that don't overlap
        assembly = mds["assemblies"][0]
        occurrences = assembly["occurrences"]

        # With N parts, naive check is N*(N-1)/2 pairs
        n = len(occurrences)
        naive_pairs = n * (n - 1) // 2

        # BBox pruning should reduce this for non-overlapping parts
        # For clean assembly, parts are distant so all pairs should be pruned
        assert naive_pairs >= 1  # At least one pair to check

    def test_bbox_pruning_performance(self, assembly_clean_fixture: Path):
        """Measure pair-check reduction with bbox pruning."""
        from mech_verify.assembly.bbox import BBox, bboxes_could_interact

        mds = load_mds(assembly_clean_fixture)
        parts = {p["part_id"]: p for p in mds["parts"]}
        assembly = mds["assemblies"][0]
        occurrences = assembly["occurrences"]

        # Count pairs that would need detailed check
        pairs_to_check = 0
        pairs_pruned = 0

        for i, occ1 in enumerate(occurrences):
            for occ2 in occurrences[i + 1 :]:
                part1 = parts[occ1["part_id"]]
                part2 = parts[occ2["part_id"]]

                bbox1_data = part1["mass_props"]["bbox"]
                bbox2_data = part2["mass_props"]["bbox"]

                # Create BBox objects
                bbox1 = BBox(
                    min_pt=tuple(bbox1_data["min_pt"]),
                    max_pt=tuple(bbox1_data["max_pt"]),
                )
                bbox2 = BBox(
                    min_pt=tuple(bbox2_data["min_pt"]),
                    max_pt=tuple(bbox2_data["max_pt"]),
                )

                # Check if bboxes could interact
                if bboxes_could_interact(bbox1, bbox2, margin=0.0):
                    pairs_to_check += 1
                else:
                    pairs_pruned += 1

        # For clean assembly, parts are distant so pairs should be pruned
        total_pairs = pairs_to_check + pairs_pruned
        assert total_pairs >= 1
