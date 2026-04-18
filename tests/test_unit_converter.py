"""Tests for unit conversion module."""

import pytest

from src.verification.semantic.unit_converter import (
    CANONICAL_UNITS,
    convert_to_canonical,
)


# Length conversions
def test_convert_mm_to_m():
    val, unit = convert_to_canonical(100.0, "mm")
    assert val == pytest.approx(0.1)
    assert unit == "m"


def test_convert_cm_to_m():
    val, unit = convert_to_canonical(100.0, "cm")
    assert val == pytest.approx(1.0)
    assert unit == "m"


def test_convert_m_unchanged():
    val, unit = convert_to_canonical(5.0, "m")
    assert val == pytest.approx(5.0)
    assert unit == "m"


def test_convert_km_to_m():
    val, unit = convert_to_canonical(2.0, "km")
    assert val == pytest.approx(2000.0)
    assert unit == "m"


# Mass conversions
def test_convert_g_to_kg():
    val, unit = convert_to_canonical(1000.0, "g")
    assert val == pytest.approx(1.0)
    assert unit == "kg"


def test_convert_kg_unchanged():
    val, unit = convert_to_canonical(5.0, "kg")
    assert val == pytest.approx(5.0)
    assert unit == "kg"


def test_convert_mg_to_kg():
    val, unit = convert_to_canonical(1000000.0, "mg")
    assert val == pytest.approx(1.0)
    assert unit == "kg"


# Force conversions
def test_convert_kN_to_N():
    val, unit = convert_to_canonical(1.0, "kN")
    assert val == pytest.approx(1000.0)
    assert unit == "N"


def test_convert_mN_to_N():
    val, unit = convert_to_canonical(1000.0, "mN")
    assert val == pytest.approx(1.0)
    assert unit == "N"


def test_convert_N_unchanged():
    val, unit = convert_to_canonical(10.0, "N")
    assert val == pytest.approx(10.0)
    assert unit == "N"


# Pressure conversions
def test_convert_MPa_to_Pa():
    val, unit = convert_to_canonical(1.0, "MPa")
    assert val == pytest.approx(1e6)
    assert unit == "Pa"


def test_convert_kPa_to_Pa():
    val, unit = convert_to_canonical(1.0, "kPa")
    assert val == pytest.approx(1000.0)
    assert unit == "Pa"


def test_convert_Pa_unchanged():
    val, unit = convert_to_canonical(5000.0, "Pa")
    assert val == pytest.approx(5000.0)
    assert unit == "Pa"


# Time conversions
def test_convert_ms_to_s():
    val, unit = convert_to_canonical(1000.0, "ms")
    assert val == pytest.approx(1.0)
    assert unit == "s"


def test_convert_s_unchanged():
    val, unit = convert_to_canonical(5.0, "s")
    assert val == pytest.approx(5.0)
    assert unit == "s"


def test_convert_us_to_s():
    val, unit = convert_to_canonical(1000000.0, "us")
    assert val == pytest.approx(1.0)
    assert unit == "s"


# Dimensionless
def test_convert_dimensionless():
    val, unit = convert_to_canonical(5.0, "")
    assert val == pytest.approx(5.0)
    assert unit == ""


def test_convert_dimensionless_whitespace():
    val, unit = convert_to_canonical(5.0, "  ")
    assert val == pytest.approx(5.0)
    assert unit == ""


# Error cases
def test_convert_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unknown unit"):
        convert_to_canonical(5.0, "zorgblats")


def test_convert_invalid_unit_raises():
    with pytest.raises(ValueError, match="Unknown unit"):
        convert_to_canonical(10.0, "xyz")


def test_convert_typo_unit_raises():
    with pytest.raises(ValueError, match="Unknown unit"):
        convert_to_canonical(10.0, "meeter")


def test_convert_malformed_unit_no_alphanum(caplog):
    """Units with no alphanumeric chars treated as dimensionless + logs warning."""
    val, unit = convert_to_canonical(10.0, "±")
    assert val == 10.0
    assert unit == ""
    assert "Malformed unit string" in caplog.text


def test_convert_malformed_unit_symbols_only(caplog):
    """Units with only symbols treated as dimensionless + logs warning."""
    val, unit = convert_to_canonical(5.0, "---")
    assert val == 5.0
    assert unit == ""
    assert "Malformed unit string" in caplog.text


# CANONICAL_UNITS constant
def test_canonical_units_defined():
    assert "m" in CANONICAL_UNITS.values()
    assert "kg" in CANONICAL_UNITS.values()
    assert "N" in CANONICAL_UNITS.values()
    assert "Pa" in CANONICAL_UNITS.values()
    assert "s" in CANONICAL_UNITS.values()


def test_canonical_units_has_length():
    assert "length" in CANONICAL_UNITS
    assert CANONICAL_UNITS["length"] == "m"


def test_canonical_units_has_mass():
    assert "mass" in CANONICAL_UNITS
    assert CANONICAL_UNITS["mass"] == "kg"


def test_canonical_units_has_force():
    assert "force" in CANONICAL_UNITS
    assert CANONICAL_UNITS["force"] == "N"


def test_canonical_units_has_pressure():
    assert "pressure" in CANONICAL_UNITS
    assert CANONICAL_UNITS["pressure"] == "Pa"


def test_canonical_units_has_time():
    assert "time" in CANONICAL_UNITS
    assert CANONICAL_UNITS["time"] == "s"


# Dimensionless unit tests (NEW for 07-02)
def test_dimensionless_ratio():
    """ratio unit compiles as dimensionless."""
    val, unit = convert_to_canonical(3.0, "ratio")
    assert val == pytest.approx(3.0)
    assert unit == ""


def test_dimensionless_factor():
    """factor unit compiles as dimensionless."""
    val, unit = convert_to_canonical(1.5, "factor")
    assert val == pytest.approx(1.5)
    assert unit == ""


def test_dimensionless_count():
    """count unit compiles as dimensionless."""
    val, unit = convert_to_canonical(4.0, "count")
    assert val == pytest.approx(4.0)
    assert unit == ""


def test_dimensionless_pcs():
    """pcs (pieces) unit compiles as dimensionless."""
    val, unit = convert_to_canonical(10.0, "pcs")
    assert val == pytest.approx(10.0)
    assert unit == ""


# Compound unit tests (NEW for 07-03)
def test_compound_acceleration():
    """m/s^2 converts correctly."""
    val, unit = convert_to_canonical(9.81, "m/s^2")
    assert val == pytest.approx(9.81)
    assert unit == "m/s^2"


def test_compound_acceleration_cm():
    """cm/s^2 converts to m/s^2."""
    val, unit = convert_to_canonical(981.0, "cm/s^2")
    assert val == pytest.approx(9.81)
    assert unit == "m/s^2"


def test_compound_area():
    """cm^2 converts to m^2."""
    val, unit = convert_to_canonical(100.0, "cm^2")
    assert val == pytest.approx(0.01)
    assert unit == "m^2"


def test_compound_area_m2():
    """m^2 unchanged."""
    val, unit = convert_to_canonical(5.0, "m^2")
    assert val == pytest.approx(5.0)
    assert unit == "m^2"


def test_compound_volume():
    """mm^3 converts to m^3."""
    val, unit = convert_to_canonical(1000.0, "mm^3")
    assert val == pytest.approx(1e-6)
    assert unit == "m^3"


def test_compound_volume_m3():
    """m^3 unchanged."""
    val, unit = convert_to_canonical(2.0, "m^3")
    assert val == pytest.approx(2.0)
    assert unit == "m^3"


def test_compound_torque():
    """N*m (torque/energy) converts to J."""
    val, unit = convert_to_canonical(10.0, "N*m")
    assert val == pytest.approx(10.0)
    assert unit == "J"


def test_compound_energy():
    """J (joules) unchanged."""
    val, unit = convert_to_canonical(100.0, "J")
    assert val == pytest.approx(100.0)
    assert unit == "J"


# Dimensionality-object equality (regression guard for Pint version variance)
def test_dim_object_lookup_matches_across_unit_aliases():
    """Dim-object keys match regardless of how unit string is spelled."""
    from src.verification.semantic.unit_converter import _DIM_CANONICAL, ureg

    # N and kg*m/s^2 have same dimensionality object
    dim_N = ureg.Quantity(1, "N").dimensionality
    dim_kgms2 = ureg.Quantity(1, "kg*m/s^2").dimensionality
    assert dim_N == dim_kgms2
    assert dim_N in _DIM_CANONICAL
