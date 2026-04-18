"""Tests for contract_compiler — tolerance regex and clause compilation."""

from src.hypergraph.models import Contract, NodeType
from src.verification.semantic.constraint_extractor import Constraint
from src.verification.semantic.contract_compiler import (
    _compile_clause,
    compile_contract_clauses_scoped,
    merge_assumption_ranges,
    merge_guarantee_ranges,
)
from src.verification.semantic.scoped_symbol_table import ScopedKey, ScopedSymbolTable
from src.verification.semantic.symbol_table import SymbolTable


class TestUnitlessToleranceClauses:
    """Unitless tolerance clauses must parse value correctly."""

    def test_unitless_percentage_tolerance(self):
        """'bend_angle within 90 +/-1%' -> [89.1, 90.9]."""
        st = SymbolTable()
        constraint, skip = _compile_clause("bend_angle within 90 +/-1%", st)
        assert skip is None
        assert constraint is not None
        assert abs(constraint.min_value - 89.1) < 0.01
        assert abs(constraint.max_value - 90.9) < 0.01

    def test_unitless_absolute_tolerance(self):
        """'bend_angle within 90 +/-5' -> [85, 95]."""
        st = SymbolTable()
        constraint, skip = _compile_clause("bend_angle within 90 +/-5", st)
        assert skip is None
        assert constraint is not None
        assert abs(constraint.min_value - 85.0) < 0.01
        assert abs(constraint.max_value - 95.0) < 0.01

    def test_with_unit_still_works(self):
        """'torque within 10 N*m +/-20%' still parses correctly."""
        st = SymbolTable()
        constraint, skip = _compile_clause("torque within 10 N*m +/-20%", st)
        assert skip is None
        assert constraint is not None
        assert constraint.min_value < constraint.max_value

    def test_unitless_canonical_unit_empty(self):
        """Unitless clause -> canonical_unit == ''."""
        st = SymbolTable()
        constraint, skip = _compile_clause("bend_angle within 90 +/-1%", st)
        assert constraint is not None
        assert constraint.canonical_unit == ""


class TestGuaranteeEqualityDedup:
    """Duplicate guarantee equalities on same quantity → second downgraded."""

    def test_duplicate_guarantee_equality_downgraded(self):
        """2 guarantees 'allowable_stress is X' with different X → second <= X."""
        contract = Contract(
            id="c1",
            node_type=NodeType.CONTRACT,
            description="test",
            assumptions=[],
            guarantees=[
                "allowable_stress is 125000000 Pa",
                "allowable_stress is 166700000 Pa",
            ],
        )
        contract.metadata = {
            "terms": {
                "assumptions": [],
                "guarantees": [
                    {"text": "allowable_stress is 125000000 Pa"},
                    {"text": "allowable_stress is 166700000 Pa"},
                ],
            }
        }
        st = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(contract, st)
        g_constraints = [c for c in result.constraints if "_G_" in c.name]
        assert len(g_constraints) == 2
        # First stays equality
        assert g_constraints[0].is_equality is True
        # Second downgraded to upper bound
        assert g_constraints[1].is_equality is False
        assert g_constraints[1].max_value is not None

    def test_single_guarantee_equality_unchanged(self):
        """1 guarantee 'is X' → stays equality."""
        contract = Contract(
            id="c2",
            node_type=NodeType.CONTRACT,
            description="test",
            assumptions=[],
            guarantees=["allowable_stress is 125000000 Pa"],
        )
        contract.metadata = {
            "terms": {
                "assumptions": [],
                "guarantees": [
                    {"text": "allowable_stress is 125000000 Pa"},
                ],
            }
        }
        st = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(contract, st)
        g_constraints = [c for c in result.constraints if "_G_" in c.name]
        assert len(g_constraints) == 1
        assert g_constraints[0].is_equality is True


class TestIsNoMoreThanPattern:
    """'deflection is no more than 0.001 m' → upper bound."""

    def test_is_no_more_than_parses_as_upper_bound(self):
        """'is no more than' variant parses as upper bound."""
        st = SymbolTable()
        constraint, skip = _compile_clause("deflection is no more than 0.001 m", st)
        assert skip is None
        assert constraint is not None
        assert constraint.is_equality is False
        assert constraint.max_value is not None
        assert constraint.min_value is None

    def test_is_at_least_parses_as_lower_bound(self):
        """'is at least' variant parses as lower bound."""
        st = SymbolTable()
        constraint, skip = _compile_clause("edge_distance is at least 0.015 m", st)
        assert skip is None
        assert constraint is not None
        assert constraint.is_equality is False
        assert constraint.min_value is not None
        assert constraint.max_value is None


class TestExactDuplicateAssumptionDedup:
    """Exact duplicate assumptions deduped without _merged suffix."""

    def test_exact_duplicate_assumptions_deduped(self):
        """2 identical constraints → 1 output, original name."""
        key = ScopedKey("system", "normal", "static_force")
        c1 = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            min_value=46.6,
            max_value=51.4,
            canonical_unit="N",
            is_equality=False,
            canonical_name="static_force",
            scoped_key=key,
        )
        c2 = Constraint(
            name="CONTRACT_c1_A_3",
            min_name="CONTRACT_c1_A_3_min",
            max_name="CONTRACT_c1_A_3_max",
            min_value=46.6,
            max_value=51.4,
            canonical_unit="N",
            is_equality=False,
            canonical_name="static_force",
            scoped_key=key,
        )
        result = merge_assumption_ranges([c1, c2])
        assert len(result) == 1
        # Original name, no _merged suffix
        assert "_merged" not in result[0].name

    def test_overlapping_assumptions_still_merge(self):
        """Different bounds → merged to envelope."""
        key = ScopedKey("system", "normal", "static_force")
        c1 = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            min_value=40.0,
            max_value=50.0,
            canonical_unit="N",
            is_equality=False,
            canonical_name="static_force",
            scoped_key=key,
        )
        c2 = Constraint(
            name="CONTRACT_c1_A_3",
            min_name="CONTRACT_c1_A_3_min",
            max_name="CONTRACT_c1_A_3_max",
            min_value=45.0,
            max_value=55.0,
            canonical_unit="N",
            is_equality=False,
            canonical_name="static_force",
            scoped_key=key,
        )
        result = merge_assumption_ranges([c1, c2])
        assert len(result) == 1
        assert result[0].min_value == 40.0
        assert result[0].max_value == 55.0
        assert "_merged" in result[0].name


class TestMergeGuaranteeRanges:
    """merge_guarantee_ranges merges same-canonical-name guarantee ranges."""

    def test_merge_guarantee_ranges_non_overlapping(self):
        """Two non-overlapping guarantee ranges → merged to widest envelope."""
        c1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            min_value=112.5e6,
            max_value=137.5e6,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="allowable_stress",
        )
        c2 = Constraint(
            name="CONTRACT_c1_G_2",
            min_name="CONTRACT_c1_G_2_min",
            max_name="CONTRACT_c1_G_2_max",
            min_value=150.0e6,
            max_value=183.3e6,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="allowable_stress",
        )
        result = merge_guarantee_ranges([c1, c2])
        merged = [c for c in result if "allowable_stress" == c.canonical_name]
        assert len(merged) == 1
        assert merged[0].min_value == 112.5e6
        assert merged[0].max_value == 183.3e6
        assert "_merged" in merged[0].name

    def test_merge_guarantee_ranges_exact_dedup(self):
        """Identical guarantee ranges → kept as one, no _merged."""
        c1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            min_value=100.0,
            max_value=200.0,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="allowable_stress",
        )
        c2 = Constraint(
            name="CONTRACT_c1_G_2",
            min_name="CONTRACT_c1_G_2_min",
            max_name="CONTRACT_c1_G_2_max",
            min_value=100.0,
            max_value=200.0,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="allowable_stress",
        )
        result = merge_guarantee_ranges([c1, c2])
        merged = [c for c in result if "allowable_stress" == c.canonical_name]
        assert len(merged) == 1
        assert "_merged" not in merged[0].name

    def test_merge_guarantee_ranges_single_passthrough(self):
        """Single guarantee → unchanged."""
        c1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            min_value=100.0,
            max_value=200.0,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="allowable_stress",
        )
        result = merge_guarantee_ranges([c1])
        assert len(result) == 1
        assert result[0].name == "CONTRACT_c1_G_1"

    def test_merge_guarantee_equality_plus_range(self):
        """Equality + range merge: envelope preserves open upper bound."""
        c1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            exact_value=150e6,
            canonical_unit="Pa",
            is_equality=True,
            canonical_name="allowable_stress",
        )
        c2 = Constraint(
            name="CONTRACT_c1_G_2",
            min_name="CONTRACT_c1_G_2_min",
            max_name="CONTRACT_c1_G_2_max",
            min_value=200e6,
            max_value=None,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="allowable_stress",
        )
        result = merge_guarantee_ranges([c1, c2])
        merged = [c for c in result if c.canonical_name == "allowable_stress"]
        assert len(merged) == 1
        assert merged[0].min_value == 150e6
        # c2 has no upper bound → merged is unbounded above
        assert merged[0].max_value is None

    def test_merge_guarantee_two_different_equalities(self):
        """Two different equalities merge into range."""
        c1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            exact_value=10.0,
            canonical_unit="mm",
            is_equality=True,
            canonical_name="thickness",
        )
        c2 = Constraint(
            name="CONTRACT_c1_G_2",
            min_name="CONTRACT_c1_G_2_min",
            max_name="CONTRACT_c1_G_2_max",
            exact_value=50.0,
            canonical_unit="mm",
            is_equality=True,
            canonical_name="thickness",
        )
        result = merge_guarantee_ranges([c1, c2])
        merged = [c for c in result if c.canonical_name == "thickness"]
        assert len(merged) == 1
        assert merged[0].min_value == 10.0
        assert merged[0].max_value == 50.0
        assert merged[0].is_equality is False

    def test_merge_guarantee_lower_bound_only(self):
        """Lower-bound-only + range: merged preserves open lower bound."""
        c1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            min_value=None,
            max_value=100.0,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="stress",
        )
        c2 = Constraint(
            name="CONTRACT_c1_G_2",
            min_name="CONTRACT_c1_G_2_min",
            max_name="CONTRACT_c1_G_2_max",
            min_value=50.0,
            max_value=200.0,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="stress",
        )
        result = merge_guarantee_ranges([c1, c2])
        merged = [c for c in result if c.canonical_name == "stress"]
        assert len(merged) == 1
        # c1 has no lower bound → merged is unbounded below
        assert merged[0].min_value is None
        assert merged[0].max_value == 200.0

    def test_merge_does_not_affect_assumptions(self):
        """Assumption constraints pass through untouched."""
        c_a = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            min_value=10.0,
            max_value=20.0,
            canonical_unit="N",
            is_equality=False,
            canonical_name="force",
        )
        c_g = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            min_value=100.0,
            max_value=200.0,
            canonical_unit="Pa",
            is_equality=False,
            canonical_name="stress",
        )
        result = merge_guarantee_ranges([c_a, c_g])
        assert len(result) == 2
