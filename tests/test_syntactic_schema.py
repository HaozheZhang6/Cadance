"""Tests for syntactic schema and reference validation (SYN-05, SYN-06, SYN-07)."""

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    Edge,
    EdgeType,
    GoalNode,
    Intent,
    Node,
    NodeType,
    Requirement,
)
from src.hypergraph.store import HypergraphStore
from src.verification.base import VerificationStatus
from src.verification.syntactic.references import check_dangling_edges
from src.verification.syntactic.schema import (
    check_required_fields,
    check_type_correctness,
)


@pytest.fixture
def engine(tmp_path):
    """Create a test engine."""
    store = HypergraphStore(str(tmp_path / "test.json"))
    return HypergraphEngine(store)


# =============================================================================
# SYN-05: Required Field Validation
# =============================================================================


class TestRequiredFields:
    """Tests for check_required_fields (SYN-05)."""

    def test_requirement_missing_statement_fails(self, engine):
        """Requirement without statement should fail validation."""
        # Create requirement with empty statement via object_setattr bypass
        req = Requirement(
            id="req_1",
            description="Test requirement",
            statement="placeholder",
        )
        # Bypass validation to set empty statement
        object.__setattr__(req, "statement", "")
        engine.nodes["req_1"] = req

        results = check_required_fields(req, engine)

        assert len(results) >= 1
        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 1
        assert "statement" in failed[0].message.lower()
        assert failed[0].node_id == "req_1"
        assert failed[0].tier == "syntactic"

    def test_goal_missing_required_fields_fails(self, engine):
        """GoalNode without goal_type, refinement_type, agent should fail."""
        # Create goal with empty required fields via bypass
        goal = GoalNode(
            id="goal_1",
            description="Test goal",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        # Bypass to set empty values
        object.__setattr__(goal, "goal_type", "")
        object.__setattr__(goal, "agent", "")
        engine.nodes["goal_1"] = goal

        results = check_required_fields(goal, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 1
        # Should catch at least one missing field
        messages = " ".join(r.message.lower() for r in failed)
        assert "goal_type" in messages or "agent" in messages

    def test_valid_requirement_passes(self, engine):
        """Requirement with all required fields should pass."""
        req = Requirement(
            id="req_1",
            description="Test requirement",
            statement="The system SHALL provide user authentication.",
        )
        engine.nodes["req_1"] = req

        results = check_required_fields(req, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0

    def test_valid_goal_passes(self, engine):
        """GoalNode with all required fields should pass."""
        goal = GoalNode(
            id="goal_1",
            description="Test goal",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        engine.nodes["goal_1"] = goal

        results = check_required_fields(goal, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0

    def test_contract_with_defaults_passes(self, engine):
        """Contract with defaults should pass (no strict required fields)."""
        contract = Contract(
            id="contract_1",
            description="Test contract",
        )
        engine.nodes["contract_1"] = contract

        results = check_required_fields(contract, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0

    def test_intent_passes(self, engine):
        """Intent with required fields should pass."""
        intent = Intent(
            id="intent_1",
            description="User intent",
            goal="Design a bracket",
        )
        engine.nodes["intent_1"] = intent

        results = check_required_fields(intent, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0


# =============================================================================
# SYN-06: Type Correctness
# =============================================================================


class TestTypeCorrectness:
    """Tests for check_type_correctness (SYN-06)."""

    def test_confidence_type_error_fails(self, engine):
        """Node with wrong confidence type should fail."""
        node = Node(
            id="node_1",
            node_type=NodeType.CONTRACT,
            description="Test node",
            confidence=0.5,
        )
        # Bypass validation to set wrong type
        object.__setattr__(node, "confidence", "high")
        engine.nodes["node_1"] = node

        results = check_type_correctness(node, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 1
        assert "confidence" in failed[0].message.lower()
        assert (
            "float" in failed[0].message.lower() or "type" in failed[0].message.lower()
        )

    def test_valid_types_passes(self, engine):
        """Node with correct types should pass."""
        node = Node(
            id="node_1",
            node_type=NodeType.CONTRACT,
            description="Test node",
            confidence=0.8,
        )
        engine.nodes["node_1"] = node

        results = check_type_correctness(node, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0

    def test_list_field_type_error_fails(self, engine):
        """Node with wrong list field type should fail."""
        req = Requirement(
            id="req_1",
            description="Test",
            statement="Test statement",
        )
        # Bypass to set wrong type for list field
        object.__setattr__(req, "assumptions", "not a list")
        engine.nodes["req_1"] = req

        results = check_type_correctness(req, engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 1


# =============================================================================
# SYN-07: Dangling Edges
# =============================================================================


class TestDanglingEdges:
    """Tests for check_dangling_edges (SYN-07)."""

    def test_dangling_edge_source_fails(self, engine):
        """Edge with missing source node should fail."""
        # Add only target node
        target = Node(
            id="target_1",
            node_type=NodeType.CONTRACT,
            description="Target node",
        )
        engine.nodes["target_1"] = target

        # Create edge with non-existent source
        edge = Edge(
            id="edge_1",
            source_id="missing_source",
            target_id="target_1",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge_1"] = edge

        results = check_dangling_edges(engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 1
        assert "source" in failed[0].message.lower()
        assert "missing_source" in failed[0].message
        assert failed[0].edge_id == "edge_1"
        assert failed[0].tier == "syntactic"

    def test_dangling_edge_target_fails(self, engine):
        """Edge with missing target node should fail."""
        # Add only source node
        source = Node(
            id="source_1",
            node_type=NodeType.CONTRACT,
            description="Source node",
        )
        engine.nodes["source_1"] = source

        # Create edge with non-existent target
        edge = Edge(
            id="edge_2",
            source_id="source_1",
            target_id="missing_target",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge_2"] = edge

        results = check_dangling_edges(engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 1
        assert "target" in failed[0].message.lower()
        assert "missing_target" in failed[0].message
        assert failed[0].edge_id == "edge_2"

    def test_dangling_both_source_and_target_fails(self, engine):
        """Edge with both missing source and target should fail twice."""
        # No nodes, just edge
        edge = Edge(
            id="edge_3",
            source_id="missing_source",
            target_id="missing_target",
            edge_type=EdgeType.DEPENDS_ON,
        )
        engine.edges["edge_3"] = edge

        results = check_dangling_edges(engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) >= 2  # One for source, one for target

    def test_valid_edge_passes(self, engine):
        """Edge with existing source and target should pass."""
        # Add both nodes
        source = Node(
            id="source_1",
            node_type=NodeType.INTENT,
            description="Source",
        )
        target = Node(
            id="target_1",
            node_type=NodeType.CONTRACT,
            description="Target",
        )
        engine.nodes["source_1"] = source
        engine.nodes["target_1"] = target

        # Create valid edge
        edge = Edge(
            id="edge_4",
            source_id="source_1",
            target_id="target_1",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["edge_4"] = edge

        results = check_dangling_edges(engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0

    def test_multiple_edges_mixed_validity(self, engine):
        """Multiple edges - some valid, some dangling."""
        # Add nodes
        node1 = Node(id="n1", node_type=NodeType.CONTRACT, description="N1")
        node2 = Node(id="n2", node_type=NodeType.CONTRACT, description="N2")
        engine.nodes["n1"] = node1
        engine.nodes["n2"] = node2

        # Valid edge
        valid_edge = Edge(
            id="e_valid",
            source_id="n1",
            target_id="n2",
            edge_type=EdgeType.DEPENDS_ON,
        )
        # Dangling edge
        dangling_edge = Edge(
            id="e_dangling",
            source_id="n1",
            target_id="nonexistent",
            edge_type=EdgeType.HAS_CHILD,
        )
        engine.edges["e_valid"] = valid_edge
        engine.edges["e_dangling"] = dangling_edge

        results = check_dangling_edges(engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 1
        assert failed[0].edge_id == "e_dangling"

    def test_empty_graph_passes(self, engine):
        """Empty graph (no edges) should pass."""
        results = check_dangling_edges(engine)

        failed = [r for r in results if r.status == VerificationStatus.FAILED]
        assert len(failed) == 0
