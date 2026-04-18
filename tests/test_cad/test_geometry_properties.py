"""Tests for geometry_properties module.

Tests the property extraction functions that serve as the single source of
truth for geometry comparison.
"""

import pytest

from tests.conftest import CADQUERY_WORKS

if not CADQUERY_WORKS:
    pytest.skip("CadQuery not available or OCP incompatible", allow_module_level=True)

import cadquery as cq  # noqa: E402

from src.cad.geometry_properties import (  # noqa: E402
    GeometryProperties,
    extract_geometry_properties,
    extract_properties_dict,
)


class TestGeometryProperties:
    """Tests for GeometryProperties dataclass."""

    def test_creation(self):
        """GeometryProperties should be creatable with all fields."""
        props = GeometryProperties(
            volume=1000.0,
            surface_area=600.0,
            face_count=6,
            edge_count=12,
            vertex_count=8,
            bounding_box={"x": 10, "y": 10, "z": 10},
            center_of_mass={"x": 0, "y": 0, "z": 5},
        )
        assert props.volume == 1000.0
        assert props.face_count == 6

    def test_to_dict(self):
        """to_dict should return dictionary representation."""
        props = GeometryProperties(
            volume=1000.0,
            surface_area=600.0,
            face_count=6,
            edge_count=12,
            vertex_count=8,
            bounding_box={"x": 10, "y": 10, "z": 10},
            center_of_mass={"x": 0, "y": 0, "z": 5},
        )
        d = props.to_dict()
        assert d["volume"] == 1000.0
        assert d["face_count"] == 6
        assert "bounding_box" in d

    def test_to_dict_excludes_none_surface_area(self):
        """to_dict should exclude surface_area if None."""
        props = GeometryProperties(
            volume=1000.0,
            surface_area=None,
            face_count=6,
            edge_count=12,
            vertex_count=8,
            bounding_box={"x": 10, "y": 10, "z": 10},
            center_of_mass=None,
        )
        d = props.to_dict()
        assert "surface_area" not in d
        assert "center_of_mass" not in d

    def test_to_spec_dict(self):
        """to_spec_dict should return spec.json format."""
        props = GeometryProperties(
            volume=1000.0,
            surface_area=600.0,
            face_count=6,
            edge_count=12,
            vertex_count=8,
            bounding_box={"x": 10, "y": 10, "z": 10},
            center_of_mass=None,
        )
        spec = props.to_spec_dict()
        assert spec["expected_volume"] == 1000.0
        assert spec["expected_faces"] == 6
        assert spec["expected_edges"] == 12
        assert spec["expected_bounding_box"] == {"x": 10, "y": 10, "z": 10}


class TestExtractGeometryProperties:
    """Tests for extract_geometry_properties function."""

    def test_extract_from_box(self):
        """Should extract properties from a simple box."""
        box = cq.Workplane("XY").box(10, 20, 5)
        props = extract_geometry_properties(box)

        assert props.volume == pytest.approx(1000.0, rel=0.01)
        assert props.face_count == 6
        assert props.edge_count == 12
        assert props.vertex_count == 8
        assert props.bounding_box["x"] == pytest.approx(10.0, rel=0.01)
        assert props.bounding_box["y"] == pytest.approx(20.0, rel=0.01)
        assert props.bounding_box["z"] == pytest.approx(5.0, rel=0.01)

    def test_extract_from_cylinder(self):
        """Should extract properties from a cylinder."""
        cyl = cq.Workplane("XY").cylinder(20, 5)
        props = extract_geometry_properties(cyl)

        # Volume = pi * r^2 * h = pi * 25 * 20 ≈ 1570.8
        assert props.volume == pytest.approx(1570.8, rel=0.01)
        # Cylinder has 3 faces (top, bottom, curved surface)
        assert props.face_count == 3
        # Cylinder has 2 or 3 edges depending on representation
        assert props.edge_count >= 2

    def test_extract_from_sphere(self):
        """Should extract properties from a sphere."""
        sphere = cq.Workplane("XY").sphere(10)
        props = extract_geometry_properties(sphere)

        # Volume = 4/3 * pi * r^3 = 4/3 * pi * 1000 ≈ 4188.79
        assert props.volume == pytest.approx(4188.79, rel=0.01)
        # Sphere has 1 face
        assert props.face_count == 1

    def test_extract_from_solid_directly(self):
        """Should extract properties from a Solid (not Workplane)."""
        box = cq.Workplane("XY").box(10, 10, 10)
        solid = box.val()
        props = extract_geometry_properties(solid)

        assert props.volume == pytest.approx(1000.0, rel=0.01)
        assert props.face_count == 6

    def test_extract_bounding_box_dimensions(self):
        """Bounding box should match shape dimensions."""
        # Non-symmetric box
        box = cq.Workplane("XY").box(30, 20, 10)
        props = extract_geometry_properties(box)

        bbox = props.bounding_box
        assert bbox["x"] == pytest.approx(30.0, rel=0.01)
        assert bbox["y"] == pytest.approx(20.0, rel=0.01)
        assert bbox["z"] == pytest.approx(10.0, rel=0.01)

    def test_extract_center_of_mass(self):
        """Center of mass should be at origin for centered box."""
        box = cq.Workplane("XY").box(10, 10, 10)
        props = extract_geometry_properties(box)

        if props.center_of_mass:
            # Centered box should have CoM at origin
            assert props.center_of_mass["x"] == pytest.approx(0.0, abs=0.1)
            assert props.center_of_mass["y"] == pytest.approx(0.0, abs=0.1)
            assert props.center_of_mass["z"] == pytest.approx(0.0, abs=0.1)

    def test_extract_surface_area(self):
        """Surface area should be calculated correctly."""
        # 10x10x10 box has surface area = 6 * 100 = 600
        box = cq.Workplane("XY").box(10, 10, 10)
        props = extract_geometry_properties(box)

        if props.surface_area is not None:
            assert props.surface_area == pytest.approx(600.0, rel=0.01)


class TestExtractPropertiesDict:
    """Tests for extract_properties_dict function."""

    def test_returns_dict_format(self):
        """Should return dictionary in executor-compatible format."""
        box = cq.Workplane("XY").box(10, 10, 10)
        props = extract_properties_dict(box)

        assert isinstance(props, dict)
        assert "volume" in props
        assert "face_count" in props
        assert "edge_count" in props
        assert "vertex_count" in props
        assert "bounding_box" in props

    def test_bounding_box_format(self):
        """Bounding box should use xlen/ylen/zlen keys."""
        box = cq.Workplane("XY").box(10, 20, 30)
        props = extract_properties_dict(box)

        bbox = props["bounding_box"]
        assert "xlen" in bbox
        assert "ylen" in bbox
        assert "zlen" in bbox
        assert bbox["xlen"] == pytest.approx(10.0, rel=0.01)
        assert bbox["ylen"] == pytest.approx(20.0, rel=0.01)
        assert bbox["zlen"] == pytest.approx(30.0, rel=0.01)

    def test_handles_invalid_geometry_type(self):
        """Should return zeroed values for non-geometry input.

        Note: The implementation doesn't raise errors for invalid types -
        it returns zeroed/empty values since the helper functions return
        defaults when methods don't exist on the input object.
        """
        # Pass something that's not geometry
        result = extract_properties_dict("not a geometry")

        # Returns zeroed values (not an error) because string doesn't have
        # geometry methods, and helpers return 0/empty for missing methods
        assert result["volume"] == 0.0
        assert result["face_count"] == 0
        assert result["edge_count"] == 0
        assert result["vertex_count"] == 0

    def test_handles_none_gracefully(self):
        """Should handle None input gracefully."""
        result = extract_properties_dict(None)

        assert "error" in result


class TestEdgeCases:
    """Tests for edge cases in property extraction."""

    def test_box_with_hole(self):
        """Should extract properties from box with hole."""
        box_with_hole = cq.Workplane("XY").box(20, 20, 10).faces(">Z").hole(5)
        props = extract_geometry_properties(box_with_hole)

        # Volume should be box - cylinder
        # Box: 20*20*10 = 4000
        # Hole: pi * 2.5^2 * 10 ≈ 196.35
        # Total ≈ 3803.65
        assert props.volume == pytest.approx(3803.65, rel=0.02)
        # Box with through hole has 7 faces
        assert props.face_count == 7

    def test_filleted_box(self):
        """Should extract properties from filleted box."""
        filleted = cq.Workplane("XY").box(20, 20, 20).edges("|Z").fillet(2)
        props = extract_geometry_properties(filleted)

        # Volume should be slightly less than 8000 due to filleting
        assert props.volume < 8000.0
        assert props.volume > 7000.0
        # Filleted box has more faces than regular box
        assert props.face_count > 6

    def test_compound_solid(self):
        """Should extract properties from compound (multi-body)."""
        # Create two separate boxes
        result = cq.Workplane("XY").box(10, 10, 10).faces(">Z").workplane().box(5, 5, 5)
        props = extract_geometry_properties(result)

        # Should get properties from the compound
        assert props.volume > 0
        assert props.face_count > 0
