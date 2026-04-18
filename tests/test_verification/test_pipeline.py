"""Tests for verification pipeline."""

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    ContractStatus,
    EdgeType,
    Evidence,
    Intent,
    Unknown,
)
from src.hypergraph.store import HypergraphStore
from src.verification.base import VerificationResult, VerificationStatus
from src.verification.pipeline import VerificationPipeline
from src.verification.tier0_schema import SchemaVerifier
from src.verification.tier1_rules import RulesVerifier


class TestVerificationResult:
    """Tests for VerificationResult."""

    def test_result_creation(self):
        """Result should be creatable."""
        result = VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V0",
            message="All checks passed",
        )
        assert result.status == VerificationStatus.PASSED
        assert result.tier == "V0"

    def test_result_with_details(self):
        """Result should accept details."""
        result = VerificationResult(
            status=VerificationStatus.FAILED,
            tier="V1",
            message="Check failed",
            details={"reason": "Invalid range"},
        )
        assert result.details["reason"] == "Invalid range"


class TestSchemaVerifier:
    """Tests for Tier-0 Schema Verifier."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def verifier(self, engine):
        """Create schema verifier."""
        return SchemaVerifier(engine)

    def test_verifier_creation(self, verifier):
        """Verifier should be creatable."""
        assert verifier is not None
        assert verifier.tier == "V0"

    def test_valid_node_passes(self, verifier, engine):
        """Valid node should pass schema checks."""
        contract = Contract(
            id="contract_001",
            description="Valid contract",
            inputs={"x": "input"},
            outputs={"y": "output"},
            guarantees=[],
        )
        engine.add_node(contract)

        result = verifier.verify_node("contract_001")
        assert result.status == VerificationStatus.PASSED

    def test_checks_required_fields(self, verifier, engine):
        """Verifier should check required fields exist."""
        # All pydantic models enforce required fields at creation time
        # This test verifies the verifier handles existing nodes correctly
        contract = Contract(
            id="contract_001",
            description="Test",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)
        result = verifier.verify_node("contract_001")
        assert result.status == VerificationStatus.PASSED

    def test_invalid_edge_target_fails(self, verifier, engine):
        """Edge to non-existent node should fail."""
        contract = Contract(
            id="contract_001",
            description="Test",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Manually add invalid edge (bypassing validation)
        from src.hypergraph.models import Edge

        invalid_edge = Edge(
            id="edge_001",
            source_id="contract_001",
            target_id="nonexistent",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge_001"] = invalid_edge

        result = verifier.verify_edge("edge_001")
        assert result.status == VerificationStatus.FAILED


class TestRulesVerifier:
    """Tests for Tier-1 Rules Verifier."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def verifier(self, engine):
        """Create rules verifier."""
        return RulesVerifier(engine)

    def test_verifier_creation(self, verifier):
        """Verifier should be creatable."""
        assert verifier is not None
        assert verifier.tier == "V1"

    def test_load_within_range_passes(self, verifier, engine):
        """Load within safe range should pass."""
        contract = Contract(
            id="contract_001",
            description="Bracket design",
            inputs={"load": "50N"},
            outputs={"stress": "MPa"},
            guarantees=["max load 50N"],
            metadata={"load_kg": 5, "material": "aluminum"},
        )
        engine.add_node(contract)

        result = verifier.verify_node("contract_001")
        assert result.status == VerificationStatus.PASSED

    def test_excessive_load_fails(self, verifier, engine):
        """Excessive load should fail rules check."""
        contract = Contract(
            id="contract_001",
            description="Overloaded bracket",
            inputs={"load": "10000N"},
            outputs={"stress": "MPa"},
            guarantees=["max load 10000N"],
            metadata={"load_kg": 1000, "material": "aluminum"},
        )
        engine.add_node(contract)

        result = verifier.verify_node("contract_001")
        # Should flag as warning or failure for excessive load
        assert result.status in [VerificationStatus.WARNING, VerificationStatus.FAILED]

    def test_satisfied_contract_requires_evidence(self, verifier, engine):
        """Satisfied contract must have Evidence and no blocking Unknowns."""
        contract = Contract(
            id="contract_002",
            description="Satisfied contract",
            inputs={},
            outputs={},
            guarantees=["stress < 100 MPa"],
            status=ContractStatus.SATISFIED,
        )
        engine.add_node(contract)

        result = verifier.verify_node("contract_002")
        assert result.status == VerificationStatus.FAILED

        evidence = Evidence(
            id="evidence_001",
            description="FEA result",
            evidence_type="simulation",
            provenance="mech-verify:report_1",
            data={"max_stress": 80.0},
        )
        engine.add_node(evidence)
        engine.add_edge("evidence_001", "contract_002", EdgeType.VALIDATES)

        result = verifier.verify_node("contract_002")
        assert result.status in [VerificationStatus.PASSED, VerificationStatus.WARNING]

        blocking_unknown = Unknown(
            id="unknown_001",
            description="PMI missing",
            reason="No PMI provided",
            metadata={"blocking": True},
        )
        engine.add_node(blocking_unknown)
        engine.add_edge("unknown_001", "contract_002", EdgeType.DEPENDS_ON)

        result = verifier.verify_node("contract_002")
        assert result.status == VerificationStatus.FAILED


class TestVerificationPipeline:
    """Tests for VerificationPipeline."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def pipeline(self, engine):
        """Create verification pipeline."""
        return VerificationPipeline(engine)

    def test_pipeline_creation(self, pipeline):
        """Pipeline should be creatable."""
        assert pipeline is not None

    def test_pipeline_has_tiers(self, pipeline):
        """Pipeline should have all verification tiers."""
        tiers = pipeline.get_tiers()
        assert len(tiers) == 4
        tier_names = [t.tier for t in tiers]
        assert "V0" in tier_names
        assert "V1" in tier_names
        assert "V3-syntactic" in tier_names
        assert "V4-semantic" in tier_names

    def test_pipeline_runs_all_tiers(self, pipeline, engine):
        """Pipeline should run all verification tiers."""
        contract = Contract(
            id="contract_001",
            description="Test contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        results = pipeline.verify_node("contract_001")

        assert len(results) == 4
        tiers_run = {r.tier for r in results}
        assert "V0" in tiers_run
        assert "V1" in tiers_run
        assert "V3-syntactic" in tiers_run
        assert "V4-semantic" in tiers_run

    def test_pipeline_stops_on_failure(self, pipeline, engine):
        """Pipeline should optionally stop on first failure."""
        # Add invalid edge to cause V0 failure
        contract = Contract(
            id="contract_001",
            description="Test",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        from src.hypergraph.models import Edge

        invalid_edge = Edge(
            id="edge_001",
            source_id="contract_001",
            target_id="nonexistent",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge_001"] = invalid_edge

        results = pipeline.verify_edge("edge_001", stop_on_failure=True)

        # Should have stopped at V0
        assert len(results) == 1
        assert results[0].tier == "V0"
        assert results[0].status == VerificationStatus.FAILED

    def test_pipeline_verify_all(self, pipeline, engine):
        """Pipeline should verify entire graph."""
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
        )
        contract = Contract(
            id="contract_001",
            description="Child",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        summary = pipeline.verify_all()

        assert "nodes" in summary
        assert "edges" in summary
        assert "passed" in summary
        assert summary["passed"] is True  # All should pass

    def test_verify_all_node_ids_filter(self, pipeline, engine):
        """verify_all with node_ids only checks specified nodes."""
        c1 = Contract(
            id="contract_001",
            description="Included",
            inputs={},
            outputs={},
            guarantees=[],
        )
        c2 = Contract(
            id="contract_002",
            description="Excluded",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(c1)
        engine.add_node(c2)

        summary = pipeline.verify_all(node_ids={"contract_001"})

        assert "contract_001" in summary["nodes"]
        assert "contract_002" not in summary["nodes"]

    def test_verify_all_node_ids_none_includes_all(self, pipeline, engine):
        """verify_all with node_ids=None includes all nodes."""
        c1 = Contract(
            id="contract_001",
            description="A",
            inputs={},
            outputs={},
            guarantees=[],
        )
        c2 = Contract(
            id="contract_002",
            description="B",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(c1)
        engine.add_node(c2)

        summary = pipeline.verify_all(node_ids=None)
        assert "contract_001" in summary["nodes"]
        assert "contract_002" in summary["nodes"]

    def test_pipeline_get_summary(self, pipeline, engine):
        """Pipeline should provide verification summary."""
        contract = Contract(
            id="contract_001",
            description="Test",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        summary = pipeline.verify_all()

        assert "total_nodes" in summary
        assert "total_edges" in summary
        assert summary["total_nodes"] == 1
