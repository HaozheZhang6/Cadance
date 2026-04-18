"""Tests for identity gate validation."""

from src.verification.semantic.constraint_extractor import Constraint
from src.verification.semantic.identity_gate import (
    IdentityError,
    format_identity_errors,
    is_unit_compatible,
    validate_identity,
)
from src.verification.semantic.scoped_symbol_table import ScopedKey, ScopedSymbolTable


class TestIsUnitCompatible:
    """Test unit compatibility checking."""

    def test_same_unit(self):
        """Same unit is compatible."""
        assert is_unit_compatible("m", "m") is True

    def test_same_dimensionality(self):
        """Different units with same dimensionality are compatible."""
        assert is_unit_compatible("mm", "m") is True
        assert is_unit_compatible("kg", "g") is True

    def test_different_dimensionality(self):
        """Different dimensionality units are incompatible."""
        assert is_unit_compatible("kg", "m") is False
        assert is_unit_compatible("N", "m") is False

    def test_empty_unit_wildcard(self):
        """Empty unit acts as wildcard (compatible with anything)."""
        assert is_unit_compatible("", "m") is True
        assert is_unit_compatible("m", "") is True

    def test_unknown_unit_incompatible(self):
        """Unknown unit is incompatible."""
        assert is_unit_compatible("xyz123", "m") is False


class TestValidateIdentity:
    """Test identity validation for constraints."""

    def test_valid_structured_constraint(self):
        """Valid structured constraint passes."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            max_value=10.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            canonical_unit="m",
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is True
        assert errors == []

    def test_missing_scoped_key(self):
        """Missing scoped_key fails validation."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=None,
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is False
        assert len(errors) == 1
        assert errors[0].field == "scoped_key"

    def test_empty_entity_id(self):
        """Empty entity_id fails validation."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=ScopedKey("", "normal", "plate_thickness"),
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is False
        assert any(e.field == "entity_id" for e in errors)

    def test_empty_regime_id(self):
        """Empty regime_id fails validation."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=ScopedKey("bracket", "", "plate_thickness"),
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is False
        assert any(e.field == "regime_id" for e in errors)

    def test_empty_quantity_id(self):
        """Empty quantity_id fails validation."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=ScopedKey("bracket", "normal", ""),
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is False
        assert any(e.field == "quantity_id" for e in errors)

    def test_unit_incompatibility(self):
        """Unit incompatible with ontology canonical unit fails."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            canonical_unit="kg",  # Wrong! plate_thickness should be m
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is False
        assert any(e.field == "unit" for e in errors)

    def test_nl_only_skipped(self):
        """nl_only constraints are skipped (not validated)."""
        scoped_table = ScopedSymbolTable()
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
            min_value=1.0,
            term_class="nl_only",
            source_spec_id="SPEC-001",
            scoped_key=None,  # Would fail if validated
        )
        is_valid, errors = validate_identity([c], scoped_table)
        assert is_valid is True  # nl_only skipped

    def test_multiple_errors_collected(self):
        """Multiple errors from multiple constraints are collected."""
        scoped_table = ScopedSymbolTable()
        c1 = Constraint(
            name="test1",
            min_name="m1",
            max_name="x1",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-001",
            scoped_key=None,
        )
        c2 = Constraint(
            name="test2",
            min_name="m2",
            max_name="x2",
            min_value=1.0,
            term_class="structured",
            source_spec_id="SPEC-002",
            scoped_key=ScopedKey("", "", ""),
        )
        is_valid, errors = validate_identity([c1, c2], scoped_table)
        assert is_valid is False
        assert len(errors) >= 2  # At least 2 errors


class TestFormatIdentityErrors:
    """Test error formatting."""

    def test_format_single_error(self):
        """Single error formats correctly."""
        errors = [
            IdentityError("SPEC-001", "thickness", "entity_id", "entity_id is empty")
        ]
        output = format_identity_errors(errors)
        assert "Identity validation failed (1 errors)" in output
        assert "SPEC-001.thickness: entity_id is empty" in output

    def test_format_multiple_errors(self):
        """Multiple errors format correctly."""
        errors = [
            IdentityError("SPEC-001", "thickness", "entity_id", "entity_id is empty"),
            IdentityError("SPEC-002", "mass", "unit", "Unit 'm' incompatible"),
        ]
        output = format_identity_errors(errors)
        assert "(2 errors)" in output
        assert "SPEC-001.thickness" in output
        assert "SPEC-002.mass" in output
