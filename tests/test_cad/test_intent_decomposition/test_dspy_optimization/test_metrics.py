"""Tests for DSPy optimization metrics."""

import json
from dataclasses import dataclass
from typing import Any

from src.cad.intent_decomposition.dspy_optimization.metrics import (
    _check_spatial_patterns,
    _code_addresses_error,
    code_generation_proxy_metric,
    decomposition_metric,
    error_correction_metric,
)


@dataclass
class MockPrediction:
    """Mock prediction object for testing metrics."""

    operations: str = ""
    code: str = ""
    fixed_code: str = ""


@dataclass
class MockExample:
    """Mock example object for testing metrics."""

    intent: str = ""
    operations: str = "[]"
    code: str = ""
    error_message: str = ""


class TestDecompositionMetric:
    """Tests for decomposition_metric()."""

    def test_valid_json_with_primitives(self):
        """Valid JSON with known primitives should score well."""
        operations = json.dumps(
            [
                {"primitive": "box", "parameters": [{"name": "length", "value": 10}]},
                {
                    "primitive": "cylinder",
                    "parameters": [{"name": "radius", "value": 5}],
                },
            ]
        )
        prediction = MockPrediction(operations=operations)
        example = MockExample()

        score = decomposition_metric(example, prediction)
        assert score > 0.5  # Should get points for valid JSON, primitives, params

    def test_invalid_json_returns_zero(self):
        """Invalid JSON should return 0."""
        prediction = MockPrediction(operations="not valid json {[}")
        example = MockExample()

        score = decomposition_metric(example, prediction)
        assert score == 0.0

    def test_empty_operations_list(self):
        """Empty operations list should get only JSON validity points."""
        prediction = MockPrediction(operations="[]")
        example = MockExample()

        score = decomposition_metric(example, prediction)
        assert score == 0.3  # Only valid JSON points

    def test_unknown_primitives(self):
        """Unknown primitives should reduce score."""
        operations = json.dumps(
            [
                {"primitive": "unknown_operation", "parameters": []},
            ]
        )
        prediction = MockPrediction(operations=operations)
        example = MockExample()

        score = decomposition_metric(example, prediction)
        # Gets JSON points (0.3), no primitive points (0.0), params present (0.2 since empty list counts)
        # Dependencies valid (0.2 since no deps = valid)
        # Total: 0.3 + 0 + 0 + 0.2 = 0.5 (or more if params counted differently)
        assert score >= 0.3  # At least JSON points
        assert score < 1.0  # Less than perfect

    def test_valid_dependencies(self):
        """Valid dependencies should contribute to score."""
        operations = json.dumps(
            [
                {"primitive": "box", "parameters": [], "dependencies": []},
                {
                    "primitive": "hole",
                    "parameters": [],
                    "dependencies": [0],
                },  # Depends on first
            ]
        )
        prediction = MockPrediction(operations=operations)
        example = MockExample()

        score = decomposition_metric(example, prediction)
        assert score > 0.5  # Should get dependency points

    def test_invalid_dependencies(self):
        """Invalid dependencies should reduce score."""
        operations = json.dumps(
            [
                {
                    "primitive": "box",
                    "parameters": [],
                    "dependencies": [5],
                },  # Invalid: refs future
            ]
        )
        prediction = MockPrediction(operations=operations)
        example = MockExample()

        score = decomposition_metric(example, prediction)
        # Should lose dependency points
        assert score < 0.8


class TestCodeGenerationProxyMetric:
    """Tests for code_generation_proxy_metric()."""

    def test_valid_syntax_with_result(self):
        """Valid syntax with result variable should score well."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        prediction = MockPrediction(code=code)
        example = MockExample(operations=json.dumps([{"primitive": "box"}]))

        score = code_generation_proxy_metric(example, prediction)
        assert score > 0.5  # Syntax, import, result, pattern match

    def test_syntax_error_returns_zero(self):
        """Syntax errors should return 0."""
        code = "def broken("  # Missing closing paren
        prediction = MockPrediction(code=code)
        example = MockExample()

        score = code_generation_proxy_metric(example, prediction)
        assert score == 0.0

    def test_empty_code_returns_zero(self):
        """Empty code should return 0."""
        prediction = MockPrediction(code="")
        example = MockExample()

        score = code_generation_proxy_metric(example, prediction)
        assert score == 0.0

    def test_missing_result_variable(self):
        """Code without result variable loses points."""
        code = """
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
"""
        prediction = MockPrediction(code=code)
        example = MockExample()

        score = code_generation_proxy_metric(example, prediction)
        # Gets syntax (0.2) and import (0.1), but not result (0.0)
        # Also gets partial pattern score (0.5 * pattern_score)
        # Score is less than 1.0 and doesn't get result bonus
        assert score >= 0.2  # At least syntax
        assert score < 1.0  # Not perfect

    def test_pattern_matching_box(self):
        """Box operation should match .box() in code."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        prediction = MockPrediction(code=code)
        example = MockExample(operations=json.dumps([{"primitive": "box"}]))

        score = code_generation_proxy_metric(example, prediction)
        assert score > 0.8  # All checks should pass


class TestCheckSpatialPatterns:
    """Tests for _check_spatial_patterns() helper."""

    def test_box_pattern(self):
        """Box primitive should match .box() call."""
        code = "result = cq.Workplane('XY').box(10, 10, 10)"
        operations = [{"primitive": "box"}]

        score = _check_spatial_patterns(code, operations)
        assert score == 1.0

    def test_cylinder_pattern(self):
        """Cylinder primitive should match .cylinder() call."""
        code = "result = cq.Workplane('XY').cylinder(10, 5)"
        operations = [{"primitive": "cylinder"}]

        score = _check_spatial_patterns(code, operations)
        assert score == 1.0

    def test_multiple_operations(self):
        """Multiple operations should be checked."""
        code = "result = cq.Workplane('XY').box(10, 10, 10).hole(5)"
        operations = [{"primitive": "box"}, {"primitive": "hole"}]

        score = _check_spatial_patterns(code, operations)
        assert score == 1.0

    def test_missing_pattern(self):
        """Missing operation patterns reduce score."""
        code = "result = cq.Workplane('XY').box(10, 10, 10)"
        operations = [{"primitive": "box"}, {"primitive": "cylinder"}]

        score = _check_spatial_patterns(code, operations)
        assert score == 0.5  # Only box matches

    def test_empty_operations(self):
        """Empty operations list gives partial credit."""
        code = "result = cq.Workplane('XY').box(10, 10, 10)"
        operations: list[dict[str, Any]] = []

        score = _check_spatial_patterns(code, operations)
        assert score == 0.5


class TestErrorCorrectionMetric:
    """Tests for error_correction_metric()."""

    def test_valid_fix_different_from_original(self):
        """Valid fix that differs from original should score well."""
        example = MockExample(
            code="result = cq.box()",  # Missing Workplane
            error_message="AttributeError: 'module' object has no attribute 'box'",
        )
        prediction = MockPrediction(
            fixed_code="result = cq.Workplane('XY').box(10, 10, 10)"
        )

        score = error_correction_metric(example, prediction)
        assert score >= 0.5  # Syntax OK, different, addresses error

    def test_syntax_error_in_fix_returns_zero(self):
        """Syntax error in fixed code returns 0."""
        example = MockExample(code="result = broken", error_message="SyntaxError")
        prediction = MockPrediction(fixed_code="result = also broken(")

        score = error_correction_metric(example, prediction)
        assert score == 0.0

    def test_empty_fixed_code_returns_zero(self):
        """Empty fixed code returns 0."""
        example = MockExample(code="x = 1", error_message="Error")
        prediction = MockPrediction(fixed_code="")

        score = error_correction_metric(example, prediction)
        assert score == 0.0

    def test_identical_code_loses_points(self):
        """Fix identical to original loses difference points."""
        original = "result = cq.box(10)"
        example = MockExample(code=original, error_message="Error")
        prediction = MockPrediction(fixed_code=original)

        score = error_correction_metric(example, prediction)
        # Gets syntax points (0.3) but loses difference (0.2) and error addressing
        assert score < 0.5


class TestCodeAddressesError:
    """Tests for _code_addresses_error() helper."""

    def test_attribute_error_with_different_code(self):
        """AttributeError with changed code should be addressed."""
        result = _code_addresses_error(
            fixed_code="result = obj.new_method()",
            original_code="result = obj.old_method()",
            error_message="AttributeError: 'obj' has no attribute 'old_method'",
        )
        assert result is True

    def test_name_error_with_added_import(self):
        """NameError addressed by adding import."""
        result = _code_addresses_error(
            fixed_code="import math\nresult = math.sqrt(4)",
            original_code="result = math.sqrt(4)",
            error_message="NameError: name 'math' is not defined",
        )
        assert result is True

    def test_same_code_returns_false(self):
        """Same code doesn't address error."""
        code = "result = x + 1"
        result = _code_addresses_error(
            fixed_code=code, original_code=code, error_message="SomeError"
        )
        assert result is False
