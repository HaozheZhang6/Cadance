"""Tests for GeometricComparator."""

from unittest.mock import Mock

import pytest

# Skip entire module if cadquery unavailable (nlopt missing on aarch64)
pytest.importorskip("cadquery")

from src.cad.comparator import ComparisonResult, GeometricComparator
from src.tools.gateway import IoUResult


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    def test_result_creation(self):
        """ComparisonResult should be creatable."""
        result = ComparisonResult(
            overall_pass=True,
            volume_match=True,
            volume_ratio=1.0,
            bounding_box_match=True,
            topology_match=True,
            face_count_match=True,
            edge_count_match=True,
        )
        assert result.overall_pass is True

    def test_result_with_details(self):
        """ComparisonResult should accept details."""
        result = ComparisonResult(
            overall_pass=False,
            volume_match=False,
            volume_ratio=0.5,
            bounding_box_match=True,
            topology_match=True,
            face_count_match=True,
            edge_count_match=True,
            details={"reason": "Volume mismatch"},
        )
        assert result.details["reason"] == "Volume mismatch"


class TestGeometricComparator:
    """Tests for GeometricComparator."""

    @pytest.fixture
    def comparator(self):
        """Create comparator with default tolerance."""
        return GeometricComparator(tolerance=0.01)

    def test_comparator_creation(self, comparator):
        """Comparator should be creatable."""
        assert comparator is not None
        assert comparator.tolerance == 0.01

    def test_exact_match_passes(self, comparator):
        """Exact match should pass."""
        generated = {
            "volume": 150000,
            "bounding_box": {"x": 100, "y": 50, "z": 30},
            "face_count": 6,
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.overall_pass is True
        assert result.volume_match is True
        assert result.volume_ratio == 1.0
        assert result.bounding_box_match is True
        assert result.topology_match is True

    def test_volume_within_tolerance_passes(self, comparator):
        """Volume within tolerance should pass."""
        generated = {
            "volume": 150500,  # 0.33% difference
            "bounding_box": {"x": 100, "y": 50, "z": 30},
            "face_count": 6,
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.volume_match is True

    def test_volume_outside_tolerance_fails(self, comparator):
        """Volume outside tolerance should fail."""
        generated = {
            "volume": 160000,  # 6.67% difference
            "bounding_box": {"x": 100, "y": 50, "z": 30},
            "face_count": 6,
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.volume_match is False
        assert result.overall_pass is False

    def test_face_count_mismatch_fails(self, comparator):
        """Face count mismatch should fail topology check."""
        generated = {
            "volume": 150000,
            "bounding_box": {"x": 100, "y": 50, "z": 30},
            "face_count": 8,  # Wrong
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.face_count_match is False
        assert result.topology_match is False
        assert result.overall_pass is False

    def test_edge_count_mismatch_fails(self, comparator):
        """Edge count mismatch should fail topology check."""
        generated = {
            "volume": 150000,
            "bounding_box": {"x": 100, "y": 50, "z": 30},
            "face_count": 6,
            "edge_count": 14,  # Wrong
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.edge_count_match is False
        assert result.topology_match is False

    def test_bounding_box_mismatch_fails(self, comparator):
        """Bounding box mismatch should fail."""
        generated = {
            "volume": 150000,
            "bounding_box": {"x": 120, "y": 50, "z": 30},  # Wrong x
            "face_count": 6,
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.bounding_box_match is False
        assert result.overall_pass is False

    def test_missing_data_handles_gracefully(self, comparator):
        """Missing data should be handled gracefully."""
        generated = {"volume": 150000}
        ground_truth = {"expected_volume": 150000}

        result = comparator.compare(generated, ground_truth)

        # Should not crash, but should fail due to missing data
        assert isinstance(result, ComparisonResult)

    def test_custom_tolerance(self):
        """Custom tolerance should be respected."""
        comparator = GeometricComparator(tolerance=0.1)  # 10% tolerance

        generated = {
            "volume": 160000,  # 6.67% difference - within 10%
            "bounding_box": {"x": 100, "y": 50, "z": 30},
            "face_count": 6,
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 150000,
            "expected_bounding_box": {"x": 100, "y": 50, "z": 30},
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.volume_match is True  # Within 10% tolerance


class TestCompareWithIoU:
    """Tests for compare_with_iou method."""

    @pytest.fixture
    def mock_gateway(self):
        """Create mock gateway."""
        gateway = Mock()
        return gateway

    def test_compare_with_iou_requires_gateway(self):
        """compare_with_iou raises ValueError without gateway."""
        comparator = GeometricComparator(tolerance=0.01)

        with pytest.raises(ValueError, match="Gateway required"):
            comparator.compare_with_iou("gen_code", "gt_code")

    def test_compare_with_iou_success(self, mock_gateway):
        """compare_with_iou returns result on successful IoU computation."""
        mock_gateway.compute_iou.return_value = IoUResult(
            iou_score=0.95,
            intersection_volume=950.0,
            union_volume=1000.0,
            generated_volume=1000.0,
            ground_truth_volume=1000.0,
            generated_props={
                "volume": 1000.0,
                "face_count": 6,
                "edge_count": 12,
                "bounding_box": {"xlen": 10, "ylen": 10, "zlen": 10},
            },
            ground_truth_props={
                "volume": 1000.0,
                "face_count": 6,
                "edge_count": 12,
                "bounding_box": {"xlen": 10, "ylen": 10, "zlen": 10},
            },
        )

        comparator = GeometricComparator(tolerance=0.01, gateway=mock_gateway)
        result = comparator.compare_with_iou("gen_code", "gt_code")

        assert result.overall_pass is True
        assert result.iou_score == 0.95
        assert result.iou_pass is True
        mock_gateway.compute_iou.assert_called_once_with(
            "cadquery", "gen_code", "gt_code"
        )

    def test_compare_with_iou_failure_returns_fail_result(self, mock_gateway):
        """compare_with_iou returns fail result when IoU computation fails."""
        mock_gateway.compute_iou.return_value = None

        comparator = GeometricComparator(tolerance=0.01, gateway=mock_gateway)
        result = comparator.compare_with_iou("gen_code", "gt_code")

        assert result.overall_pass is False
        assert "error" in result.details

    def test_compare_with_iou_low_score_fails(self, mock_gateway):
        """compare_with_iou fails when IoU score is low."""
        mock_gateway.compute_iou.return_value = IoUResult(
            iou_score=0.5,  # Low IoU
            intersection_volume=500.0,
            union_volume=1000.0,
            generated_volume=800.0,
            ground_truth_volume=700.0,
            generated_props={
                "volume": 800.0,
                "face_count": 6,
                "edge_count": 12,
                "bounding_box": {"xlen": 10, "ylen": 10, "zlen": 10},
            },
            ground_truth_props={
                "volume": 700.0,
                "face_count": 6,
                "edge_count": 12,
                "bounding_box": {"xlen": 10, "ylen": 10, "zlen": 10},
            },
        )

        comparator = GeometricComparator(tolerance=0.01, gateway=mock_gateway)
        result = comparator.compare_with_iou("gen_code", "gt_code")

        # Volume mismatch should cause failure
        assert result.volume_match is False
        assert result.iou_score == 0.5
        assert result.iou_pass is False  # Below 0.9 threshold

    def test_compare_with_iou_uses_provided_props(self, mock_gateway):
        """compare_with_iou uses provided props over IoU result props."""
        mock_gateway.compute_iou.return_value = IoUResult(
            iou_score=1.0,
            intersection_volume=1000.0,
            union_volume=1000.0,
            generated_volume=1000.0,
            ground_truth_volume=1000.0,
            generated_props={"volume": 999.0},  # Slightly off
            ground_truth_props={"volume": 1000.0},
        )

        # Provide explicit props that match
        gen_props = {
            "volume": 1000.0,
            "face_count": 6,
            "edge_count": 12,
            "bounding_box": {"xlen": 10, "ylen": 10, "zlen": 10},
        }
        gt_props = {
            "volume": 1000.0,
            "face_count": 6,
            "edge_count": 12,
            "bounding_box": {"xlen": 10, "ylen": 10, "zlen": 10},
        }

        comparator = GeometricComparator(tolerance=0.01, gateway=mock_gateway)
        result = comparator.compare_with_iou(
            "gen_code",
            "gt_code",
            generated_props=gen_props,
            ground_truth_props=gt_props,
        )

        # Should pass because provided props match
        assert result.volume_match is True
