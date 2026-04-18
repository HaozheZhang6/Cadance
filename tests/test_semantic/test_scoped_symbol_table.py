"""Tests for scoped symbol table with triple-key Z3 variable identity."""

import pytest

from src.verification.semantic.scoped_symbol_table import (
    ScopedKey,
    ScopedSymbolTable,
    get_scoped_invariants,
)


class TestScopedKey:
    """Tests for ScopedKey dataclass."""

    def test_scoped_key_to_z3_name(self):
        """to_z3_name returns Entity__Regime__Quantity format."""
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        assert key.to_z3_name() == "bracket__normal__plate_thickness"

    def test_scoped_key_from_z3_name(self):
        """from_z3_name parses back correctly."""
        name = "housing__shock__safety_factor"
        key = ScopedKey.from_z3_name(name)
        assert key.entity_id == "housing"
        assert key.regime_id == "shock"
        assert key.quantity_id == "safety_factor"

    def test_scoped_key_from_z3_name_invalid_too_few(self):
        """from_z3_name raises ValueError on wrong format (too few parts)."""
        with pytest.raises(ValueError, match="expected 3 parts, got 2"):
            ScopedKey.from_z3_name("bracket__thickness")

    def test_scoped_key_from_z3_name_invalid_too_many(self):
        """from_z3_name raises ValueError on wrong format (too many parts)."""
        with pytest.raises(ValueError, match="expected 3 parts, got 4"):
            ScopedKey.from_z3_name("bracket__normal__plate__thickness")

    def test_scoped_key_hashable(self):
        """ScopedKey is hashable (usable as dict key)."""
        key1 = ScopedKey("a", "b", "c")
        key2 = ScopedKey("a", "b", "c")
        d = {key1: "value"}
        assert d[key2] == "value"

    def test_scoped_key_equality(self):
        """Same fields => equal keys."""
        key1 = ScopedKey("x", "y", "z")
        key2 = ScopedKey("x", "y", "z")
        assert key1 == key2


class TestScopedSymbolTable:
    """Tests for ScopedSymbolTable class."""

    def test_scoped_symbol_table_resolve_creates_z3_var(self):
        """resolve() creates Z3 variable on first call, returns same on second."""
        table = ScopedSymbolTable()
        key1, var1 = table.resolve("bracket", "normal", "plate_thickness")
        key2, var2 = table.resolve("bracket", "normal", "plate_thickness")
        # Same key
        assert key1 == key2
        # Same Z3 variable (identity)
        assert var1 is var2

    def test_different_entities_different_vars(self):
        """Different entities produce distinct Z3 variables."""
        table = ScopedSymbolTable()
        _, var_bracket = table.resolve("bracket", "normal", "plate_thickness")
        _, var_housing = table.resolve("housing", "normal", "plate_thickness")
        # Different Z3 variables
        assert var_bracket is not var_housing
        # Check Z3 names are different
        assert str(var_bracket) == "bracket__normal__plate_thickness"
        assert str(var_housing) == "housing__normal__plate_thickness"

    def test_different_regimes_different_vars(self):
        """Different regimes produce distinct Z3 variables."""
        table = ScopedSymbolTable()
        _, var_normal = table.resolve("bracket", "normal", "safety_factor")
        _, var_shock = table.resolve("bracket", "shock", "safety_factor")
        # Different Z3 variables
        assert var_normal is not var_shock
        # Check Z3 names are different
        assert str(var_normal) == "bracket__normal__safety_factor"
        assert str(var_shock) == "bracket__shock__safety_factor"

    def test_resolve_alias_known(self):
        """resolve_alias returns quantity_id for known alias."""
        table = ScopedSymbolTable()
        # "wall_thickness" is alias for "plate_thickness"
        result = table.resolve_alias("wall_thickness")
        assert result == "plate_thickness"

    def test_resolve_alias_unknown(self):
        """resolve_alias returns None for unknown alias."""
        table = ScopedSymbolTable()
        result = table.resolve_alias("unknown_param_xyz")
        assert result is None

    def test_resolve_alias_normalized(self):
        """resolve_alias normalizes input (lowercase, spaces to underscore)."""
        table = ScopedSymbolTable()
        # "Wall Thickness" -> "wall_thickness" -> "plate_thickness"
        result = table.resolve_alias("Wall Thickness")
        assert result == "plate_thickness"


class TestScopedInvariants:
    """Tests for get_scoped_invariants function."""

    def test_get_domain_class(self):
        """get_domain_class returns domain_class from ontology."""
        table = ScopedSymbolTable()
        assert table.get_domain_class("plate_thickness") == "LENGTH_POS"
        assert table.get_domain_class("safety_factor") == "FACTOR_GE1"
        assert table.get_domain_class("deflection") == "LENGTH_NONNEG"

    def test_get_domain_class_unknown(self):
        """get_domain_class returns empty string for unknown quantity."""
        table = ScopedSymbolTable()
        assert table.get_domain_class("unknown_quantity_xyz") == ""

    def test_get_scoped_invariants_pos(self):
        """get_scoped_invariants generates > 0 for LENGTH_POS."""
        table = ScopedSymbolTable()
        table.resolve("part", "normal", "plate_thickness")
        invariants = get_scoped_invariants(table)
        assert len(invariants) == 1
        name, _ = invariants[0]
        assert name == "INV_POS_part__normal__plate_thickness"

    def test_get_scoped_invariants_ge1(self):
        """get_scoped_invariants generates >= 1 for FACTOR_GE1."""
        table = ScopedSymbolTable()
        table.resolve("system", "normal", "safety_factor")
        invariants = get_scoped_invariants(table)
        assert len(invariants) == 1
        name, _ = invariants[0]
        assert name == "INV_GE1_system__normal__safety_factor"

    def test_invariant_name_includes_scope(self):
        """Invariant name includes entity, regime, quantity."""
        table = ScopedSymbolTable()
        table.resolve("bracket", "shock", "plate_thickness")
        invariants = get_scoped_invariants(table)
        name, _ = invariants[0]
        assert "bracket" in name
        assert "shock" in name
        assert "plate_thickness" in name

    def test_get_scoped_invariants_multiple(self):
        """get_scoped_invariants handles multiple variables."""
        table = ScopedSymbolTable()
        table.resolve("a", "normal", "plate_thickness")  # LENGTH_POS
        table.resolve("a", "normal", "safety_factor")  # FACTOR_GE1
        table.resolve("b", "normal", "deflection")  # LENGTH_NONNEG
        invariants = get_scoped_invariants(table)
        assert len(invariants) == 3
        names = {inv[0] for inv in invariants}
        assert "INV_POS_a__normal__plate_thickness" in names
        assert "INV_GE1_a__normal__safety_factor" in names
        assert "INV_NONNEG_b__normal__deflection" in names
