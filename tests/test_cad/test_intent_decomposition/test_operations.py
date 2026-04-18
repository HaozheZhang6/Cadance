"""Tests for CAD operations module."""

import pytest

from src.cad.intent_decomposition.operations import (
    CADIntentParser,
    CADOperation,
    CADPrimitive,
    OperationParameter,
    OperationSequence,
    PrimitiveCategory,
)
from src.cad.intent_decomposition.operations.intent_parser import MockCADIntentParser


class TestCADPrimitive:
    """Tests for CADPrimitive enum."""

    def test_primitive_values(self):
        """Primitives should have expected string values."""
        assert CADPrimitive.BOX.value == "box"
        assert CADPrimitive.CYLINDER.value == "cylinder"
        assert CADPrimitive.HOLE.value == "hole"
        assert CADPrimitive.FILLET.value == "fillet"

    def test_primitive_category(self):
        """Primitives should have correct categories."""
        assert CADPrimitive.BOX.category == PrimitiveCategory.SOLID_CREATION
        assert CADPrimitive.SKETCH_CIRCLE.category == PrimitiveCategory.SKETCH_2D
        assert CADPrimitive.EXTRUDE.category == PrimitiveCategory.TRANSFORM_3D
        assert CADPrimitive.HOLE.category == PrimitiveCategory.FEATURE_MODIFICATION
        assert CADPrimitive.UNION.category == PrimitiveCategory.BOOLEAN_OPERATION
        assert CADPrimitive.LINEAR_PATTERN.category == PrimitiveCategory.PATTERN
        assert CADPrimitive.SELECT_FACE.category == PrimitiveCategory.GEOMETRY_SELECTION

    def test_by_category(self):
        """Should get primitives by category."""
        solids = CADPrimitive.by_category(PrimitiveCategory.SOLID_CREATION)
        assert CADPrimitive.BOX in solids
        assert CADPrimitive.CYLINDER in solids
        assert CADPrimitive.SPHERE in solids
        assert CADPrimitive.HOLE not in solids

    def test_all_primitives_have_categories(self):
        """Every primitive should have a category."""
        for prim in CADPrimitive:
            assert prim.category is not None


class TestPrimitiveCategory:
    """Tests for PrimitiveCategory enum."""

    def test_category_values(self):
        """Categories should have expected values."""
        assert PrimitiveCategory.SOLID_CREATION.value == "solid_creation"
        assert PrimitiveCategory.SKETCH_2D.value == "sketch_2d"
        assert PrimitiveCategory.FEATURE_MODIFICATION.value == "feature_modification"


class TestOperationParameter:
    """Tests for OperationParameter dataclass."""

    def test_parameter_creation(self):
        """Parameter should be creatable with basic values."""
        param = OperationParameter("length", 100, "mm")
        assert param.name == "length"
        assert param.value == 100
        assert param.unit == "mm"
        assert param.inferred is False

    def test_parameter_inferred(self):
        """Parameter should track inferred flag."""
        param = OperationParameter("depth", 50, "mm", inferred=True)
        assert param.inferred is True

    def test_parameter_str(self):
        """Parameter should have readable string repr."""
        param = OperationParameter("radius", 25, "mm")
        assert str(param) == "radius=25 mm"

    def test_parameter_str_no_unit(self):
        """Parameter without unit should format correctly."""
        param = OperationParameter("count", 5)
        assert str(param) == "count=5"

    def test_parameter_str_inferred(self):
        """Inferred parameter should show marker."""
        param = OperationParameter("height", 30, "mm", inferred=True)
        assert "(inferred)" in str(param)


class TestCADOperation:
    """Tests for CADOperation dataclass."""

    @pytest.fixture
    def box_operation(self):
        """Create a sample box operation."""
        return CADOperation(
            primitive=CADPrimitive.BOX,
            description="Create base box",
            parameters=[
                OperationParameter("length", 100, "mm"),
                OperationParameter("width", 50, "mm"),
                OperationParameter("height", 30, "mm"),
            ],
        )

    def test_operation_creation(self, box_operation):
        """Operation should be creatable."""
        assert box_operation.primitive == CADPrimitive.BOX
        assert len(box_operation.parameters) == 3

    def test_get_parameter(self, box_operation):
        """Should get parameter by name."""
        param = box_operation.get_parameter("length")
        assert param is not None
        assert param.value == 100

    def test_get_parameter_missing(self, box_operation):
        """Should return None for missing parameter."""
        param = box_operation.get_parameter("nonexistent")
        assert param is None

    def test_get_parameter_value(self, box_operation):
        """Should get parameter value directly."""
        assert box_operation.get_parameter_value("width") == 50
        assert box_operation.get_parameter_value("missing", 0) == 0

    def test_operation_str(self, box_operation):
        """Operation should have readable string repr."""
        s = str(box_operation)
        assert "box" in s
        assert "length=100" in s

    def test_operation_with_dependencies(self):
        """Operation should track dependencies."""
        op = CADOperation(
            primitive=CADPrimitive.HOLE,
            description="Add hole",
            dependencies=[0, 1],
        )
        assert op.dependencies == [0, 1]


class TestOperationSequence:
    """Tests for OperationSequence dataclass."""

    @pytest.fixture
    def sequence(self):
        """Create a sample operation sequence."""
        seq = OperationSequence(original_intent="Create a box with a hole")
        seq.add_operation(
            CADOperation(
                primitive=CADPrimitive.BOX,
                description="Create box",
                parameters=[OperationParameter("length", 100, "mm")],
            )
        )
        seq.add_operation(
            CADOperation(
                primitive=CADPrimitive.SELECT_FACE,
                description="Select top face",
                dependencies=[0],
            )
        )
        seq.add_operation(
            CADOperation(
                primitive=CADPrimitive.HOLE,
                description="Add hole",
                dependencies=[1],
            )
        )
        return seq

    def test_sequence_length(self, sequence):
        """Sequence should report correct length."""
        assert len(sequence) == 3

    def test_sequence_iteration(self, sequence):
        """Sequence should be iterable."""
        primitives = [op.primitive for op in sequence]
        assert primitives == [
            CADPrimitive.BOX,
            CADPrimitive.SELECT_FACE,
            CADPrimitive.HOLE,
        ]

    def test_sequence_indexing(self, sequence):
        """Sequence should support indexing."""
        assert sequence[0].primitive == CADPrimitive.BOX
        assert sequence[2].primitive == CADPrimitive.HOLE

    def test_add_operation_returns_index(self):
        """add_operation should return the index."""
        seq = OperationSequence()
        idx = seq.add_operation(CADOperation(CADPrimitive.BOX, "box"))
        assert idx == 0
        idx = seq.add_operation(CADOperation(CADPrimitive.HOLE, "hole"))
        assert idx == 1

    def test_get_by_primitive(self, sequence):
        """Should get operations by primitive type."""
        boxes = sequence.get_by_primitive(CADPrimitive.BOX)
        assert len(boxes) == 1
        assert boxes[0].description == "Create box"

    def test_primitives_used(self, sequence):
        """Should get set of primitives used."""
        primitives = sequence.primitives_used()
        assert CADPrimitive.BOX in primitives
        assert CADPrimitive.HOLE in primitives
        assert CADPrimitive.FILLET not in primitives

    def test_sequence_summary(self, sequence):
        """Summary should contain key info."""
        summary = sequence.summary()
        assert "box with a hole" in summary
        assert "Operations: 3" in summary


class TestCADIntentParser:
    """Tests for CADIntentParser."""

    def test_parser_with_mock_llm(self):
        """Parser should work with mock LLM."""
        from src.cad.intent_decomposition.llm import MockLLMClient

        # Mock returns empty dict, so parser will return empty sequence
        mock_llm = MockLLMClient(default_response="{}")
        parser = CADIntentParser(llm=mock_llm)
        result = parser.parse("Create a box")
        assert isinstance(result, OperationSequence)

    def test_parser_empty_intent_raises(self):
        """Parser should raise for empty intent."""
        parser = MockCADIntentParser()
        with pytest.raises(ValueError, match="empty"):
            parser.parse("")

    def test_parser_whitespace_intent_raises(self):
        """Parser should raise for whitespace-only intent."""
        parser = MockCADIntentParser()
        with pytest.raises(ValueError, match="empty"):
            parser.parse("   ")


class TestMockCADIntentParser:
    """Tests for MockCADIntentParser."""

    def test_mock_parser_returns_sequence(self):
        """Mock parser should return an OperationSequence."""
        parser = MockCADIntentParser()
        result = parser.parse("Create a box")
        assert isinstance(result, OperationSequence)

    def test_mock_parser_default_response(self):
        """Mock parser should return default box operation."""
        parser = MockCADIntentParser()
        result = parser.parse("anything")
        assert len(result) == 1
        assert result[0].primitive == CADPrimitive.BOX

    def test_mock_parser_custom_response(self):
        """Mock parser should use custom response if provided."""
        custom = OperationSequence(
            original_intent="custom",
            operations=[CADOperation(CADPrimitive.CYLINDER, "test cylinder")],
        )
        parser = MockCADIntentParser(mock_response=custom)
        result = parser.parse("anything")
        assert len(result) == 1
        assert result[0].primitive == CADPrimitive.CYLINDER

    def test_mock_parser_preserves_intent(self):
        """Mock parser should preserve original intent."""
        parser = MockCADIntentParser()
        result = parser.parse("Create a special box")
        assert "special box" in result.original_intent


class TestPrimitiveMatching:
    """Tests for primitive name matching in parser."""

    def test_match_direct(self):
        """Should match exact primitive names."""
        parser = CADIntentParser.__new__(CADIntentParser)
        assert parser._match_primitive("box") == CADPrimitive.BOX
        assert parser._match_primitive("cylinder") == CADPrimitive.CYLINDER

    def test_match_with_spaces(self):
        """Should handle spaces/hyphens."""
        parser = CADIntentParser.__new__(CADIntentParser)
        assert (
            parser._match_primitive("sketch rectangle") == CADPrimitive.SKETCH_RECTANGLE
        )
        assert parser._match_primitive("sketch-circle") == CADPrimitive.SKETCH_CIRCLE

    def test_match_variations(self):
        """Should match common variations."""
        parser = CADIntentParser.__new__(CADIntentParser)
        assert parser._match_primitive("rect") == CADPrimitive.SKETCH_RECTANGLE
        assert parser._match_primitive("round") == CADPrimitive.FILLET
        assert parser._match_primitive("bevel") == CADPrimitive.CHAMFER

    def test_match_unknown(self):
        """Should return None for unknown primitives."""
        parser = CADIntentParser.__new__(CADIntentParser)
        assert parser._match_primitive("unknown_primitive") is None
