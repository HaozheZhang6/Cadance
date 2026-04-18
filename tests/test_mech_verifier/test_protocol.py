"""Tests for backend protocol and data structures."""

from mech_verify.backend.protocol import BBox, MassProps, Shape


class TestMassProps:
    """Tests for MassProps dataclass."""

    def test_creation(self):
        props = MassProps(
            volume=100.0,
            center_of_mass=(1.0, 2.0, 3.0),
            surface_area=200.0,
        )
        assert props.volume == 100.0
        assert props.center_of_mass == (1.0, 2.0, 3.0)
        assert props.surface_area == 200.0

    def test_to_dict(self):
        props = MassProps(
            volume=100.0,
            center_of_mass=(1.0, 2.0, 3.0),
            surface_area=200.0,
        )
        d = props.to_dict()
        assert d["volume"] == 100.0
        assert d["center_of_mass"] == [1.0, 2.0, 3.0]
        assert d["surface_area"] == 200.0


class TestBBox:
    """Tests for BBox dataclass."""

    def test_creation(self):
        bbox = BBox(
            min_pt=(0.0, 0.0, 0.0),
            max_pt=(10.0, 20.0, 30.0),
        )
        assert bbox.min_pt == (0.0, 0.0, 0.0)
        assert bbox.max_pt == (10.0, 20.0, 30.0)

    def test_dimensions(self):
        bbox = BBox(
            min_pt=(0.0, 5.0, 10.0),
            max_pt=(10.0, 15.0, 40.0),
        )
        assert bbox.dimensions == (10.0, 10.0, 30.0)

    def test_is_degenerate_false(self):
        bbox = BBox(
            min_pt=(0.0, 0.0, 0.0),
            max_pt=(10.0, 20.0, 30.0),
        )
        assert not bbox.is_degenerate

    def test_is_degenerate_zero_dimension(self):
        bbox = BBox(
            min_pt=(0.0, 0.0, 0.0),
            max_pt=(10.0, 0.0, 30.0),
        )
        assert bbox.is_degenerate

    def test_is_degenerate_negative_dimension(self):
        bbox = BBox(
            min_pt=(10.0, 0.0, 0.0),
            max_pt=(0.0, 20.0, 30.0),
        )
        assert bbox.is_degenerate

    def test_to_dict(self):
        bbox = BBox(
            min_pt=(0.0, 0.0, 0.0),
            max_pt=(10.0, 20.0, 30.0),
        )
        d = bbox.to_dict()
        assert d["min_pt"] == [0.0, 0.0, 0.0]
        assert d["max_pt"] == [10.0, 20.0, 30.0]
        assert d["dimensions"] == [10.0, 20.0, 30.0]


class TestShape:
    """Tests for Shape wrapper."""

    def test_creation(self):
        shape = Shape(native="mock_shape", name="test")
        assert shape.native == "mock_shape"
        assert shape.name == "test"

    def test_repr(self):
        shape = Shape(native="mock", name="bracket")
        assert "bracket" in repr(shape)
