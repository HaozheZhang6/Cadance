"""Tests for IoU-based geometric comparison via gateway.

Tests the gateway.compute_iou method for various geometric comparison scenarios.
These are integration tests requiring the CadQuery subprocess venv.
"""

import pytest

from src.tools.gateway import IoUResult


@pytest.mark.integration
class TestComputeIoUViaGateway:
    """Tests for IoU computation via gateway."""

    def test_identical_boxes(self, real_gateway):
        """Identical boxes should have IoU = 1.0."""
        code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", code, code)

        assert result is not None
        assert isinstance(result, IoUResult)
        assert result.iou_score == pytest.approx(1.0, rel=0.01)
        assert result.intersection_volume == pytest.approx(1000.0, rel=0.01)
        assert result.union_volume == pytest.approx(1000.0, rel=0.01)

    def test_identical_cylinders(self, real_gateway):
        """Identical cylinders should have IoU = 1.0."""
        code = """import cadquery as cq
result = cq.Workplane("XY").cylinder(20, 5)
"""
        result = real_gateway.compute_iou("cadquery", code, code)

        assert result is not None
        assert result.iou_score == pytest.approx(1.0, rel=0.01)

    def test_no_overlap_separated_boxes(self, real_gateway):
        """Non-overlapping boxes should have IoU = 0.0."""
        box1_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        box2_code = """import cadquery as cq
result = cq.Workplane("XY").center(100, 0).box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", box1_code, box2_code)

        assert result is not None
        assert result.iou_score == pytest.approx(0.0, abs=0.01)
        assert result.intersection_volume == pytest.approx(0.0, abs=0.01)
        # Union should be sum of two boxes (2000)
        assert result.union_volume == pytest.approx(2000.0, rel=0.01)

    def test_partial_overlap_boxes(self, real_gateway):
        """Partially overlapping boxes should have 0 < IoU < 1."""
        box1_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        box2_code = """import cadquery as cq
result = cq.Workplane("XY").center(5, 0).box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", box1_code, box2_code)

        assert result is not None
        assert 0.0 < result.iou_score < 1.0
        # Expected IoU is approximately 1/3
        assert result.iou_score == pytest.approx(0.333, rel=0.1)

    def test_one_inside_other(self, real_gateway):
        """Small box inside large box."""
        large_code = """import cadquery as cq
result = cq.Workplane("XY").box(20, 20, 20)
"""
        small_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", small_code, large_code)

        assert result is not None
        assert result.iou_score == pytest.approx(0.125, rel=0.05)
        assert result.intersection_volume == pytest.approx(1000.0, rel=0.05)
        assert result.union_volume == pytest.approx(8000.0, rel=0.05)

    def test_result_contains_volumes(self, real_gateway):
        """IoUResult should contain all volume information."""
        small_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        large_code = """import cadquery as cq
result = cq.Workplane("XY").box(20, 20, 20)
"""
        result = real_gateway.compute_iou("cadquery", small_code, large_code)

        assert result is not None
        assert result.generated_volume == pytest.approx(1000.0, rel=0.01)
        assert result.ground_truth_volume == pytest.approx(8000.0, rel=0.01)
        assert result.intersection_volume > 0
        assert result.union_volume > 0

    def test_result_contains_props(self, real_gateway):
        """IoUResult should contain geometry properties."""
        code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", code, code)

        assert result is not None
        assert result.generated_props.get("volume") == pytest.approx(1000.0, rel=0.01)
        assert result.generated_props.get("face_count") == 6
        assert result.ground_truth_props.get("volume") == pytest.approx(
            1000.0, rel=0.01
        )

    def test_iou_clamped_to_valid_range(self, real_gateway):
        """IoU should always be between 0 and 1."""
        box_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        separated_code = """import cadquery as cq
result = cq.Workplane("XY").center(100, 0).box(10, 10, 10)
"""
        small_code = """import cadquery as cq
result = cq.Workplane("XY").box(5, 5, 5)
"""

        for code1, code2 in [
            (box_code, box_code),
            (box_code, separated_code),
            (box_code, small_code),
        ]:
            result = real_gateway.compute_iou("cadquery", code1, code2)
            assert result is not None
            assert 0.0 <= result.iou_score <= 1.0


@pytest.mark.integration
class TestIoUThresholds:
    """Tests for IoU threshold behavior."""

    def test_high_iou_above_90_threshold(self, real_gateway):
        """Test that similar shapes achieve > 0.9 IoU."""
        box1_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        box2_code = """import cadquery as cq
result = cq.Workplane("XY").box(10.1, 10.1, 10.1)
"""
        result = real_gateway.compute_iou("cadquery", box1_code, box2_code)

        assert result is not None
        assert result.iou_score > 0.9

    def test_moderate_iou_around_70_threshold(self, real_gateway):
        """Test shapes with moderate overlap achieve ~0.7 IoU."""
        box1_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        box2_code = """import cadquery as cq
result = cq.Workplane("XY").center(3, 0).box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", box1_code, box2_code)

        assert result is not None
        assert 0.5 < result.iou_score < 0.9

    def test_low_iou_different_shapes(self, real_gateway):
        """Different shape types should have lower IoU."""
        box_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        cyl_code = """import cadquery as cq
result = cq.Workplane("XY").cylinder(10, 5.64)
"""
        result = real_gateway.compute_iou("cadquery", box_code, cyl_code)

        assert result is not None
        assert result.iou_score < 0.9


@pytest.mark.integration
class TestComputeIoUErrors:
    """Tests for IoU error handling."""

    def test_returns_none_for_syntax_error(self, real_gateway):
        """Should return None when code has syntax error."""
        good_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        bad_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10,
"""
        result = real_gateway.compute_iou("cadquery", good_code, bad_code)
        assert result is None

    def test_returns_none_for_missing_result(self, real_gateway):
        """Should return None when code doesn't define result."""
        good_code = """import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        bad_code = """import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
"""
        result = real_gateway.compute_iou("cadquery", good_code, bad_code)
        assert result is None
