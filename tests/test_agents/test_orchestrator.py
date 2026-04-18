"""Tests for orchestrator and agent system."""

from unittest.mock import Mock

import pytest

from src.agents.base import (
    AgentResult,
    HypergraphMutation,
    Trigger,
    TriggerType,
)
from src.agents.llm import LLMClient
from src.agents.orchestrator import Orchestrator
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    Edge,
    EdgeType,
    Intent,
)
from src.hypergraph.store import HypergraphStore


class TestHypergraphMutation:
    """Tests for HypergraphMutation."""

    def test_mutation_creation(self):
        """Mutation should be creatable."""
        mutation = HypergraphMutation(
            nodes_to_add=[],
            edges_to_add=[],
            nodes_to_update={},
            description="Test mutation",
        )
        assert mutation.description == "Test mutation"

    def test_mutation_with_nodes(self):
        """Mutation should track nodes to add."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        mutation = HypergraphMutation(
            nodes_to_add=[intent],
            edges_to_add=[],
            nodes_to_update={},
            description="Add intent",
        )
        assert len(mutation.nodes_to_add) == 1


class TestAgentResult:
    """Tests for AgentResult."""

    def test_success_result(self):
        """Success result should be creatable."""
        result = AgentResult(
            success=True,
            mutation=None,
            message="Task completed",
        )
        assert result.success is True

    def test_result_with_mutation(self):
        """Result should include mutation."""
        mutation = HypergraphMutation(
            nodes_to_add=[],
            edges_to_add=[],
            nodes_to_update={},
            description="Test",
        )
        result = AgentResult(
            success=True,
            mutation=mutation,
            message="Done",
        )
        assert result.mutation is not None


class TestOrchestrator:
    """Tests for Orchestrator."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        mock = Mock(spec=LLMClient)
        mock.complete.return_value = "Mock response"
        return mock

    @pytest.fixture
    def orchestrator(self, engine, mock_llm):
        """Create orchestrator with mock LLM."""
        return Orchestrator(engine, mock_llm)

    def test_orchestrator_creation(self, orchestrator):
        """Orchestrator should be creatable."""
        assert orchestrator is not None

    def test_orchestrator_with_default_agents(self, orchestrator):
        """Orchestrator should register Phase 2+3 agents by default."""
        agents = orchestrator.list_agents()
        assert len(agents) == 4
        agent_names = [a.name for a in agents]
        assert "IntentParsingAgent" in agent_names
        assert "AmbiguityDetectionAgent" in agent_names
        assert "FeedbackController" in agent_names
        assert "MechanicalVerificationAgent" in agent_names

    def test_orchestrator_validates_mutations(self, orchestrator, engine):
        """Orchestrator should validate mutations before committing."""
        mutation = HypergraphMutation(
            nodes_to_add=[
                Contract(
                    id="contract_001",
                    description="Test",
                    inputs={},
                    outputs={},
                    guarantees=[],
                )
            ],
            edges_to_add=[],
            nodes_to_update={},
            description="Test mutation",
        )

        success, results = orchestrator.validate_and_commit(mutation)
        assert success is True

    def test_orchestrator_rejects_invalid_mutations(self, orchestrator, engine):
        """Orchestrator should reject invalid mutations."""
        mutation = HypergraphMutation(
            nodes_to_add=[],
            edges_to_add=[
                Edge(
                    id="edge_001",
                    source_id="nonexistent_1",
                    target_id="nonexistent_2",
                    edge_type=EdgeType.HAS_CHILD,
                )
            ],
            nodes_to_update={},
            description="Invalid mutation",
        )

        success, results = orchestrator.validate_and_commit(mutation)
        assert success is False

    def test_orchestrator_routes_intent_created_to_agent(self, orchestrator, engine):
        """Orchestrator should route INTENT_CREATED to IntentParsingAgent."""
        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
        )
        engine.add_node(intent)

        trigger = Trigger(
            trigger_type=TriggerType.INTENT_CREATED,
            node_id="intent_001",
            data={"description": "Test intent"},
        )

        # Should route to IntentParsingAgent
        results = orchestrator.route_trigger(trigger)
        assert len(results) == 1
