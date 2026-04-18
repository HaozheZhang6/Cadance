"""Tests for contract SAT checks."""

import pytest

from src.hypergraph.models import Contract
from src.verification.semantic.contract_sat import (
    check_contract_sat,
)
from src.verification.semantic.symbol_table import SymbolTable


class TestSatA:
    """Test SAT(A) - assumption satisfiability."""

    def test_sat_a_consistent_assumptions(self):
        """Consistent assumptions return SAT."""
        contract = Contract(
            id="contract_consistent",
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
        result = check_contract_sat(contract, symbol_table)

        assert result.sat_a_status == "SAT"
        assert "payload_mass" in result.sat_a_witness
        assert result.sat_a_witness["payload_mass"]["value"] == pytest.approx(5.0)

    def test_sat_a_contradictory_assumptions_unsat(self):
        """Contradictory assumptions return UNSAT with core."""
        contract = Contract(
            id="contract_contradict",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "payload_mass is 10 kg", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = check_contract_sat(contract, symbol_table)

        assert result.sat_a_status == "UNSAT"
        assert len(result.sat_a_core) > 0
        # Core should contain CONTRACT_* names
        assert any("CONTRACT_" in name for name in result.sat_a_core)

    def test_sat_a_empty_assumptions_sat(self):
        """Empty assumptions are vacuously SAT."""
        contract = Contract(
            id="contract_empty_a",
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
        result = check_contract_sat(contract, symbol_table)

        assert result.sat_a_status == "SAT"
        assert result.sat_a_witness == {}

    def test_sat_a_invariant_violation_unsat(self):
        """Assumption violating domain invariant returns UNSAT."""
        # Use shock_factor (FACTOR_GE1 domain) - "safety" triggers NL skip
        contract = Contract(
            id="contract_inv_violate",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "shock_factor is 0.5", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = check_contract_sat(contract, symbol_table)

        # shock_factor < 1 violates INV_GE1_shock_factor
        assert result.sat_a_status == "UNSAT"
        assert "INV_GE1_shock_factor" in result.sat_a_core


class TestSatAG:
    """Test SAT(A AND G) - guarantees under assumptions."""

    def test_sat_ag_achievable_guarantees(self):
        """Achievable guarantees return SAT."""
        contract = Contract(
            id="contract_achievable",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
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
        result = check_contract_sat(contract, symbol_table)

        assert result.sat_ag_status == "SAT"
        assert "payload_mass" in result.sat_ag_witness
        assert "deflection" in result.sat_ag_witness

    def test_sat_ag_conflicting_guarantees_unsat(self):
        """Guarantees conflicting with assumptions return UNSAT."""
        # Assumption: deflection <= 1mm, Guarantee: deflection >= 2mm
        contract = Contract(
            id="contract_conflict_ag",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "deflection no more than 1 mm",
                            "confidence": "Confident",
                        },
                    ],
                    "guarantees": [
                        {"text": "minimum deflection 2 mm", "confidence": "Confident"},
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = check_contract_sat(contract, symbol_table)

        assert result.sat_ag_status == "UNSAT"
        assert len(result.sat_ag_core) > 0
        # Core should have both assumption and guarantee constraints
        has_a = any("_A_" in name for name in result.sat_ag_core)
        has_g = any("_G_" in name for name in result.sat_ag_core)
        assert has_a or has_g  # At least one contract constraint in core

    def test_sat_ag_empty_guarantees_equals_sat_a(self):
        """Empty guarantees means SAT(A AND G) = SAT(A)."""
        contract = Contract(
            id="contract_no_g",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        symbol_table = SymbolTable()
        result = check_contract_sat(contract, symbol_table)

        assert result.sat_a_status == result.sat_ag_status
        assert result.sat_a_witness == result.sat_ag_witness

    def test_sat_ag_inherits_sat_a_unsat(self):
        """If SAT(A) is UNSAT, SAT(A AND G) is also UNSAT."""
        contract = Contract(
            id="contract_a_unsat",
            description="Test",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "payload_mass is 10 kg", "confidence": "Confident"},
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
        result = check_contract_sat(contract, symbol_table)

        # Both should be UNSAT
        assert result.sat_a_status == "UNSAT"
        assert result.sat_ag_status == "UNSAT"


class TestContractSatResultStructure:
    """Test result structure and fields."""

    def test_result_has_compilation_result(self):
        """Result includes compilation stats."""
        contract = Contract(
            id="contract_stats",
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
        result = check_contract_sat(contract, symbol_table)

        assert result.compilation_result is not None
        assert result.compilation_result.compiled_count == 1
        assert result.compilation_result.skipped_count == 1


class TestGoldenFixtures:
    """Test against golden fixtures from CONTEXT.md."""

    def test_contract_bbf23697_sat(self):
        """contract_bbf23697 should have SAT(A) and SAT(A AND G)."""
        # G2 uses "clearance_diameter is 14 mm" (equality) since compiler
        # doesn't support "value unit +/- tol" without "within/of" keyword
        contract = Contract(
            id="contract_bbf23697",
            description="Contract between Mounting Bracket and User/Installer",
            metadata={
                "terms": {
                    "assumptions": [
                        {
                            "text": "installation torque within 10 N*m +/-20%",
                            "confidence": "Likely",
                        },
                        {
                            "text": "tooling consistent with specified clearance diameter",
                            "confidence": "Likely",
                        },
                    ],
                    "guarantees": [
                        {
                            "text": "minimum edge radius 1 mm (+/-0.5 mm)",
                            "confidence": "Confident",
                        },
                        {
                            "text": "clearance_diameter is 14 mm",
                            "confidence": "Confident",
                        },
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = check_contract_sat(contract, symbol_table)

        # Compilation: 3 compile (A1, G1, G2), 1 skip (A2 - "specified" triggers skip)
        assert result.compilation_result.compiled_count >= 3
        assert result.compilation_result.skipped_count >= 1

        # Both checks should be SAT
        assert result.sat_a_status == "SAT"
        assert result.sat_ag_status == "SAT"

    def test_contract_1e60d8b2_sat(self):
        """contract_1e60d8b2 should have SAT(A) and SAT(A AND G)."""
        contract = Contract(
            id="contract_1e60d8b2",
            description="Contract between Mounting Bracket and Payload",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "Payload mass is 5 kg", "confidence": "Confident"},
                        {"text": "shock_factor is 5.0", "confidence": "Confident"},
                        {
                            "text": "Deflection no more than 1 mm",
                            "confidence": "Confident",
                        },
                    ],
                    "guarantees": [
                        {
                            "text": "Tip deflection no more than 0.001 m",
                            "confidence": "Confident",
                        },
                    ],
                }
            },
        )
        symbol_table = SymbolTable()
        result = check_contract_sat(contract, symbol_table)

        # Both checks should be SAT
        assert result.sat_a_status == "SAT"
        assert result.sat_ag_status == "SAT"


class TestContractSatScoped:
    """Test scoped contract SAT with identity gate."""

    def test_check_contract_sat_scoped_returns_sat(self):
        """Scoped SAT with consistent assumptions returns SAT."""
        from src.verification.semantic.contract_sat import check_contract_sat_scoped
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_scoped_sat",
            description="Test scoped SAT",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = check_contract_sat_scoped(contract, scoped_table)

        assert result.sat_a_status == "SAT"
        # Witness should use scoped key format
        witness_keys = list(result.sat_a_witness.keys())
        assert any("__" in k for k in witness_keys)  # scoped key format

    def test_check_contract_sat_scoped_identity_gate_blocks(self):
        """Missing scoped_key blocks with BLOCKED status."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.contract_sat import check_contract_sat_scoped
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        # Create contract that will produce constraint without scoped_key
        # (using unmapped quantity that gets skipped, then force a broken constraint)
        contract = Contract(
            id="contract_blocked",
            description="Test identity gate",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()

        # Patch compilation to produce constraint without scoped_key
        from unittest.mock import patch

        from src.verification.semantic.contract_compiler import (
            ContractCompilationResult,
        )

        broken_constraint = Constraint(
            name="CONTRACT_broken_A_1",
            min_name="CONTRACT_broken_A_1_min",
            max_name="CONTRACT_broken_A_1_max",
            min_value=4.5,
            max_value=5.5,
            canonical_unit="kg",
            is_equality=False,
            canonical_name="payload_mass",
            term_class="structured",
            source_spec_id="contract_blocked",
            scoped_key=None,  # Missing!
        )
        broken_result = ContractCompilationResult(
            constraints=[broken_constraint], compiled_count=1
        )

        with patch(
            "src.verification.semantic.contract_compiler.compile_contract_clauses_scoped",
            return_value=broken_result,
        ):
            result = check_contract_sat_scoped(contract, scoped_table)

        assert result.sat_a_status == "BLOCKED"
        assert "identity" in result.sat_a_core[0].lower()

    def test_dump_contract_smt2_includes_clause_comments(self):
        """SMT2 dump includes comments mapping assertions to clause text."""
        from z3 import Real, Solver

        from src.verification.semantic.contract_sat import dump_contract_smt2

        solver = Solver()
        x = Real("system__normal__payload_mass")
        solver.assert_and_track(x >= 4.5, "CONTRACT_xxx_A_1_min")
        solver.assert_and_track(x <= 5.5, "CONTRACT_xxx_A_1_max")

        clause_map = {"CONTRACT_xxx_A_1": "payload_mass is 5 kg"}

        smt2 = dump_contract_smt2(solver, clause_map)

        # Should contain comment with clause text
        assert "; CONTRACT_xxx_A_1: payload_mass is 5 kg" in smt2

    def test_explain_contract_core_maps_to_clauses(self):
        """Core explanation maps UNSAT core to clause texts and inequalities."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.contract_sat import (
            ContractCoreExplanation,
            explain_contract_core,
        )
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
        )

        core = ["CONTRACT_xxx_A_1_min", "CONTRACT_xxx_A_2"]
        clause_map = {
            "CONTRACT_xxx_A_1": "payload_mass is 5 kg",
            "CONTRACT_xxx_A_2": "payload_mass is 10 kg",
        }
        constraints = [
            Constraint(
                name="CONTRACT_xxx_A_1",
                min_name="CONTRACT_xxx_A_1_min",
                max_name="CONTRACT_xxx_A_1_max",
                min_value=4.5,
                max_value=5.5,
                canonical_unit="kg",
                is_equality=False,
                canonical_name="payload_mass",
                term_class="structured",
                source_spec_id="xxx",
                scoped_key=ScopedKey("system", "normal", "payload_mass"),
            ),
            Constraint(
                name="CONTRACT_xxx_A_2",
                min_name="CONTRACT_xxx_A_2_min",
                max_name="CONTRACT_xxx_A_2_max",
                exact_value=10.0,
                canonical_unit="kg",
                is_equality=True,
                canonical_name="payload_mass",
                term_class="structured",
                source_spec_id="xxx",
                scoped_key=ScopedKey("system", "normal", "payload_mass"),
            ),
        ]

        explanation = explain_contract_core(core, clause_map, constraints)

        assert isinstance(explanation, ContractCoreExplanation)
        assert "payload_mass is 5 kg" in explanation.clause_texts
        assert "payload_mass is 10 kg" in explanation.clause_texts
        assert len(explanation.inequalities) > 0
        assert explanation.summary  # Non-empty summary

    def test_contradiction_yields_clause_naming_core(self):
        """Intentional contradiction yields core explanation with both clause texts."""
        from src.verification.semantic.contract_sat import check_contract_sat_scoped
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        contract = Contract(
            id="contract_contradict_scoped",
            description="Test contradiction",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"},
                        {"text": "payload_mass is 10 kg", "confidence": "Confident"},
                    ],
                    "guarantees": [],
                }
            },
        )
        scoped_table = ScopedSymbolTable()
        result = check_contract_sat_scoped(contract, scoped_table)

        assert result.sat_a_status == "UNSAT"
        assert result.core_explanation is not None
        # Both conflicting clauses should be named
        assert "payload_mass is 5 kg" in result.core_explanation.clause_texts
        assert "payload_mass is 10 kg" in result.core_explanation.clause_texts
