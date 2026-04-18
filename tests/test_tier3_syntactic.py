"""Integration tests for SyntacticVerifier (V3 tier)."""

from unittest.mock import Mock

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Edge,
    EdgeType,
    Intent,
    Node,
    NodeType,
    Requirement,
)
from src.hypergraph.store import HypergraphStore
from src.verification.base import VerificationStatus
from src.verification.pipeline import VerificationPipeline
from src.verification.tier3_syntactic import SyntacticVerifier


@pytest.fixture
def engine(tmp_path):
    """Create test engine."""
    store = HypergraphStore(str(tmp_path / "test.json"))
    return HypergraphEngine(store)


@pytest.fixture
def mock_llm():
    """Create mock LLM that returns no ambiguity issues."""
    llm = Mock()
    # Return empty IEEE830Analysis (no issues)
    llm.complete_json.return_value = {"issues": []}
    return llm


@pytest.fixture
def verifier(engine, mock_llm):
    """Create SyntacticVerifier with mock LLM."""
    return SyntacticVerifier(engine, llm=mock_llm)


class TestSyntacticVerifierBasics:
    """Basic SyntacticVerifier tests."""

    def test_tier_name(self, verifier):
        """Verifier reports correct tier name."""
        assert verifier.tier == "V3-syntactic"

    def test_cost(self, verifier):
        """Verifier reports moderate cost."""
        assert verifier.cost == 0.3


class TestVerifyNodeSchemaErrors:
    """Tests for schema error detection (FAILED status)."""

    def test_missing_required_field_returns_failed(self, engine, verifier):
        """Requirement with empty statement returns FAILED."""
        req = Requirement(
            id="req-001",
            description="Test requirement",
            statement="placeholder",
        )
        # Bypass Pydantic to set empty statement
        object.__setattr__(req, "statement", "")
        engine.nodes["req-001"] = req

        result = verifier.verify_node("req-001")

        assert result.status == VerificationStatus.FAILED
        assert result.tier == "V3-syntactic"
        assert "schema error" in result.message.lower()
        assert result.node_id == "req-001"

    def test_type_error_returns_failed(self, engine, verifier):
        """Node with wrong type returns FAILED."""
        node = Node(
            id="node-001",
            node_type=NodeType.CONTRACT,
            description="Test node",
            confidence=0.5,
        )
        # Bypass validation to set wrong type
        object.__setattr__(node, "confidence", "high")
        engine.nodes["node-001"] = node

        result = verifier.verify_node("node-001")

        assert result.status == VerificationStatus.FAILED


class TestVerifyNodeWarnings:
    """Tests for IEEE 830 warnings (WARNING status)."""

    def test_missing_verification_method_returns_warning(self, engine, verifier):
        """Requirement without verification_method returns WARNING."""
        req = Requirement(
            id="req-002",
            description="Test requirement",
            statement="The system SHALL work properly",
            verification_method="",  # Empty but valid field
        )
        engine.add_node(req)

        # Add DERIVES_FROM edge so traceability passes
        intent = Intent(id="intent-001", description="Test intent", goal="Test goal")
        engine.add_node(intent)
        engine.add_edge("req-002", "intent-001", EdgeType.DERIVES_FROM)

        result = verifier.verify_node("req-002")

        # Should be WARNING (IEEE 830 issue), not FAILED
        assert result.status == VerificationStatus.WARNING
        assert result.tier == "V3-syntactic"
        assert "warning" in result.message.lower()

    def test_missing_traceability_returns_warning(self, engine, verifier):
        """Orphan requirement returns WARNING for traceability."""
        req = Requirement(
            id="req-003",
            description="Orphan requirement",
            statement="The system SHALL be orphan",
            verification_method="TEST",  # Valid method
        )
        engine.add_node(req)

        result = verifier.verify_node("req-003")

        assert result.status == VerificationStatus.WARNING
        assert "warning" in result.message.lower()


class TestVerifyNodePassing:
    """Tests for passing verification."""

    def test_valid_requirement_passes(self, engine, verifier):
        """Requirement with all fields and traceability passes."""
        intent = Intent(id="intent-001", description="Root intent", goal="Design goal")
        req = Requirement(
            id="req-004",
            description="Valid requirement",
            statement="The system SHALL verify correctly",
            verification_method="TEST",
        )

        engine.add_node(intent)
        engine.add_node(req)
        engine.add_edge("req-004", "intent-001", EdgeType.DERIVES_FROM)

        result = verifier.verify_node("req-004")

        assert result.status == VerificationStatus.PASSED
        assert result.tier == "V3-syntactic"
        assert result.node_id == "req-004"

    def test_node_not_found_returns_failed(self, verifier):
        """Non-existent node returns FAILED."""
        result = verifier.verify_node("nonexistent")

        assert result.status == VerificationStatus.FAILED
        assert "not found" in result.message.lower()


class TestVerifyEdge:
    """Tests for edge verification."""

    def test_dangling_edge_returns_failed(self, engine, verifier):
        """Edge with missing target returns FAILED."""
        source = Node(id="source-001", node_type=NodeType.INTENT, description="Source")
        engine.nodes["source-001"] = source

        edge = Edge(
            id="edge-001",
            source_id="source-001",
            target_id="missing-target",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge-001"] = edge

        result = verifier.verify_edge("edge-001")

        assert result.status == VerificationStatus.FAILED
        assert result.tier == "V3-syntactic"
        assert result.edge_id == "edge-001"

    def test_valid_edge_passes(self, engine, verifier):
        """Edge with existing nodes passes."""
        source = Node(id="src-001", node_type=NodeType.INTENT, description="Source")
        target = Node(id="tgt-001", node_type=NodeType.CONTRACT, description="Target")
        engine.nodes["src-001"] = source
        engine.nodes["tgt-001"] = target

        edge = Edge(
            id="edge-002",
            source_id="src-001",
            target_id="tgt-001",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge-002"] = edge

        result = verifier.verify_edge("edge-002")

        assert result.status == VerificationStatus.PASSED

    def test_edge_not_found_returns_failed(self, verifier):
        """Non-existent edge returns FAILED."""
        result = verifier.verify_edge("nonexistent-edge")

        assert result.status == VerificationStatus.FAILED
        assert "not found" in result.message.lower()


class TestPipelineIntegration:
    """Tests for pipeline integration."""

    def test_pipeline_includes_syntactic_verifier(self, engine, mock_llm):
        """Pipeline contains V3-syntactic tier."""
        pipeline = VerificationPipeline(engine, llm=mock_llm)
        tiers = [v.tier for v in pipeline.get_tiers()]

        assert "V3-syntactic" in tiers

    def test_pipeline_tier_order(self, engine, mock_llm):
        """Tiers are ordered V0 -> V1 -> V3-syntactic -> V4-semantic."""
        pipeline = VerificationPipeline(engine, llm=mock_llm)
        tiers = [v.tier for v in pipeline.get_tiers()]

        assert tiers == ["V0", "V1", "V3-syntactic", "V4-semantic"]

    def test_verify_all_includes_syntactic_results(self, engine, mock_llm):
        """verify_all() includes V3-syntactic results."""
        req = Requirement(
            id="req-pipe",
            description="Pipeline test",
            statement="The system SHALL test pipeline",
            verification_method="TEST",
        )
        engine.add_node(req)

        pipeline = VerificationPipeline(engine, llm=mock_llm)
        results = pipeline.verify_all()

        # Check that node results include V3-syntactic tier
        node_tiers = [r["tier"] for r in results["nodes"]["req-pipe"]]
        assert "V3-syntactic" in node_tiers
