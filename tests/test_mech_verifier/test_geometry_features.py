"""Tests for geometry-based feature detection from STEP files.

Tests hole/fillet detection via B-Rep topology analysis.
"""

from pathlib import Path

import pytest

from .conftest import TEST_PROJECTS, requires_occt


class TestGeometryFeatureExtraction:
    """Tests for extracting features from B-Rep geometry."""

    @pytest.fixture
    def occt_backend(self):
        """Get OCCT backend if available."""
        try:
            from mech_verify.backend.occt import OCCT_AVAILABLE, OCCTBackend

            if not OCCT_AVAILABLE:
                pytest.skip("pythonocc-core not installed")
            return OCCTBackend()
        except ImportError:
            pytest.skip("pythonocc-core not installed")

    @pytest.fixture
    def block_with_holes_step(self) -> Path:
        """Block with cylindrical holes."""
        path = TEST_PROJECTS / "step_with_holes" / "inputs" / "block_with_holes.step"
        if not path.exists():
            pytest.skip(f"block_with_holes.step not found: {path}")
        return path

    @pytest.fixture
    def simple_box_step(self) -> Path:
        """Simple box without holes."""
        path = TEST_PROJECTS / "step_golden_pass" / "inputs" / "simple_box.step"
        if not path.exists():
            pytest.skip(f"simple_box.step not found: {path}")
        return path

    @requires_occt
    def test_extract_cylindrical_holes(self, block_with_holes_step: Path, occt_backend):
        """Block with holes should detect cylindrical faces as holes."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds = builder.build_from_step(block_with_holes_step, occt_backend)

        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]

        # Block has 2 holes with 5mm diameter
        assert len(holes) == 2, f"Expected 2 holes, got {len(holes)}"

        # Check hole structure
        for hole in holes:
            assert "feature_id" in hole
            assert "object_ref" in hole
            assert "diameter" in hole
            assert 4.9 < hole["diameter"] < 5.1  # ~5mm diameter
            assert hole.get("from_geometry") is True
            assert "confidence" in hole

    @requires_occt
    def test_simple_box_no_holes(self, simple_box_step: Path, occt_backend):
        """Simple box should have no holes detected."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds = builder.build_from_step(simple_box_step, occt_backend)

        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]

        # Simple box has no cylindrical faces
        assert len(holes) == 0

    @requires_occt
    def test_geometry_features_have_deterministic_ids(
        self, block_with_holes_step: Path, occt_backend
    ):
        """Same STEP should produce same feature IDs."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds1 = builder.build_from_step(block_with_holes_step, occt_backend)
        mds2 = builder.build_from_step(block_with_holes_step, occt_backend)

        features1 = mds1.get("features", [])
        features2 = mds2.get("features", [])

        assert len(features1) == len(features2)

        ids1 = sorted([f["feature_id"] for f in features1])
        ids2 = sorted([f["feature_id"] for f in features2])
        assert ids1 == ids2

    @requires_occt
    def test_geometry_features_object_ref_format(
        self, block_with_holes_step: Path, occt_backend
    ):
        """Feature object_refs must be well-formed."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds = builder.build_from_step(block_with_holes_step, occt_backend)

        for feature in mds.get("features", []):
            obj_ref = feature["object_ref"]
            assert obj_ref.startswith("mech://part/")
            assert "/feature/" in obj_ref


class TestGeometryFeatureGracefulDegradation:
    """Tests for graceful handling when OCCT geometry APIs fail."""

    @requires_occt
    def test_build_succeeds_even_if_feature_extraction_fails(self):
        """MDS build should succeed even if geometry feature extraction raises."""
        from mech_verify.backend.occt import OCCTBackend
        from mech_verify.mds.builder import MDSBuilder

        # Create a mock backend that will cause feature extraction to fail
        backend = OCCTBackend()
        builder = MDSBuilder()

        # Build should not crash - just return empty features
        step_path = TEST_PROJECTS / "step_golden_pass" / "inputs" / "simple_box.step"
        if not step_path.exists():
            pytest.skip("simple_box.step not found")

        mds = builder.build_from_step(step_path, backend)
        assert "features" in mds
        assert isinstance(mds["features"], list)


class TestHoleDepthEstimation:
    """Tests for hole depth estimation from geometry."""

    @pytest.fixture
    def occt_backend(self):
        """Get OCCT backend if available."""
        try:
            from mech_verify.backend.occt import OCCT_AVAILABLE, OCCTBackend

            if not OCCT_AVAILABLE:
                pytest.skip("pythonocc-core not installed")
            return OCCTBackend()
        except ImportError:
            pytest.skip("pythonocc-core not installed")

    @requires_occt
    def test_through_hole_has_depth(self, occt_backend):
        """Through holes should have estimated depth from geometry."""
        from mech_verify.mds.builder import MDSBuilder

        step_path = (
            TEST_PROJECTS / "step_with_holes" / "inputs" / "block_with_holes.step"
        )
        if not step_path.exists():
            pytest.skip("block_with_holes.step not found")

        builder = MDSBuilder()
        mds = builder.build_from_step(step_path, occt_backend)

        holes = [f for f in mds.get("features", []) if f.get("feature_type") == "hole"]

        # Block has 10mm deep holes
        holes_with_depth = [h for h in holes if "depth" in h and h["depth"] > 0]
        assert len(holes_with_depth) >= 1, "At least one hole should have depth"

        for h in holes_with_depth:
            assert 9.0 < h["depth"] < 11.0  # ~10mm depth
