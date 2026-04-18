"""Tests for tolerance parsing module."""

import pytest

from src.verification.semantic.tolerance_parser import parse_tolerance


# Percentage tests
def test_parse_percentage_tolerance_5pct():
    min_v, max_v = parse_tolerance(100.0, "+/- 5%")
    assert min_v == 95.0
    assert max_v == 105.0


def test_parse_percentage_tolerance_unicode_plusminus():
    min_v, max_v = parse_tolerance(100.0, "± 5%")
    assert min_v == 95.0
    assert max_v == 105.0


def test_parse_percentage_tolerance_10pct():
    min_v, max_v = parse_tolerance(200.0, "+/- 10%")
    assert min_v == pytest.approx(180.0)
    assert max_v == pytest.approx(220.0)


def test_parse_percentage_tolerance_with_spaces():
    min_v, max_v = parse_tolerance(100.0, "+/- 5 %")
    assert min_v == 95.0
    assert max_v == 105.0


# Absolute tests
def test_parse_absolute_tolerance():
    min_v, max_v = parse_tolerance(10.0, "+/- 0.5")
    assert min_v == 9.5
    assert max_v == 10.5


def test_parse_absolute_tolerance_unicode():
    min_v, max_v = parse_tolerance(10.0, "± 0.5")
    assert min_v == 9.5
    assert max_v == 10.5


def test_parse_absolute_tolerance_larger_delta():
    min_v, max_v = parse_tolerance(50.0, "+/- 5")
    assert min_v == 45.0
    assert max_v == 55.0


# Range tests
def test_parse_range_tolerance():
    min_v, max_v = parse_tolerance(10.0, "8-12")
    assert min_v == 8.0
    assert max_v == 12.0


def test_parse_range_tolerance_floats():
    min_v, max_v = parse_tolerance(0.0, "2.5-3.5")
    assert min_v == 2.5
    assert max_v == 3.5


def test_parse_range_tolerance_with_spaces():
    min_v, max_v = parse_tolerance(0.0, "8 - 12")
    assert min_v == 8.0
    assert max_v == 12.0


# Error cases
def test_parse_unparseable_tolerance_raises():
    with pytest.raises(ValueError, match="Cannot parse"):
        parse_tolerance(10.0, "approximately")


def test_parse_empty_tolerance_raises():
    with pytest.raises(ValueError):
        parse_tolerance(10.0, "")


def test_parse_whitespace_only_raises():
    with pytest.raises(ValueError):
        parse_tolerance(10.0, "   ")


def test_parse_invalid_format_raises():
    with pytest.raises(ValueError, match="Cannot parse"):
        parse_tolerance(10.0, "random text")


# Edge cases
def test_parse_percentage_zero():
    min_v, max_v = parse_tolerance(100.0, "+/- 0%")
    assert min_v == 100.0
    assert max_v == 100.0


def test_parse_percentage_decimal():
    min_v, max_v = parse_tolerance(1000.0, "+/- 2.5%")
    assert min_v == 975.0
    assert max_v == 1025.0


def test_parse_absolute_with_decimal():
    min_v, max_v = parse_tolerance(10.0, "+/- 0.25")
    assert min_v == 9.75
    assert max_v == 10.25


def test_parse_range_with_decimals():
    min_v, max_v = parse_tolerance(0.0, "1.5-2.5")
    assert min_v == 1.5
    assert max_v == 2.5


# Tolerance-before-conversion tests (BF-2 fix)
def test_parse_tolerance_does_not_convert_units():
    """Parser returns values in original units, no conversion."""
    min_v, max_v = parse_tolerance(4.0, "+/- 0.2")
    assert min_v == pytest.approx(3.8)
    assert max_v == pytest.approx(4.2)


def test_parse_percentage_tolerance_original_units():
    """Percentage tolerance computed in original units."""
    min_v, max_v = parse_tolerance(100.0, "+/- 5%")
    assert min_v == 95.0
    assert max_v == 105.0


def test_parse_range_tolerance_original_units():
    """Range tolerance uses range values directly."""
    min_v, max_v = parse_tolerance(10.0, "7-13")
    assert min_v == 7.0
    assert max_v == 13.0


# One-sided constraint tests (NEW for 07-02)
def test_one_sided_min():
    """min tolerance compiles to (value, None) for >= inequality."""
    from src.verification.semantic.tolerance_parser import parse_one_sided

    min_v, max_v = parse_one_sided(12.0, "min")
    assert min_v == 12.0
    assert max_v is None


def test_one_sided_max():
    """max tolerance compiles to (None, value) for <= inequality."""
    from src.verification.semantic.tolerance_parser import parse_one_sided

    min_v, max_v = parse_one_sided(500.0, "max")
    assert min_v is None
    assert max_v == 500.0


def test_one_sided_gte_operator():
    """'>=' tolerance compiles to (value, None)."""
    from src.verification.semantic.tolerance_parser import parse_one_sided

    min_v, max_v = parse_one_sided(5.0, ">=")
    assert min_v == 5.0
    assert max_v is None


def test_one_sided_lte_operator():
    """'<=' tolerance compiles to (None, value)."""
    from src.verification.semantic.tolerance_parser import parse_one_sided

    min_v, max_v = parse_one_sided(10.0, "<=")
    assert min_v is None
    assert max_v == 10.0


def test_one_sided_minimum():
    """'minimum' tolerance compiles to (value, None)."""
    from src.verification.semantic.tolerance_parser import parse_one_sided

    min_v, max_v = parse_one_sided(1.0, "minimum")
    assert min_v == 1.0
    assert max_v is None


def test_one_sided_maximum():
    """'maximum' tolerance compiles to (None, value)."""
    from src.verification.semantic.tolerance_parser import parse_one_sided

    min_v, max_v = parse_one_sided(100.0, "maximum")
    assert min_v is None
    assert max_v == 100.0


def test_classify_tolerance_one_sided():
    """classify_tolerance detects one-sided constraints."""
    from src.verification.semantic.tolerance_parser import classify_tolerance

    assert classify_tolerance("min") == "ONE_SIDED"
    assert classify_tolerance("max") == "ONE_SIDED"
    assert classify_tolerance(">=") == "ONE_SIDED"
    assert classify_tolerance("<=") == "ONE_SIDED"
    assert classify_tolerance("minimum") == "ONE_SIDED"
    assert classify_tolerance("maximum") == "ONE_SIDED"


def test_classify_tolerance_ambiguous():
    """classify_tolerance detects ambiguous tolerances."""
    from src.verification.semantic.tolerance_parser import classify_tolerance

    assert classify_tolerance("~5") == "AMBIGUOUS"
    assert classify_tolerance("approx") == "AMBIGUOUS"
    assert classify_tolerance("approximately") == "AMBIGUOUS"
    assert classify_tolerance("about 5mm") == "AMBIGUOUS"
    assert classify_tolerance("roughly 10") == "AMBIGUOUS"


def test_classify_tolerance_existing_types():
    """classify_tolerance detects existing tolerance types."""
    from src.verification.semantic.tolerance_parser import classify_tolerance

    assert classify_tolerance("+/- 5%") == "PERCENTAGE"
    assert classify_tolerance("+/- 0.5") == "ABSOLUTE"
    assert classify_tolerance("8-12") == "RANGE"
