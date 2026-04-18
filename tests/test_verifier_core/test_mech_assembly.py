"""Tests for mech assembly ingestion and tier0 assembly checks."""

from __future__ import annotations

import hashlib
from unittest.mock import Mock

from src.mech_verifier.mech_verify.assembly.bbox import (
    BBox,
    bboxes_could_interact,
)
from src.mech_verifier.mech_verify.assembly.clearance import (
    RULE_ID_CLEARANCE,
    check_clearance,
)
from src.mech_verifier.mech_verify.assembly.ingestion import (
    AssemblyIngestion,
    Occurrence,
    generate_assembly_id,
)
from src.mech_verifier.mech_verify.assembly.interference import (
    RULE_ID_INTERFERENCE,
    check_interference,
)
from src.mech_verifier.mech_verify.tier0_assembly import (
    Tier0AssemblyConfig,
    build_pair_object_ref,
    generate_pairs,
    run_tier0_assembly_checks,
)
from src.verifier_core.verifier_core.models import Severity


class TestAssemblyIdGeneration:
    """Tests for deterministic assembly ID generation."""

    def test_generate_assembly_id_from_path(self):
        path = "/path/to/assembly.step"
        aid = generate_assembly_id(path)
        expected = hashlib.sha256(path.encode()).hexdigest()[:12]
        assert aid == expected

    def test_generate_assembly_id_deterministic(self):
        path = "/path/to/assembly.step"
        aid1 = generate_assembly_id(path)
        aid2 = generate_assembly_id(path)
        assert aid1 == aid2

    def test_generate_assembly_id_different_paths(self):
        aid1 = generate_assembly_id("/path/a.step")
        aid2 = generate_assembly_id("/path/b.step")
        assert aid1 != aid2


class TestOccurrence:
    """Tests for Occurrence dataclass."""

    def test_occurrence_creation(self):
        transform = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 10, 20, 30, 1]
        occ = Occurrence(
            part_id="part001",
            name="Bracket",
            transform=transform,
        )
        assert occ.part_id == "part001"
        assert occ.name == "Bracket"
        assert len(occ.transform) == 16
        assert occ.transform[12:15] == [10, 20, 30]

    def test_occurrence_to_dict(self):
        occ = Occurrence(
            part_id="part001",
            name="Bracket",
            transform=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        )
        d = occ.to_dict()
        assert d["part_id"] == "part001"
        assert d["name"] == "Bracket"
        assert len(d["transform"]) == 16


class TestBBox:
    """Tests for BBox helper."""

    def test_bbox_creation(self):
        bbox = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))
        assert bbox.min_pt == (0, 0, 0)
        assert bbox.max_pt == (10, 10, 10)

    def test_bboxes_overlap(self):
        bbox_a = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))
        bbox_b = BBox(min_pt=(5, 5, 5), max_pt=(15, 15, 15))
        assert bboxes_could_interact(bbox_a, bbox_b) is True

    def test_bboxes_separated(self):
        bbox_a = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))
        bbox_b = BBox(min_pt=(20, 20, 20), max_pt=(30, 30, 30))
        assert bboxes_could_interact(bbox_a, bbox_b) is False

    def test_bboxes_touching(self):
        bbox_a = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))
        bbox_b = BBox(min_pt=(10, 0, 0), max_pt=(20, 10, 10))
        assert bboxes_could_interact(bbox_a, bbox_b) is True

    def test_bboxes_within_margin(self):
        bbox_a = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))
        bbox_b = BBox(min_pt=(10.1, 0, 0), max_pt=(20, 10, 10))
        assert bboxes_could_interact(bbox_a, bbox_b, margin=0.0) is False
        assert bboxes_could_interact(bbox_a, bbox_b, margin=0.2) is True

    def test_bboxes_separated_one_axis(self):
        bbox_a = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))
        bbox_b = BBox(min_pt=(0, 0, 100), max_pt=(10, 10, 110))
        assert bboxes_could_interact(bbox_a, bbox_b) is False


class TestAssemblyIngestion:
    """Tests for STEP assembly ingestion."""

    def test_ingestion_returns_assembly_dict(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.load_assembly.return_value = {
            "name": "Test Assembly",
            "occurrences": [
                {"part_id": "part001", "name": "Bracket", "transform": [1] * 16},
                {"part_id": "part002", "name": "Plate", "transform": [1] * 16},
            ],
        }

        ingestion = AssemblyIngestion(mock_backend)
        result = ingestion.ingest_step_assembly("/path/to/assembly.step")

        assert "assembly_id" in result
        assert "name" in result
        assert "object_ref" in result
        assert "source_artifact" in result
        assert "occurrences" in result
        assert len(result["occurrences"]) == 2

    def test_ingestion_generates_stable_assembly_id(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.load_assembly.return_value = {
            "name": "Test",
            "occurrences": [],
        }

        ingestion = AssemblyIngestion(mock_backend)
        result1 = ingestion.ingest_step_assembly("/path/to/assembly.step")
        result2 = ingestion.ingest_step_assembly("/path/to/assembly.step")

        assert result1["assembly_id"] == result2["assembly_id"]

    def test_ingestion_object_ref_format(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.load_assembly.return_value = {
            "name": "Test",
            "occurrences": [],
        }

        ingestion = AssemblyIngestion(mock_backend)
        result = ingestion.ingest_step_assembly("/path/to/assembly.step")

        assert result["object_ref"].startswith("mech://assembly/")
        assert result["assembly_id"] in result["object_ref"]

    def test_ingestion_backend_unavailable_returns_unknown(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = False

        ingestion = AssemblyIngestion(mock_backend)
        result = ingestion.ingest_step_assembly("/path/to/assembly.step")

        assert result is None or "error" in result or result.get("occurrences") == []


class TestPairGeneration:
    """Tests for deterministic pair generation."""

    def test_generate_pairs_two_parts(self):
        occurrences = [
            {"part_id": "part_b"},
            {"part_id": "part_a"},
        ]
        pairs = generate_pairs(occurrences)
        assert len(pairs) == 1
        assert pairs[0] == ("part_a", "part_b")

    def test_generate_pairs_three_parts(self):
        occurrences = [
            {"part_id": "z"},
            {"part_id": "a"},
            {"part_id": "m"},
        ]
        pairs = generate_pairs(occurrences)
        assert len(pairs) == 3
        assert ("a", "m") in pairs
        assert ("a", "z") in pairs
        assert ("m", "z") in pairs

    def test_generate_pairs_deterministic_ordering(self):
        occurrences1 = [{"part_id": "b"}, {"part_id": "a"}, {"part_id": "c"}]
        occurrences2 = [{"part_id": "c"}, {"part_id": "a"}, {"part_id": "b"}]

        pairs1 = generate_pairs(occurrences1)
        pairs2 = generate_pairs(occurrences2)

        assert pairs1 == pairs2

    def test_build_pair_object_ref(self):
        ref = build_pair_object_ref("asm123", "part_a", "part_b")
        assert ref == "mech://assembly/asm123/pair/part_a__part_b"

    def test_build_pair_object_ref_sorts_parts(self):
        ref1 = build_pair_object_ref("asm123", "part_b", "part_a")
        ref2 = build_pair_object_ref("asm123", "part_a", "part_b")
        assert ref1 == ref2


class TestInterferenceCheck:
    """Tests for interference detection."""

    def test_interference_detected(self):
        mock_backend = Mock()
        mock_backend.get_intersection_volume.return_value = 0.001

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_interference(
            part_a, part_b, "asm123", mock_backend, eps_volume=1e-6
        )

        assert finding is not None
        assert finding.severity == Severity.BLOCKER
        assert finding.rule_id == RULE_ID_INTERFERENCE
        assert "a" in finding.message and "b" in finding.message
        assert finding.measured_value["intersection_volume"] == 0.001

    def test_no_interference(self):
        mock_backend = Mock()
        mock_backend.get_intersection_volume.return_value = 0.0

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_interference(
            part_a, part_b, "asm123", mock_backend, eps_volume=1e-6
        )

        assert finding is None

    def test_interference_below_threshold(self):
        mock_backend = Mock()
        mock_backend.get_intersection_volume.return_value = 1e-9

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_interference(
            part_a, part_b, "asm123", mock_backend, eps_volume=1e-6
        )

        assert finding is None

    def test_interference_object_ref_format(self):
        mock_backend = Mock()
        mock_backend.get_intersection_volume.return_value = 0.01

        part_a = {"part_id": "alpha", "shape": Mock()}
        part_b = {"part_id": "beta", "shape": Mock()}

        finding = check_interference(
            part_a, part_b, "asm123", mock_backend, eps_volume=1e-6
        )

        assert finding.object_ref == "mech://assembly/asm123/pair/alpha__beta"


class TestClearanceCheck:
    """Tests for clearance detection."""

    def test_clearance_violation_warn(self):
        mock_backend = Mock()
        mock_backend.get_min_distance.return_value = 0.1

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_clearance(part_a, part_b, "asm123", mock_backend, min_dist=0.2)

        assert finding is not None
        assert finding.severity == Severity.WARN
        assert finding.rule_id == RULE_ID_CLEARANCE
        assert finding.measured_value["clearance_mm"] == 0.1
        assert finding.limit["min_clearance_mm"] == 0.2

    def test_clearance_ok(self):
        mock_backend = Mock()
        mock_backend.get_min_distance.return_value = 0.5

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_clearance(part_a, part_b, "asm123", mock_backend, min_dist=0.2)

        assert finding is None

    def test_clearance_exact_threshold(self):
        mock_backend = Mock()
        mock_backend.get_min_distance.return_value = 0.2

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_clearance(part_a, part_b, "asm123", mock_backend, min_dist=0.2)

        assert finding is None

    def test_clearance_zero_distance_warn(self):
        """Zero distance (exact contact) should be WARN, not ERROR."""
        mock_backend = Mock()
        mock_backend.get_min_distance.return_value = 0.0

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_clearance(part_a, part_b, "asm123", mock_backend, min_dist=0.2)

        assert finding is not None
        assert finding.severity == Severity.WARN
        assert "contact" in finding.message.lower()

    def test_clearance_negative_distance_error(self):
        """Negative distance (overlap) should be ERROR."""
        mock_backend = Mock()
        mock_backend.get_min_distance.return_value = -0.1

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_clearance(part_a, part_b, "asm123", mock_backend, min_dist=0.2)

        assert finding is not None
        assert finding.severity == Severity.ERROR
        assert "overlap" in finding.message.lower()

    def test_clearance_suggested_fix(self):
        mock_backend = Mock()
        mock_backend.get_min_distance.return_value = 0.05

        part_a = {"part_id": "a", "shape": Mock()}
        part_b = {"part_id": "b", "shape": Mock()}

        finding = check_clearance(part_a, part_b, "asm123", mock_backend, min_dist=0.2)

        assert finding.suggested_fix is not None
        assert (
            "0.2" in finding.suggested_fix
            or "clearance" in finding.suggested_fix.lower()
        )


class TestTier0AssemblyConfig:
    """Tests for Tier0 assembly configuration."""

    def test_default_config(self):
        config = Tier0AssemblyConfig()
        assert config.clearance_min_mm == 0.2
        assert config.interference_eps_volume == 1e-6

    def test_custom_config(self):
        config = Tier0AssemblyConfig(
            clearance_min_mm=0.5,
            interference_eps_volume=1e-9,
        )
        assert config.clearance_min_mm == 0.5
        assert config.interference_eps_volume == 1e-9

    def test_config_from_dict(self):
        d = {"clearance_min_mm": 0.3, "interference_eps_volume": 1e-8}
        config = Tier0AssemblyConfig.from_dict(d)
        assert config.clearance_min_mm == 0.3
        assert config.interference_eps_volume == 1e-8


class TestTier0AssemblyRunner:
    """Tests for the full tier0 assembly check runner."""

    def test_run_empty_assemblies(self):
        mds = {"assemblies": []}
        mock_backend = Mock()

        findings = run_tier0_assembly_checks(mds, mock_backend)

        assert findings == []

    def test_run_single_part_no_pairs(self):
        mds = {
            "assemblies": [
                {
                    "assembly_id": "asm1",
                    "occurrences": [{"part_id": "p1", "shape": Mock()}],
                }
            ]
        }
        mock_backend = Mock()

        findings = run_tier0_assembly_checks(mds, mock_backend)

        assert findings == []

    def test_run_finds_interference(self):
        mock_shape_a = Mock()
        mock_shape_b = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.get_intersection_volume.return_value = 0.01
        mock_backend.get_min_distance.return_value = 0.0
        mock_backend.get_bbox.side_effect = [
            BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10)),
            BBox(min_pt=(5, 5, 5), max_pt=(15, 15, 15)),
        ]

        mds = {
            "assemblies": [
                {
                    "assembly_id": "asm1",
                    "occurrences": [
                        {"part_id": "a", "shape": mock_shape_a},
                        {"part_id": "b", "shape": mock_shape_b},
                    ],
                }
            ]
        }

        findings = run_tier0_assembly_checks(mds, mock_backend)

        interference_findings = [
            f for f in findings if f.rule_id == RULE_ID_INTERFERENCE
        ]
        assert len(interference_findings) == 1
        assert interference_findings[0].severity == Severity.BLOCKER

    def test_run_clearance_only_if_no_interference(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.get_intersection_volume.return_value = 0.01
        mock_backend.get_min_distance.return_value = 0.05
        mock_backend.get_bbox.side_effect = [
            BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10)),
            BBox(min_pt=(5, 5, 5), max_pt=(15, 15, 15)),
        ]

        mds = {
            "assemblies": [
                {
                    "assembly_id": "asm1",
                    "occurrences": [
                        {"part_id": "a", "shape": Mock()},
                        {"part_id": "b", "shape": Mock()},
                    ],
                }
            ]
        }

        findings = run_tier0_assembly_checks(mds, mock_backend)

        clearance_findings = [f for f in findings if f.rule_id == RULE_ID_CLEARANCE]
        assert len(clearance_findings) == 0

    def test_run_deterministic_ordering(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.get_intersection_volume.return_value = 0.01
        mock_backend.get_min_distance.return_value = 0.1
        mock_backend.get_bbox.return_value = BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10))

        mds = {
            "assemblies": [
                {
                    "assembly_id": "asm1",
                    "occurrences": [
                        {"part_id": "z", "shape": Mock()},
                        {"part_id": "a", "shape": Mock()},
                        {"part_id": "m", "shape": Mock()},
                    ],
                }
            ]
        }

        findings1 = run_tier0_assembly_checks(mds, mock_backend)
        findings2 = run_tier0_assembly_checks(mds, mock_backend)

        refs1 = [f.object_ref for f in findings1]
        refs2 = [f.object_ref for f in findings2]
        assert refs1 == refs2

    def test_bbox_pruning_skips_distant_pairs(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.get_bbox.side_effect = [
            BBox(min_pt=(0, 0, 0), max_pt=(10, 10, 10)),
            BBox(min_pt=(100, 100, 100), max_pt=(110, 110, 110)),
        ]

        mds = {
            "assemblies": [
                {
                    "assembly_id": "asm1",
                    "occurrences": [
                        {"part_id": "a", "shape": Mock()},
                        {"part_id": "b", "shape": Mock()},
                    ],
                }
            ]
        }

        findings = run_tier0_assembly_checks(mds, mock_backend)

        mock_backend.get_intersection_volume.assert_not_called()
        mock_backend.get_min_distance.assert_not_called()
        assert findings == []

    def test_backend_unavailable_emits_unknown(self):
        mock_backend = Mock()
        mock_backend.is_available.return_value = False

        mds = {
            "assemblies": [
                {
                    "assembly_id": "asm1",
                    "occurrences": [
                        {"part_id": "a", "shape": Mock()},
                        {"part_id": "b", "shape": Mock()},
                    ],
                }
            ]
        }

        result = run_tier0_assembly_checks(mds, mock_backend)

        unknowns = [r for r in result if hasattr(r, "summary")]
        assert len(unknowns) > 0 or result == []
