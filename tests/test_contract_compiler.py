"""Tests for contract clause compilation."""

import pytest

from src.hypergraph.models import Contract
from src.verification.semantic.contract_compiler import (
    ContractSkipReason,
    _compile_clause,
    compile_contract_clauses,
)
from src.verification.semantic.symbol_table import SymbolTable


class TestContractCompilerSkipReasons:
    """Test skip reason classification."""

    def test_derived_equation_skipped(self):
        """Derived equations (A*B) are skipped with EQ_DERIVED."""
        contract = Contract(
            id="contract_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "static_load is 49.1 N (payload_mass*gravity)",
                            "confidence": "Likely",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.skipped_count == 1
        assert ContractSkipReason.SKIPPED_EQ_DERIVED.value in result.skip_breakdown

    def test_qualitative_requirement_skipped(self):
        """Qualitative/analysis statements skipped with NL_REQUIREMENT."""
        contract = Contract(
            id="contract_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [],
                    "guarantees": [
                        {
                            "text": "bracket will not yield or fracture under design loads",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.skipped_count == 1
        assert ContractSkipReason.SKIPPED_NL_REQUIREMENT.value in result.skip_breakdown

    def test_spec_reference_skipped(self):
        """References to specs without values skipped with UNDER_SPEC_REFERENCE."""
        contract = Contract(
            id="contract_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "tooling consistent with specified clearance diameter",
                            "confidence": "Likely",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.skipped_count == 1
        assert (
            ContractSkipReason.SKIPPED_UNDER_SPEC_REFERENCE.value
            in result.skip_breakdown
        )


class TestContractCompilerCompilation:
    """Test successful clause compilation."""

    def test_compile_torque_with_tolerance(self):
        """Torque clause with +/-20% compiles to bounds."""
        contract = Contract(
            id="contract_bbf23697",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "installation torque within 10 N*m +/-20%",
                            "confidence": "Likely",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.name == "CONTRACT_contract_bbf23697_A_1"
        assert c.min_value == pytest.approx(8.0)
        assert c.max_value == pytest.approx(12.0)
        assert c.canonical_name == "installation_torque"

    def test_compile_edge_radius_with_tolerance(self):
        """Edge radius with +/-0.5mm compiles to SI bounds."""
        contract = Contract(
            id="contract_bbf23697",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [],
                    "guarantees": [
                        {
                            "text": "minimum edge radius 1 mm (+/-0.5 mm)",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.name == "CONTRACT_contract_bbf23697_G_1"
        # 1mm +/- 0.5mm = [0.5mm, 1.5mm] = [0.0005m, 0.0015m]
        assert c.min_value == pytest.approx(0.0005)
        assert c.max_value == pytest.approx(0.0015)

    def test_compile_payload_mass_equality(self):
        """Payload mass equality compiles."""
        contract = Contract(
            id="contract_1e60d8b2",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "Payload mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.name == "CONTRACT_contract_1e60d8b2_A_1"
        assert c.exact_value == pytest.approx(5.0)
        assert c.is_equality is True
        assert c.canonical_name == "payload_mass"

    def test_compile_deflection_upper_bound(self):
        """Upper bound constraint compiles."""
        contract = Contract(
            id="contract_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "Deflection no more than 1 mm",
                            "confidence": "Confident",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.max_value == pytest.approx(0.001)  # 1mm in meters
        assert c.min_value is None  # unbounded below


class TestContractCompilerNaming:
    """Test CONTRACT_* naming convention."""

    def test_assumption_naming(self):
        """Assumptions use _A_ in name."""
        contract = Contract(
            id="contract_abc123",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        assert result.constraints[0].name == "CONTRACT_contract_abc123_A_1"

    def test_guarantee_naming(self):
        """Guarantees use _G_ in name."""
        contract = Contract(
            id="contract_xyz789",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [],
                    "guarantees": [
                        {
                            "text": "deflection no more than 1 mm",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        assert result.constraints[0].name == "CONTRACT_contract_xyz789_G_1"

    def test_multiple_clauses_numbered(self):
        """Multiple clauses get sequential numbers."""
        contract = Contract(
            id="contract_multi",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "shock_factor is 5.0", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 2
        names = [c.name for c in result.constraints]
        assert "CONTRACT_contract_multi_A_1" in names
        assert "CONTRACT_contract_multi_A_2" in names


class TestContractCompilerFallback:
    """Test fallback to node.assumptions/guarantees when metadata.terms missing."""

    def test_fallback_to_assumptions_list(self):
        """Falls back to node.assumptions if metadata.terms missing."""
        contract = Contract(
            id="contract_fallback",
            description="Test",
            assumptions=["payload_mass is 5 kg"],
            guarantees=["deflection no more than 1 mm"],
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 2


class TestContractCompilerScoped:
    """Test scoped contract compilation with identity fields."""

    def test_assumption_equality_emits_range(self):
        """Assumption 'payload_mass is 5 kg' emits range [4.5, 5.5] not equality."""
        from src.verification.semantic.contract_compiler import (
            compile_contract_clauses_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_range_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(
            contract, scoped_table, entity_id="bracket", regime_id="normal"
        )

        assert result.compiled_count == 1
        c = result.constraints[0]
        # Assumption emits range (4.5, 5.5), not equality
        assert c.is_equality is False
        assert c.min_value == pytest.approx(4.5)  # 5 - 10%
        assert c.max_value == pytest.approx(5.5)  # 5 + 10%
        assert c.exact_value is None

    def test_derived_quantity_multiplication(self):
        """Derived quantity A*B produces constraint with factors."""
        from src.verification.semantic.contract_compiler import (
            compile_contract_clauses_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_derived_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "static_force = payload_mass * gravity",
                            "confidence": "Confident",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(
            contract, scoped_table, entity_id="bracket", regime_id="normal"
        )

        # Should NOT be skipped - should compile to derived constraint
        assert result.compiled_count == 1
        c = result.constraints[0]
        # Derived constraint has factors
        assert c.derived is True
        assert "payload_mass" in c.factors
        assert "gravity" in c.factors
        assert c.result_quantity == "static_force"

    def test_scoped_identity_fields_populated(self):
        """Scoped compilation sets scoped_key, source_spec_id, term_class."""
        from src.verification.semantic.contract_compiler import (
            compile_contract_clauses_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
            ScopedSymbolTable,
        )

        contract = Contract(
            id="contract_identity_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(
            contract, scoped_table, entity_id="bracket", regime_id="shock"
        )

        assert result.compiled_count == 1
        c = result.constraints[0]
        # Scoped identity fields
        assert c.scoped_key == ScopedKey("bracket", "shock", "payload_mass")
        assert c.source_spec_id == "contract_identity_test"
        assert c.term_class == "structured"

    def test_guarantee_keeps_exact_bound(self):
        """Guarantees keep exact bound (no range emission)."""
        from src.verification.semantic.contract_compiler import (
            compile_contract_clauses_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_guarantee_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [],
                    "guarantees": [
                        {
                            "text": "deflection no more than 1 mm",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(
            contract, scoped_table, entity_id="bracket", regime_id="normal"
        )

        assert result.compiled_count == 1
        c = result.constraints[0]
        # Guarantee upper bound is exact (0.001m), no range widening
        assert c.max_value == pytest.approx(0.001)
        assert c.min_value is None  # Unbounded below
        assert c.is_equality is False


class TestPerClauseCoverage:
    """Test per-clause coverage tracking."""

    def test_per_clause_coverage_populated(self):
        """per_clause_coverage has entry for each clause."""
        contract = Contract(
            id="contract_coverage_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {
                            "text": "static_load is payload_mass*gravity",
                            "confidence": "Likely",
                        },
                    ],
                    "guarantees": [
                        {
                            "text": "deflection no more than 1 mm",
                            "confidence": "Confident",
                        },
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        # 3 clauses total
        assert len(result.per_clause_coverage) == 3
        # Each entry has required fields
        for entry in result.per_clause_coverage:
            assert "clause_idx" in entry
            assert "clause_type" in entry
            assert "clause_text" in entry
            assert "status" in entry
            assert "reason" in entry

    def test_per_clause_coverage_status_values(self):
        """Status is 'compiled' or 'skipped'."""
        contract = Contract(
            id="contract_status_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "bracket will not yield", "confidence": "Likely"},
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        statuses = {e["status"] for e in result.per_clause_coverage}
        assert statuses == {"compiled", "skipped"}

    def test_clause_map_populated(self):
        """clause_map maps constraint name to clause text."""
        contract = Contract(
            id="contract_map_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        # clause_map has entry for compiled constraint
        assert "CONTRACT_contract_map_test_A_1" in result.clause_map
        assert (
            result.clause_map["CONTRACT_contract_map_test_A_1"]
            == "payload_mass is 5 kg"
        )

    def test_clause_map_only_compiled(self):
        """clause_map only contains compiled constraints."""
        contract = Contract(
            id="contract_map_only",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "bracket will not yield", "confidence": "Likely"},
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        # Only 1 entry (the compiled one)
        assert len(result.clause_map) == 1
        assert "CONTRACT_contract_map_only_A_1" in result.clause_map

    def test_coverage_report_format(self):
        """coverage_report includes summary and reason breakdown."""
        contract = Contract(
            id="contract_report_test",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {
                            "text": "static_load is payload_mass*gravity",
                            "confidence": "Likely",
                        },
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        report = result.coverage_report
        assert "Compiled: 1" in report
        assert "Skipped: 1" in report
        assert "SKIPPED_EQ_DERIVED" in report

    def test_scoped_compilation_populates_coverage(self):
        """compile_contract_clauses_scoped also populates per_clause_coverage."""
        from src.verification.semantic.contract_compiler import (
            compile_contract_clauses_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_scoped_coverage",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "bracket will not yield", "confidence": "Likely"},
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(
            contract, scoped_table, entity_id="bracket", regime_id="normal"
        )

        # per_clause_coverage populated
        assert len(result.per_clause_coverage) == 2
        # clause_map has compiled constraint
        assert len(result.clause_map) == 1


class TestContractCompilationResult:
    """Test result structure and coverage calculation."""

    def test_coverage_calculation(self):
        """Coverage is compiled / total."""
        contract = Contract(
            id="contract_coverage",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {
                            "text": "static_load is payload_mass*gravity",
                            "confidence": "Likely",
                        },
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        # 1 compiled, 1 skipped -> 50% coverage
        assert result.compiled_count == 1
        assert result.skipped_count == 1
        assert result.coverage == pytest.approx(0.5)

    def test_empty_contract_coverage(self):
        """Empty contract has 100% coverage."""
        contract = Contract(
            id="contract_empty",
            description="Test",
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 0
        assert result.skipped_count == 0
        assert result.coverage == 1.0


class TestBug1LowerBoundParamFirst:
    """Bug 1: _LOWER_BOUND_PATTERN is keyword-first, clauses are param-first."""

    def test_param_first_at_least(self):
        """'edge_distance at least 0.015 m' should compile, not skip."""
        contract = Contract(
            id="contract_lb1",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "edge_distance at least 0.015 m",
                            "confidence": "Confident",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        assert result.skipped_count == 0
        c = result.constraints[0]
        assert c.min_value == pytest.approx(0.015)
        assert c.max_value is None

    def test_param_first_minimum(self):
        """'coating_thickness minimum 0.00006 m' should compile."""
        contract = Contract(
            id="contract_lb2",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "coating_thickness minimum 0.00006 m",
                            "confidence": "Confident",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(0.00006)

    def test_param_first_gte(self):
        """'salt_spray_duration >= 172800 s' should compile."""
        contract = Contract(
            id="contract_lb3",
            description="Test",
            metadata={
                "terms": {
                    "guarantees": [
                        {
                            "text": "salt_spray_duration >= 172800 s",
                            "confidence": "Confident",
                        }
                    ],
                    "assumptions": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(172800.0)

    def test_keyword_first_still_works(self):
        """'at least 5 mm thickness' keyword-first should still compile."""
        contract = Contract(
            id="contract_lb4",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "minimum thickness 5 mm", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1

    def test_param_first_scoped(self):
        """Param-first lower bound works in scoped compilation too."""
        from src.verification.semantic.contract_compiler import (
            compile_contract_clauses_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_lb_scoped",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "edge_distance at least 0.015 m",
                            "confidence": "Confident",
                        }
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = compile_contract_clauses_scoped(
            contract, scoped_table, entity_id="bracket", regime_id="normal"
        )

        assert result.compiled_count == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(0.015)


class TestBug2NLWordBoundaries:
    """Bug 2: NL skip patterns match inside param names."""

    def test_yield_strength_not_skipped(self):
        """'yield_strength at least 250000000 Pa' should compile, not skip on 'yield'."""
        contract = Contract(
            id="contract_wb1",
            description="Test",
            metadata={
                "terms": {
                    "guarantees": [
                        {
                            "text": "yield_strength at least 250000000 Pa",
                            "confidence": "Confident",
                        }
                    ],
                    "assumptions": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        assert result.skipped_count == 0
        c = result.constraints[0]
        assert c.min_value == pytest.approx(250000000.0)

    def test_safety_factor_not_skipped(self):
        """'safety_factor at least 1.5' should compile, not skip on 'safety'."""
        contract = Contract(
            id="contract_wb2",
            description="Test",
            metadata={
                "terms": {
                    "guarantees": [
                        {
                            "text": "safety_factor at least 1.5",
                            "confidence": "Confident",
                        }
                    ],
                    "assumptions": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1
        assert result.skipped_count == 0

    def test_static_safety_factor_not_skipped(self):
        """'static_safety_factor at least 3.0' should compile."""
        contract = Contract(
            id="contract_wb3",
            description="Test",
            metadata={
                "terms": {
                    "guarantees": [
                        {
                            "text": "static_safety_factor at least 3.0",
                            "confidence": "Confident",
                        }
                    ],
                    "assumptions": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.compiled_count == 1

    def test_standalone_yield_still_skipped(self):
        """'bracket will not yield under load' should still be skipped."""
        contract = Contract(
            id="contract_wb4",
            description="Test",
            metadata={
                "terms": {
                    "guarantees": [
                        {
                            "text": "bracket will not yield under load",
                            "confidence": "Confident",
                        }
                    ],
                    "assumptions": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.skipped_count == 1
        assert ContractSkipReason.SKIPPED_NL_REQUIREMENT.value in result.skip_breakdown

    def test_standalone_safety_still_skipped(self):
        """'ensure safety margins' should still be skipped."""
        contract = Contract(
            id="contract_wb5",
            description="Test",
            metadata={
                "terms": {
                    "guarantees": [
                        {
                            "text": "ensure safety margins are adequate",
                            "confidence": "Confident",
                        }
                    ],
                    "assumptions": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = compile_contract_clauses(contract, symbol_table)

        assert result.skipped_count == 1


class TestBug3AssumptionRangeMerge:
    """Bug 3: Same-param conflicts across contract assumptions."""

    def test_merge_overlapping_assumption_ranges(self):
        """Two assumptions on same scoped_key should merge to widest envelope."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.contract_compiler import (
            merge_assumption_ranges,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        key = ScopedKey("system", "normal", "test_load")
        c1 = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            min_value=44.14,
            max_value=53.95,
            canonical_unit="N",
            scoped_key=key,
            term_class="structured",
            source_spec_id="c1",
        )
        c2 = Constraint(
            name="CONTRACT_c2_A_1",
            min_name="CONTRACT_c2_A_1_min",
            max_name="CONTRACT_c2_A_1_max",
            min_value=66.22,
            max_value=80.93,
            canonical_unit="N",
            scoped_key=key,
            term_class="structured",
            source_spec_id="c2",
        )

        merged = merge_assumption_ranges([c1, c2])

        # Should merge to one constraint with min(mins), max(maxes)
        scoped_constraints = [c for c in merged if c.scoped_key == key]
        assert len(scoped_constraints) == 1
        assert scoped_constraints[0].min_value == pytest.approx(44.14)
        assert scoped_constraints[0].max_value == pytest.approx(80.93)

    def test_merge_leaves_guarantees_untouched(self):
        """Guarantee constraints should not be merged."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.contract_compiler import (
            merge_assumption_ranges,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        key = ScopedKey("system", "normal", "deflection")
        g1 = Constraint(
            name="CONTRACT_c1_G_1",
            min_name="CONTRACT_c1_G_1_min",
            max_name="CONTRACT_c1_G_1_max",
            max_value=0.001,
            canonical_unit="m",
            scoped_key=key,
            term_class="structured",
            source_spec_id="c1",
        )
        g2 = Constraint(
            name="CONTRACT_c2_G_1",
            min_name="CONTRACT_c2_G_1_min",
            max_name="CONTRACT_c2_G_1_max",
            max_value=0.002,
            canonical_unit="m",
            scoped_key=key,
            term_class="structured",
            source_spec_id="c2",
        )

        merged = merge_assumption_ranges([g1, g2])

        # Guarantees should pass through unchanged
        assert len(merged) == 2

    def test_merge_leaves_spec_constraints_untouched(self):
        """Spec constraints (non-CONTRACT_ prefix) should pass through."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.contract_compiler import (
            merge_assumption_ranges,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        key = ScopedKey("system", "normal", "thickness")
        spec = Constraint(
            name="SPEC-001_thickness",
            min_name="SPEC-001_thickness_min",
            max_name="SPEC-001_thickness_max",
            min_value=0.004,
            max_value=0.006,
            canonical_unit="m",
            scoped_key=key,
            term_class="structured",
            source_spec_id="SPEC-001",
        )

        merged = merge_assumption_ranges([spec])
        assert len(merged) == 1
        assert merged[0].name == "SPEC-001_thickness"

    def test_merge_no_conflict_passes_through(self):
        """Single assumption on a key should pass through unchanged."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.contract_compiler import (
            merge_assumption_ranges,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        key = ScopedKey("system", "normal", "test_load")
        c1 = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            min_value=44.14,
            max_value=53.95,
            canonical_unit="N",
            scoped_key=key,
            term_class="structured",
            source_spec_id="c1",
        )

        merged = merge_assumption_ranges([c1])
        assert len(merged) == 1
        assert merged[0].min_value == pytest.approx(44.14)
        assert merged[0].max_value == pytest.approx(53.95)


class TestRangePattern:
    """Range pattern: 'param is LOW-HIGH unit' → range constraint."""

    def test_torque_range_parsed(self):
        """'installation_torque is 9.0-11.0 N*m' → [9.0, 11.0] N*m."""
        st = SymbolTable()
        constraint, skip = _compile_clause("installation_torque is 9.0-11.0 N*m", st)
        assert skip is None
        assert constraint is not None
        assert constraint.is_equality is False
        assert constraint.min_value == pytest.approx(9.0)
        assert constraint.max_value == pytest.approx(11.0)
        assert constraint.canonical_name == "installation_torque"

    def test_range_no_unit(self):
        """'safety_factor is 2.0-3.0' → range, empty unit."""
        st = SymbolTable()
        constraint, skip = _compile_clause("safety_factor is 2.0-3.0", st)
        assert skip is None
        assert constraint is not None
        assert constraint.min_value == pytest.approx(2.0)
        assert constraint.max_value == pytest.approx(3.0)
        assert constraint.canonical_unit == ""

    def test_range_en_dash(self):
        """En-dash also works: '9.0\u20139.5 mm'."""
        st = SymbolTable()
        constraint, skip = _compile_clause("thickness is 9.0\u201311.0 mm", st)
        assert skip is None
        assert constraint is not None
        assert constraint.min_value is not None
        assert constraint.max_value is not None

    def test_equality_no_longer_captures_range_as_unit(self):
        """'installation_torque is 9.0-11.0 N*m' must NOT produce unit='-11.0'."""
        st = SymbolTable()
        constraint, skip = _compile_clause("installation_torque is 9.0-11.0 N*m", st)
        assert constraint is not None
        # Should be range, not equality with bad unit
        assert constraint.is_equality is False
        assert constraint.canonical_unit != "-11.0"

    def test_equality_still_works(self):
        """Simple equality still works: 'payload_mass is 5 kg'."""
        st = SymbolTable()
        constraint, skip = _compile_clause("payload_mass is 5 kg", st)
        assert constraint is not None
        assert constraint.is_equality is True
        assert constraint.exact_value == pytest.approx(5.0)

    def test_equality_unit_rejects_leading_dash_digit(self):
        """Equality pattern won't capture '-11.0' as unit."""
        st = SymbolTable()
        # Standalone equality with no range — ensure no spurious unit capture
        constraint, skip = _compile_clause("payload_mass is 5.0", st)
        assert constraint is not None
        assert constraint.canonical_unit == ""
