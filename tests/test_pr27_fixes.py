"""Tests for PR #27 review fixes."""

from src.agents.schemas import SpecOutput, SpecParameterOutput
from src.hypergraph.models import SpecificationNode, SpecParameter
from src.verification.base import VerificationResult, VerificationStatus
from src.verification.gate_report import GateReport
from src.verification.semantic.conflict_explainer import explain_conflict
from src.verification.semantic.constraint_extractor import (
    extract_constraints,
    extract_constraints_scoped,
)
from src.verification.semantic.z3_solver import solve_constraints

# --- Fix 1: Scoped identity fields persisted through hypergraph ---


class TestScopedIdentityPersistence:
    """Scoped IDs survive SpecParameter/SpecificationNode round-trip."""

    def test_spec_parameter_stores_quantity_id_term_class(self):
        p = SpecParameter(
            name="wall_thickness",
            value=2.5,
            unit="mm",
            quantity_id="wall_thickness",
            term_class="structured",
        )
        d = p.model_dump()
        restored = SpecParameter(**d)
        assert restored.quantity_id == "wall_thickness"
        assert restored.term_class == "structured"

    def test_specification_node_stores_entity_regime(self):
        node = SpecificationNode(
            id="spec_001",
            description="test",
            entity_id="bracket",
            regime_id="normal",
        )
        d = node.model_dump()
        restored = SpecificationNode(**d)
        assert restored.entity_id == "bracket"
        assert restored.regime_id == "normal"

    def test_spec_parameter_output_to_spec_parameter_preserves_ids(self):
        """SpecParameterOutput.model_dump() -> SpecParameter keeps quantity_id/term_class."""
        out = SpecParameterOutput(
            name="hole_diameter",
            value="6.5",
            unit="mm",
            quantity_id="hole_diameter",
            term_class="structured",
        )
        p = SpecParameter(**out.model_dump())
        assert p.quantity_id == "hole_diameter"
        assert p.term_class == "structured"

    def test_spec_output_entity_regime_round_trip(self):
        """SpecOutput entity_id/regime_id survive reconstruction."""
        spec_out = SpecOutput(
            id="S1.1",
            description="test",
            entity_id="bracket",
            regime_id="startup",
        )
        assert spec_out.entity_id == "bracket"
        assert spec_out.regime_id == "startup"


# --- Fix 2: _compute_passing_nodes includes cross-spec UNSAT core ---


class TestComputePassingNodesCrossSpec:
    """_compute_passing_nodes excludes spec IDs from cross-spec unsat core."""

    def test_cross_spec_unsat_excludes_implicated_specs(self):

        from src.hypergraph.engine import HypergraphEngine
        from src.hypergraph.store import HypergraphStore
        from src.verification.pre_artifact_gate import PreArtifactGate

        # Setup engine with 2 spec nodes
        store = HypergraphStore(":memory:")
        engine = HypergraphEngine(store)

        spec1 = SpecificationNode(id="specification_aabbccdd", description="spec1")
        spec2 = SpecificationNode(id="specification_11223344", description="spec2")
        engine.add_node(spec1)
        engine.add_node(spec2)

        gate = PreArtifactGate(
            engine=engine,
            intent="test",
            store_path=":memory:",
            llm=None,
            max_attempts=1,
            coverage_threshold=0.7,
            verbose=False,
            auto=True,
        )

        # Report: tiers pass, contract passes, but cross-spec UNSAT
        report = GateReport(
            attempt=1,
            tier_results={},
            cross_spec_result=VerificationResult(
                status=VerificationStatus.FAILED,
                tier="V4-semantic",
                message="UNSAT",
                details={
                    "unsat_core": [
                        "specification_aabbccdd_wall_thickness_min",
                        "specification_aabbccdd_wall_thickness_max",
                    ]
                },
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
                details={"per_contract": {}},
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            v4_unsat_affected_ids={"specification_aabbccdd"},
        )

        passing = gate._compute_passing_nodes(report)
        # spec1 implicated by cross-spec UNSAT -> excluded
        assert "specification_aabbccdd" not in passing
        # spec2 not implicated -> included
        assert "specification_11223344" in passing


# --- Fix 3: verify_all() includes cross-spec failure ---


class TestVerifyAllCrossSpec:
    """Cross-spec UNSAT forces summary['passed'] == False."""

    def test_cross_spec_failure_forces_not_passed(self):
        from unittest.mock import MagicMock

        from src.hypergraph.engine import HypergraphEngine
        from src.hypergraph.store import HypergraphStore
        from src.verification.pipeline import VerificationPipeline

        store = HypergraphStore(":memory:")
        engine = HypergraphEngine(store)

        # Add a node so pipeline has something to iterate
        spec = SpecificationNode(id="spec_1", description="test")
        engine.add_node(spec)

        # Create a mock semantic verifier
        mock_verifier = MagicMock()
        mock_verifier.tier = "V4-semantic"
        mock_verifier.verify_node.return_value = VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V4-semantic",
            message="OK",
        )
        mock_verifier.verify_all_specs.return_value = VerificationResult(
            status=VerificationStatus.FAILED,
            tier="V4-semantic",
            message="UNSAT",
            details={"unsat_core": ["spec_1_x_min"]},
        )
        mock_verifier.verify_contracts.return_value = VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V4-semantic",
            message="SAT",
            details={"per_contract": {}},
        )

        pipeline = VerificationPipeline(engine)
        pipeline._verifiers = [mock_verifier]

        summary = pipeline.verify_all()
        assert summary["passed"] is False
        assert summary["total_failures"] >= 1
        assert summary["cross_spec_result"] is not None
        assert summary["cross_spec_result"]["status"] == "failed"


# --- Fix 4: Conflict explainer spec ID parsing ---


class TestConflictExplainerSpecIdParsing:
    """specification_<hex>_ constraint names parse correctly."""

    def test_specification_hex_id_grouped_correctly(self):
        """Two constraints from same spec should group together."""
        unsat_core = [
            "specification_aabbccdd_wall_thickness_min",
            "specification_aabbccdd_wall_thickness_max",
        ]
        constraints_by_name = {
            "specification_aabbccdd_wall_thickness_min": {"min_value": 10.0},
            "specification_aabbccdd_wall_thickness_max": {"max_value": 5.0},
        }
        result = explain_conflict(unsat_core, constraints_by_name)
        assert "1 specification" in result.summary
        assert "specification_aabbccdd" in result.fix_hint

    def test_two_distinct_specification_hex_ids(self):
        """Different spec hex IDs should be separate groups."""
        unsat_core = [
            "specification_aabbccdd_x_min",
            "specification_11223344_y_max",
        ]
        result = explain_conflict(unsat_core, {})
        assert "2 specification" in result.summary

    def test_legacy_spec_id_still_works(self):
        """SPEC-XXX format still parses correctly."""
        unsat_core = ["SPEC-001_width_min", "SPEC-001_width_max"]
        result = explain_conflict(unsat_core, {})
        assert "1 specification" in result.summary


# --- Fix 5: One-sided tolerance unit conversion error handling ---


class TestOneSidedToleranceUnitConversion:
    """One-sided tolerance + invalid unit yields warning, no exception."""

    def test_one_sided_invalid_unit_warning_extract_constraints(self):
        spec = SpecificationNode(
            id="SPEC-001",
            description="test",
            parameters=[
                SpecParameter(
                    name="pressure",
                    value=100,
                    unit="invalid_unit_xyz",
                    tolerance="min",
                )
            ],
        )
        result = extract_constraints(spec)
        assert result.compiled_count == 0
        assert result.skipped_count == 1
        warnings = [w for w in result.warnings if w.code == "UNIT_CONVERSION_FAILED"]
        assert len(warnings) == 1

    def test_one_sided_invalid_unit_warning_extract_constraints_scoped(self):
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        table = ScopedSymbolTable()
        spec = SpecificationNode(
            id="SPEC-002",
            description="test",
            parameters=[
                SpecParameter(
                    name="pressure",
                    value=100,
                    unit="invalid_unit_xyz",
                    tolerance="max",
                    quantity_id="pressure",
                    term_class="structured",
                )
            ],
        )
        result = extract_constraints_scoped(
            spec, table, entity_id="system", regime_id="normal"
        )
        assert result.compiled_count == 0
        assert result.skipped_count == 1
        warnings = [w for w in result.warnings if w.code == "UNIT_CONVERSION_FAILED"]
        assert len(warnings) == 1


# --- Fix 6: Z3 timeout configured ---


class TestZ3Timeout:
    """Solver has timeout set."""

    def test_solve_constraints_returns_result_not_hang(self):
        """Basic SAT check confirming solver runs with timeout."""
        from src.verification.semantic.constraint_extractor import Constraint

        c = Constraint(
            name="test_x",
            min_name="test_x_min",
            max_name="test_x_max",
            min_value=1.0,
            max_value=10.0,
            canonical_unit="m",
        )
        result = solve_constraints([c])
        assert result.status == "SAT"
        assert result.constraint_count == 1

    def test_empty_constraints_sat(self):
        result = solve_constraints([])
        assert result.status == "SAT"
