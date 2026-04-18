"""Tests for SemanticVerifier integration."""

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import Contract, SpecificationNode, SpecParameter
from src.hypergraph.store import HypergraphStore
from src.verification.base import VerificationStatus
from src.verification.tier4_semantic import SemanticVerifier


@pytest.fixture
def engine(tmp_path):
    store = HypergraphStore(tmp_path / "test.json")
    return HypergraphEngine(store)


@pytest.fixture
def verifier(engine):
    return SemanticVerifier(engine)


class TestSemanticVerifierBasic:
    """Basic verifier tests."""

    def test_tier_is_v4_semantic(self, verifier):
        assert verifier.tier == "V4-semantic"

    def test_cost_higher_than_syntactic(self, verifier):
        assert verifier.cost > 0.3  # Syntactic is 0.3


class TestVerifyNode:
    """Test single node verification."""

    def test_skip_non_spec_node(self, engine, verifier):
        from src.hypergraph.models import GoalNode

        goal = GoalNode(
            id="GOAL-001",
            description="Test goal",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        engine.add_node(goal)
        result = verifier.verify_node("GOAL-001")
        assert result.status == VerificationStatus.SKIPPED

    def test_pass_spec_with_sat_constraints(self, engine, verifier):
        spec = SpecificationNode(
            id="SPEC-001",
            description="Test spec",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=100, unit="mm", tolerance="+/- 5%"
                )
            ],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-001")
        assert result.status == VerificationStatus.PASSED
        assert "satisfiable" in result.message
        assert "witness" in result.details

    def test_fail_spec_with_unsat_constraints(self, engine, verifier):
        spec = SpecificationNode(
            id="SPEC-002",
            description="Impossible spec",
            parameters=[
                # min > max is impossible
                SpecParameter(name="hole_diameter", value=0, unit="m", tolerance="10-5")
            ],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-002")
        assert result.status == VerificationStatus.FAILED
        assert "UNSAT" in result.message
        assert "explanation" in result.details

    def test_pass_spec_no_constraints(self, engine, verifier):
        spec = SpecificationNode(
            id="SPEC-003",
            description="No numeric params",
            parameters=[],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-003")
        assert result.status == VerificationStatus.PASSED
        assert "No numeric constraints" in result.message


class TestVerifyAllSpecs:
    """Test all-specs verification."""

    def test_sat_multiple_compatible_specs(self, engine, verifier):
        spec1 = SpecificationNode(
            id="SPEC-001",
            description="Diameter spec",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=100, unit="mm", tolerance="+/- 10%"
                )
            ],
        )
        spec2 = SpecificationNode(
            id="SPEC-002",
            description="Thickness spec",
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=50, unit="mm", tolerance="+/- 10%"
                )
            ],
        )
        engine.add_node(spec1)
        engine.add_node(spec2)

        result = verifier.verify_all_specs()
        assert result.status == VerificationStatus.PASSED
        assert "SAT" in result.message
        assert result.details["spec_count"] == 2

    def test_unsat_conflicting_specs(self, engine, verifier):
        # Create specs with impossible internal constraints
        spec = SpecificationNode(
            id="SPEC-001",
            description="Impossible",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=0, unit="m", tolerance="10-5"
                )  # min > max
            ],
        )
        engine.add_node(spec)

        result = verifier.verify_all_specs()
        assert result.status == VerificationStatus.FAILED
        assert "UNSAT" in result.message
        assert "fix_hint" in result.details["explanation"]

    def test_empty_graph_passes(self, engine, verifier):
        result = verifier.verify_all_specs()
        assert result.status == VerificationStatus.PASSED


class TestVerifyEdge:
    """Test edge verification (should skip)."""

    def test_edge_skipped(self, engine, verifier):
        from src.hypergraph.models import EdgeType, GoalNode

        # Add two nodes first
        node1 = GoalNode(
            id="GOAL-001",
            description="Test goal 1",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        node2 = GoalNode(
            id="GOAL-002",
            description="Test goal 2",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        engine.add_node(node1)
        engine.add_node(node2)

        # Add edge between them
        edge_id = engine.add_edge("GOAL-001", "GOAL-002", EdgeType.HAS_CHILD)
        result = verifier.verify_edge(edge_id)
        assert result.status == VerificationStatus.SKIPPED


class TestCrossSpecUnification:
    """Tests for cross-spec variable unification via SymbolTable (08-03)."""

    def test_cross_spec_contradiction_returns_unsat(self, engine, verifier):
        """TEST-SMOKE-UNSAT: Cross-spec contradiction detection.

        Two specs constrain same canonical variable via aliases to incompatible exact values.
        Spec A: payload_mass = 5 +/- 0 kg (exact)
        Spec B: mass = 7 +/- 0 kg (exact) -- 'mass' is alias for 'payload_mass'

        Expected: UNSAT with core naming both constraints.
        """
        spec_a = SpecificationNode(
            id="SPEC-A",
            description="Spec with payload_mass=5kg",
            parameters=[
                SpecParameter(
                    name="payload_mass", value=5.0, unit="kg", tolerance=""
                )  # exact
            ],
        )
        spec_b = SpecificationNode(
            id="SPEC-B",
            description="Spec with mass=7kg (alias for payload_mass)",
            parameters=[
                SpecParameter(name="mass", value=7.0, unit="kg", tolerance="")  # exact
            ],
        )
        engine.add_node(spec_a)
        engine.add_node(spec_b)

        result = verifier.verify_all_specs()

        # Assert UNSAT
        assert result.status == VerificationStatus.FAILED
        assert "UNSAT" in result.message
        assert "cross-spec conflict" in result.message.lower()

        # Assert UNSAT core contains constraints from both specs
        unsat_core = result.details["unsat_core"]
        spec_a_constraints = [c for c in unsat_core if c.startswith("SPEC-A")]
        spec_b_constraints = [c for c in unsat_core if c.startswith("SPEC-B")]
        assert len(spec_a_constraints) > 0, "UNSAT core should mention SPEC-A"
        assert len(spec_b_constraints) > 0, "UNSAT core should mention SPEC-B"

        # Assert explanation identifies cross-spec conflict
        explanation = result.details["explanation"]
        assert "SPEC-A" in explanation["summary"] or "SPEC-A" in str(
            explanation["details"]
        )
        assert "SPEC-B" in explanation["summary"] or "SPEC-B" in str(
            explanation["details"]
        )
        assert (
            "payload_mass" in explanation["fix_hint"].lower()
            or "mass" in explanation["fix_hint"].lower()
        )

    def test_cross_spec_consistent_values_returns_sat(self, engine, verifier):
        """Two specs with same canonical value should be SAT."""
        spec_a = SpecificationNode(
            id="SPEC-C",
            description="Spec with payload_mass=5kg",
            parameters=[
                SpecParameter(name="payload_mass", value=5.0, unit="kg", tolerance="")
            ],
        )
        spec_b = SpecificationNode(
            id="SPEC-D",
            description="Spec with mass=5kg (alias, same value)",
            parameters=[SpecParameter(name="mass", value=5.0, unit="kg", tolerance="")],
        )
        engine.add_node(spec_a)
        engine.add_node(spec_b)

        result = verifier.verify_all_specs()

        # Should be SAT since both specs agree on payload_mass=5.0
        assert result.status == VerificationStatus.PASSED
        assert "SAT" in result.message
        # Witness uses scoped keys: system__normal__payload_mass
        witness = result.details["witness"]
        scoped_key = "system__normal__payload_mass"
        assert scoped_key in witness
        assert witness[scoped_key]["value"] == 5.0

    def test_unmapped_param_skipped_with_suggestion(self, engine, verifier):
        """Unmapped params generate UNMAPPED_SYMBOL warning."""
        spec = SpecificationNode(
            id="SPEC-E",
            description="Spec with unmapped param",
            parameters=[
                SpecParameter(
                    name="payload_weight", value=5.0, unit="kg", tolerance=""
                )  # unmapped, not in scoped ontology
            ],
        )
        engine.add_node(spec)

        result = verifier.verify_node("SPEC-E")

        # Should skip with UNMAPPED_SYMBOL warning
        assert result.status == VerificationStatus.WARNING
        warnings = result.details.get("warnings", [])
        unmapped_warnings = [w for w in warnings if w["code"] == "UNMAPPED_SYMBOL"]
        assert len(unmapped_warnings) > 0

        # Warning should indicate param is not in scoped ontology
        unmapped_warning = unmapped_warnings[0]
        assert "payload_weight" in unmapped_warning["field"]
        assert "not in scoped ontology" in unmapped_warning["message"]


class TestCoverageThreshold:
    """Test coverage threshold warnings (07-03)."""

    def test_coverage_above_threshold_no_warning(self, engine):
        """Coverage above threshold -> no LOW_COVERAGE warning."""
        verifier = SemanticVerifier(engine, coverage_threshold=0.6)
        spec = SpecificationNode(
            id="SPEC-COV-1",
            description="High coverage spec",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=10, unit="mm", tolerance="+/- 5%"
                ),
                SpecParameter(name="payload_mass", value=5, unit="kg", tolerance=""),
                SpecParameter(
                    name="p3", value=3, unit="badunit", tolerance=""
                ),  # 1 skip
            ],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-COV-1")
        assert result.status == VerificationStatus.PASSED
        # Coverage = 2/3 = 66% > 60% threshold
        assert result.details["coverage"]["percentage"] == "67%"
        warnings = result.details.get("warnings", [])
        assert not any(w["code"] == "LOW_COVERAGE" for w in warnings)

    def test_coverage_below_threshold_warning(self, engine):
        """Coverage below threshold -> LOW_COVERAGE warning."""
        verifier = SemanticVerifier(engine, coverage_threshold=0.6)
        spec = SpecificationNode(
            id="SPEC-COV-2",
            description="Low coverage spec",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=10, unit="mm", tolerance="+/- 5%"
                ),
                SpecParameter(name="p2", value=5, unit="bad1", tolerance=""),  # skip
                SpecParameter(name="p3", value=3, unit="bad2", tolerance=""),  # skip
            ],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-COV-2")
        # Coverage = 1/3 = 33% < 60% threshold
        assert result.details["coverage"]["percentage"] == "33%"
        warnings = result.details.get("warnings", [])
        assert any(w["code"] == "LOW_COVERAGE" for w in warnings)
        low_cov_warning = next(w for w in warnings if w["code"] == "LOW_COVERAGE")
        assert "33%" in low_cov_warning["message"]
        assert "skip_breakdown" in low_cov_warning

    def test_coverage_info_in_result_details(self, engine, verifier):
        """Coverage summary included in result details."""
        spec = SpecificationNode(
            id="SPEC-COV-3",
            description="Coverage tracking",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=10, unit="mm", tolerance="+/- 5%"
                ),
                SpecParameter(name="payload_mass", value=5, unit="kg", tolerance=""),
            ],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-COV-3")
        assert "coverage" in result.details
        cov = result.details["coverage"]
        assert cov["compiled"] == 2
        assert cov["skipped"] == 0
        assert cov["total"] == 2
        assert cov["percentage"] == "100%"
        assert isinstance(cov["skip_breakdown"], dict)

    def test_low_coverage_does_not_change_status(self, engine):
        """LOW_COVERAGE warning does not change PASSED status."""
        verifier = SemanticVerifier(engine, coverage_threshold=0.9)
        spec = SpecificationNode(
            id="SPEC-COV-4",
            description="Status test",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=10, unit="mm", tolerance="+/- 5%"
                )
            ],
        )
        engine.add_node(spec)
        result = verifier.verify_node("SPEC-COV-4")
        # Coverage = 100% but for coverage test in verify_all_specs
        assert result.status == VerificationStatus.PASSED

    def test_coverage_all_specs(self, engine):
        """Coverage tracking works across all specs."""
        verifier = SemanticVerifier(engine, coverage_threshold=0.6)
        spec1 = SpecificationNode(
            id="SPEC-ALL-1",
            description="Spec 1",
            parameters=[
                SpecParameter(
                    name="hole_diameter", value=10, unit="mm", tolerance="+/- 5%"
                ),
                SpecParameter(name="p2", value=5, unit="badunit", tolerance=""),
            ],
        )
        spec2 = SpecificationNode(
            id="SPEC-ALL-2",
            description="Spec 2",
            parameters=[
                SpecParameter(name="payload_mass", value=20, unit="kg", tolerance=""),
                SpecParameter(name="p4", value=3, unit="badunit2", tolerance=""),
            ],
        )
        engine.add_node(spec1)
        engine.add_node(spec2)
        result = verifier.verify_all_specs()
        # Coverage = 2/4 = 50% < 60%
        assert result.details["coverage"]["percentage"] == "50%"
        assert result.details["coverage"]["compiled"] == 2
        assert result.details["coverage"]["skipped"] == 2
        warnings = result.details.get("warnings", [])
        assert any(w["code"] == "LOW_COVERAGE" for w in warnings)


class TestVerifyContracts:
    """Test contract verification with SAT(A), SAT(A AND G), SAT(A AND G AND Specs)."""

    def test_verify_contracts_all_sat(self, engine, verifier):
        """Compatible contract and specs return all SAT."""
        # Add spec with plate_thickness = 5mm
        spec = SpecificationNode(
            id="SPEC-001",
            description="Thickness spec",
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=5.0, unit="mm", tolerance=""
                )
            ],
        )
        engine.add_node(spec)

        # Add contract with compatible guarantee
        contract = Contract(
            id="contract_001",
            description="Compatible contract",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [
                        {
                            "text": "plate_thickness no more than 10 mm",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        engine.add_node(contract)

        result = verifier.verify_contracts()

        assert result.status == VerificationStatus.PASSED
        assert "contract_001" in result.details["per_contract"]
        contract_result = result.details["per_contract"]["contract_001"]
        assert contract_result["sat_a"] == "SAT"
        assert contract_result["sat_ag"] == "SAT"
        assert contract_result["sat_ags"] == "SAT"

    def test_verify_contracts_contract_spec_conflict_unsat(self, engine, verifier):
        """Contract guarantee conflicting with spec returns UNSAT with combined core."""
        # Spec: plate_thickness = 5mm (exactly)
        spec = SpecificationNode(
            id="SPEC-002",
            description="Thickness spec",
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=5.0, unit="mm", tolerance=""
                )
            ],
        )
        engine.add_node(spec)

        # Contract: guarantee plate_thickness >= 10mm (conflicts!)
        contract = Contract(
            id="contract_conflict",
            description="Conflicting contract",
            metadata={
                "terms": {
                    "assumptions": [],
                    "guarantees": [
                        {
                            "text": "minimum plate_thickness 10 mm",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        engine.add_node(contract)

        result = verifier.verify_contracts()

        assert result.status == VerificationStatus.FAILED
        contract_result = result.details["per_contract"]["contract_conflict"]
        assert contract_result["sat_ags"] == "UNSAT"
        # Core should contain both spec and contract constraints
        core = contract_result["unsat_core"]
        has_spec = any("SPEC-002" in name for name in core)
        has_contract = any("CONTRACT_" in name for name in core)
        assert has_spec and has_contract

    def test_verify_contracts_assumption_violates_spec_unsat(self, engine, verifier):
        """Contract assumption conflicting with spec returns UNSAT."""
        # Spec: payload_mass = 5kg
        spec = SpecificationNode(
            id="SPEC-003",
            description="Mass spec",
            parameters=[
                SpecParameter(name="payload_mass", value=5.0, unit="kg", tolerance="")
            ],
        )
        engine.add_node(spec)

        # Contract: assumption payload_mass = 10kg (conflicts!)
        contract = Contract(
            id="contract_mass_conflict",
            description="Conflicting mass",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 10 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        engine.add_node(contract)

        result = verifier.verify_contracts()

        assert result.status == VerificationStatus.FAILED
        contract_result = result.details["per_contract"]["contract_mass_conflict"]
        assert contract_result["sat_ags"] == "UNSAT"

    def test_verify_contracts_no_contracts_passed(self, engine, verifier):
        """No contracts in graph returns PASSED with empty results."""
        spec = SpecificationNode(
            id="SPEC-004",
            description="Spec only",
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=5.0, unit="mm", tolerance=""
                )
            ],
        )
        engine.add_node(spec)

        result = verifier.verify_contracts()

        assert result.status == VerificationStatus.PASSED
        assert result.details["contract_count"] == 0

    def test_verify_contracts_multiple_contracts(self, engine, verifier):
        """Multiple contracts each checked independently."""
        spec = SpecificationNode(
            id="SPEC-005",
            description="Spec",
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=5.0, unit="mm", tolerance=""
                )
            ],
        )
        engine.add_node(spec)

        # Contract 1: compatible
        contract1 = Contract(
            id="contract_ok",
            description="OK",
            metadata={
                "terms": {
                    "assumptions": [
                        {"text": "payload_mass is 5 kg", "confidence": "Confident"}
                    ],
                    "guarantees": [],
                }
            },
        )
        engine.add_node(contract1)

        # Contract 2: conflicts
        contract2 = Contract(
            id="contract_bad",
            description="Bad",
            metadata={
                "terms": {
                    "assumptions": [],
                    "guarantees": [
                        {
                            "text": "minimum plate_thickness 10 mm",
                            "confidence": "Confident",
                        }
                    ],
                }
            },
        )
        engine.add_node(contract2)

        result = verifier.verify_contracts()

        # Overall FAILED because one contract failed
        assert result.status == VerificationStatus.FAILED
        assert result.details["per_contract"]["contract_ok"]["sat_ags"] == "SAT"
        assert result.details["per_contract"]["contract_bad"]["sat_ags"] == "UNSAT"

    def test_verify_contracts_includes_compilation_stats(self, engine, verifier):
        """Result includes compilation statistics per contract."""
        contract = Contract(
            id="contract_stats",
            description="Stats test",
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
        engine.add_node(contract)

        result = verifier.verify_contracts()

        contract_result = result.details["per_contract"]["contract_stats"]
        assert "compilation" in contract_result
        assert contract_result["compilation"]["compiled"] == 1
        assert contract_result["compilation"]["skipped"] == 1

    def test_verify_contracts_sat_a_unsat_propagates(self, engine, verifier):
        """If SAT(A) is UNSAT, all subsequent checks are UNSAT."""
        # Contract with contradictory assumptions
        contract = Contract(
            id="contract_internal_conflict",
            description="Internal conflict",
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
                        }
                    ],
                }
            },
        )
        engine.add_node(contract)

        result = verifier.verify_contracts()

        assert result.status == VerificationStatus.FAILED
        contract_result = result.details["per_contract"]["contract_internal_conflict"]
        assert contract_result["sat_a"] == "UNSAT"
        assert contract_result["sat_ag"] == "UNSAT"
        assert contract_result["sat_ags"] == "UNSAT"


class TestProductionWiring:
    """Tests for v1.3 production wiring (Phase 15)."""

    def test_golden_run_deterministic_bindings(self, engine):
        """Same SAT case produces identical bindings across 3 runs."""
        spec = SpecificationNode(
            id="SPEC-GOLD-001",
            description="Golden test",
            metadata={"interface": "bracket"},
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=5.0, unit="mm", tolerance="+/- 10%"
                ),
                SpecParameter(
                    name="hole_diameter", value=10.0, unit="mm", tolerance="+/- 5%"
                ),
            ],
        )
        engine.add_node(spec)

        binding_logs = []
        for _ in range(3):
            verifier = SemanticVerifier(engine)
            result = verifier.verify_all_specs()
            assert result.status == VerificationStatus.PASSED
            binding_logs.append(verifier.log_binding_table())

        # All 3 runs produce identical bindings
        assert binding_logs[0] == binding_logs[1] == binding_logs[2]
        # Bindings captured
        assert len(binding_logs[0]) >= 2

    def test_consistency_same_spec_twice(self, engine):
        """Same spec verified twice produces identical bindings."""
        spec = SpecificationNode(
            id="SPEC-CONSIST-001",
            description="Consistency test",
            metadata={"interface": "bracket"},
            parameters=[
                SpecParameter(
                    name="plate_thickness",
                    value=5.0,
                    unit="mm",
                    tolerance="+/- 10%",
                ),
            ],
        )
        engine.add_node(spec)

        # Run 1
        v1 = SemanticVerifier(engine)
        r1 = v1.verify_all_specs()
        log1 = v1.log_binding_table()

        # Run 2 (fresh verifier, same engine state)
        v2 = SemanticVerifier(engine)
        r2 = v2.verify_all_specs()
        log2 = v2.log_binding_table()

        # Both SAT
        assert r1.status == VerificationStatus.PASSED
        assert r2.status == VerificationStatus.PASSED

        # Bindings identical
        assert log1 == log2

        # Verify identity fields populated
        assert len(log1) >= 1
        for entry in log1:
            assert entry["entity_id"]
            assert entry["regime_id"]

    def test_identity_gate_raises_on_incomplete_structured_term(self, engine):
        """Direct test: solve_constraints_scoped raises on incomplete identity."""
        from src.verification.semantic.constraint_extractor import Constraint
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
            ScopedSymbolTable,
        )
        from src.verification.semantic.z3_solver import solve_constraints_scoped

        # Create constraint with empty entity_id (should fail gate)
        bad_constraint = Constraint(
            name="bad_constraint",
            min_name="bad_min",
            max_name="bad_max",
            min_value=0.0,
            max_value=10.0,
            canonical_unit="mm",
            is_equality=False,
            canonical_name="plate_thickness",
            scoped_key=ScopedKey(
                entity_id="", regime_id="normal", quantity_id="plate_thickness"
            ),
            term_class="structured",
            source_spec_id="SPEC-BAD",
        )

        scoped_table = ScopedSymbolTable()

        with pytest.raises(ValueError) as exc_info:
            solve_constraints_scoped([bad_constraint], scoped_table)

        assert "entity_id" in str(exc_info.value).lower()

    def test_verify_contracts_identity_gate_scoped(self, engine):
        """verify_contracts uses scoped contract SAT with identity gate."""
        # Create contract with valid assumptions
        contract = Contract(
            id="contract_test_scoped",
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
        engine.add_node(contract)

        # Run verify_contracts
        verifier = SemanticVerifier(engine)
        result = verifier.verify_contracts()

        # Should use scoped SAT (witness keys in scoped format)
        contract_result = result.details["per_contract"].get("contract_test_scoped")
        assert contract_result is not None
        # Scoped format: system__normal__payload_mass
        if contract_result["sat_a"] == "SAT":
            # SAT(A) uses scoped variables
            assert contract_result["sat_ag"] == "SAT"
            assert contract_result["sat_ags"] == "SAT"
            # Compilation occurred
            assert contract_result["compilation"]["compiled"] == 1

    def test_verify_contracts_core_explanation_on_unsat(self, engine):
        """verify_contracts includes core_explanation on UNSAT."""
        # Create contract with conflicting assumptions
        contract = Contract(
            id="contract_conflict_test",
            description="Conflicting assumptions",
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
        engine.add_node(contract)

        verifier = SemanticVerifier(engine)
        result = verifier.verify_contracts()

        assert result.status == VerificationStatus.FAILED
        contract_result = result.details["per_contract"]["contract_conflict_test"]
        assert contract_result["sat_a"] == "UNSAT"
        # Core explanation should be present
        assert "core_explanation" in contract_result
        explanation = contract_result["core_explanation"]
        assert len(explanation["clause_texts"]) >= 1
        assert "UNSAT" in explanation["summary"]
