"""Tests for Orchestrator coverage - process_intent, triggers, and edge cases."""

from unittest.mock import MagicMock, Mock, patch

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
    ContractStatus,
    Edge,
    EdgeType,
    Intent,
    NodeType,
    Requirement,
    RequirementStatus,
)
from src.hypergraph.store import HypergraphStore


class TestOrchestratorProcessIntent:
    """Tests for Orchestrator.process_intent() method."""

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
        mock.is_configured.return_value = True
        return mock

    def test_process_intent_creates_intent_node(self, engine, mock_llm, tmp_path):
        """process_intent should create Intent node."""
        # Create orchestrator with mocked agents
        with patch("src.agents.orchestrator.IntentParsingAgent") as mock_ipa:
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent") as mock_ada:
                with patch("src.agents.orchestrator.FeedbackController") as mock_fc:
                    # Configure mock agents
                    mock_agent = MagicMock()
                    mock_agent.can_handle.return_value = False
                    mock_ipa.return_value = mock_agent
                    mock_ada.return_value = mock_agent
                    mock_fc.return_value = mock_agent

                    orchestrator = Orchestrator(engine, mock_llm)
                    result = orchestrator.process_intent("Design a bracket")

                    assert result.success is True
                    assert "intent_id" in result.details
                    # Verify intent node was created
                    intent_id = result.details["intent_id"]
                    intent = engine.get_node(intent_id)
                    assert intent is not None
                    assert intent.node_type == NodeType.INTENT

    def test_process_intent_routes_trigger_to_agents(self, engine, mock_llm):
        """process_intent should route INTENT_CREATED trigger to agents."""
        with patch("src.agents.orchestrator.IntentParsingAgent") as mock_ipa:
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent") as mock_ada:
                with patch("src.agents.orchestrator.FeedbackController") as mock_fc:
                    mock_agent = MagicMock()
                    mock_agent.can_handle.return_value = True
                    mock_agent.execute.return_value = AgentResult(
                        success=True, mutation=None, message="Done", next_triggers=[]
                    )
                    mock_ipa.return_value = mock_agent
                    mock_ada.return_value = MagicMock(
                        can_handle=Mock(return_value=False)
                    )
                    mock_fc.return_value = MagicMock(
                        can_handle=Mock(return_value=False)
                    )

                    orchestrator = Orchestrator(engine, mock_llm)
                    orchestrator.process_intent("Test intent")

                    # Agent should have been called
                    assert mock_agent.execute.called

    def test_process_intent_processes_follow_up_triggers(self, engine, mock_llm):
        """process_intent should process follow-up triggers from agents."""
        with patch("src.agents.orchestrator.IntentParsingAgent") as mock_ipa:
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent") as mock_ada:
                with patch("src.agents.orchestrator.FeedbackController") as mock_fc:
                    # First agent returns a follow-up trigger
                    follow_up = Trigger(
                        trigger_type=TriggerType.CONTRACT_CREATED,
                        node_id="contract_001",
                    )
                    first_result = AgentResult(
                        success=True,
                        mutation=None,
                        message="Done",
                        next_triggers=[follow_up],
                    )
                    second_result = AgentResult(
                        success=True, mutation=None, message="Done", next_triggers=[]
                    )

                    mock_agent1 = MagicMock()
                    mock_agent1.can_handle.side_effect = (
                        lambda t: t.trigger_type == TriggerType.INTENT_CREATED
                    )
                    mock_agent1.execute.return_value = first_result

                    mock_agent2 = MagicMock()
                    mock_agent2.can_handle.side_effect = (
                        lambda t: t.trigger_type == TriggerType.CONTRACT_CREATED
                    )
                    mock_agent2.execute.return_value = second_result

                    mock_ipa.return_value = mock_agent1
                    mock_ada.return_value = mock_agent2
                    mock_fc.return_value = MagicMock(
                        can_handle=Mock(return_value=False)
                    )

                    orchestrator = Orchestrator(engine, mock_llm)
                    orchestrator.process_intent("Test intent")

                    # Both agents should have been executed
                    assert mock_agent1.execute.called
                    # Follow-up trigger should also be processed
                    assert mock_agent2.can_handle.called

    def test_process_intent_computes_confidence(self, engine, mock_llm):
        """process_intent should compute and return confidence."""
        with patch("src.agents.orchestrator.IntentParsingAgent") as mock_ipa:
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent") as mock_ada:
                with patch("src.agents.orchestrator.FeedbackController") as mock_fc:
                    mock_agent = MagicMock()
                    mock_agent.can_handle.return_value = False
                    mock_ipa.return_value = mock_agent
                    mock_ada.return_value = mock_agent
                    mock_fc.return_value = mock_agent

                    orchestrator = Orchestrator(engine, mock_llm)
                    result = orchestrator.process_intent("Test intent")

                    assert "confidence" in result.details
                    assert isinstance(result.details["confidence"], float)


class TestOrchestratorValidateAndCommit:
    """Tests for Orchestrator.validate_and_commit() with rollback."""

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
        """Create orchestrator."""
        with patch("src.agents.orchestrator.IntentParsingAgent"):
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent"):
                with patch("src.agents.orchestrator.FeedbackController"):
                    return Orchestrator(engine, mock_llm)

    def test_validate_and_commit_with_node_updates(self, orchestrator, engine):
        """validate_and_commit should apply node updates."""
        # First add a node
        contract = Contract(
            id="contract_001",
            description="Original description",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Create mutation that updates the node
        mutation = HypergraphMutation(
            nodes_to_add=[],
            edges_to_add=[],
            nodes_to_update={"contract_001": {"description": "Updated description"}},
            description="Update contract",
        )

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is True

        # Verify update was applied
        updated = engine.get_node("contract_001")
        assert updated.description == "Updated description"

    def test_validate_and_commit_with_node_removal(self, orchestrator, engine):
        """validate_and_commit should remove nodes."""
        contract = Contract(
            id="contract_001",
            description="To be removed",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        mutation = HypergraphMutation(
            nodes_to_add=[],
            edges_to_add=[],
            nodes_to_update={},
            nodes_to_remove=["contract_001"],
            description="Remove contract",
        )

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is True

        # Verify node was removed
        assert engine.get_node("contract_001") is None

    def test_validate_and_commit_with_edge_removal(self, orchestrator, engine):
        """validate_and_commit should remove edges."""
        parent = Intent(id="intent_001", description="Parent", goal="Goal")
        child = Contract(
            id="contract_001",
            description="Child",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(parent)
        engine.add_node(child)
        edge_id = engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        mutation = HypergraphMutation(
            nodes_to_add=[],
            edges_to_add=[],
            nodes_to_update={},
            edges_to_remove=[edge_id],
            description="Remove edge",
        )

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is True

        # Verify edge was removed
        assert edge_id not in engine.edges

    def test_validate_and_commit_rollback_on_failure(self, orchestrator, engine):
        """validate_and_commit should rollback on verification failure."""
        # Create a valid node first
        contract = Contract(
            id="contract_001",
            description="Original",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Create mutation with invalid edge (nodes don't exist)
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

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is False

        # Original node should still exist
        assert engine.get_node("contract_001") is not None

    def test_validate_and_commit_fires_contract_created_trigger(
        self, orchestrator, engine
    ):
        """validate_and_commit should fire CONTRACT_CREATED for new contracts."""
        contract = Contract(
            id="contract_001",
            description="New contract",
            inputs={},
            outputs={},
            guarantees=[],
        )

        mutation = HypergraphMutation(
            nodes_to_add=[contract],
            edges_to_add=[],
            nodes_to_update={},
            description="Add contract",
        )

        # Track if CONTRACT_CREATED was routed
        original_route = orchestrator.route_trigger

        triggers_routed = []

        def track_route(trigger):
            triggers_routed.append(trigger.trigger_type)
            return original_route(trigger)

        orchestrator.route_trigger = track_route

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is True
        assert TriggerType.CONTRACT_CREATED in triggers_routed


class TestOrchestratorFormallyVerifiedTrigger:
    """Tests for FORMALLY_VERIFIED trigger firing."""

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
        mock.complete_json.return_value = {"issues": []}
        mock.is_configured.return_value = True
        return mock

    @pytest.fixture
    def orchestrator(self, engine, mock_llm):
        """Create orchestrator."""
        with patch("src.agents.orchestrator.IntentParsingAgent"):
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent"):
                with patch("src.agents.orchestrator.FeedbackController"):
                    return Orchestrator(engine, mock_llm)

    def test_formally_verified_fires_when_all_requirements_validated(
        self, orchestrator, engine
    ):
        """FORMALLY_VERIFIED should fire when all requirements are validated."""
        # Add an intent first
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        # Create validated requirement
        req = Requirement(
            id="req_001",
            description="Requirement",
            statement="System SHALL...",
            status=RequirementStatus.VALIDATED,
        )

        # Edge from requirement to intent
        edge = Edge(
            id="edge_001",
            source_id="req_001",
            target_id="intent_001",
            edge_type=EdgeType.DERIVES_FROM,
        )

        mutation = HypergraphMutation(
            nodes_to_add=[req],
            edges_to_add=[edge],
            nodes_to_update={},
            description="Add validated requirement",
        )

        triggers_routed = []
        original_route = orchestrator.route_trigger

        def track_route(trigger):
            triggers_routed.append(trigger.trigger_type)
            return original_route(trigger)

        orchestrator.route_trigger = track_route

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is True

        # FORMALLY_VERIFIED should have been fired
        assert TriggerType.FORMALLY_VERIFIED in triggers_routed

    def test_formally_verified_not_fired_when_requirements_not_validated(
        self, orchestrator, engine
    ):
        """FORMALLY_VERIFIED should NOT fire when requirements not validated."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        # Create non-validated requirement
        req = Requirement(
            id="req_001",
            description="Requirement",
            statement="System SHALL...",
            status=RequirementStatus.DRAFT,  # Not validated
        )

        edge = Edge(
            id="edge_001",
            source_id="req_001",
            target_id="intent_001",
            edge_type=EdgeType.DERIVES_FROM,
        )

        mutation = HypergraphMutation(
            nodes_to_add=[req],
            edges_to_add=[edge],
            nodes_to_update={},
            description="Add draft requirement",
        )

        triggers_routed = []
        original_route = orchestrator.route_trigger

        def track_route(trigger):
            triggers_routed.append(trigger.trigger_type)
            return original_route(trigger)

        orchestrator.route_trigger = track_route

        success, _ = orchestrator.validate_and_commit(mutation)
        assert success is True

        # FORMALLY_VERIFIED should NOT have been fired
        assert TriggerType.FORMALLY_VERIFIED not in triggers_routed


class TestOrchestratorCheckAndFireRequirementSatisfied:
    """Tests for _check_and_fire_requirement_satisfied method."""

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
        """Create orchestrator."""
        with patch("src.agents.orchestrator.IntentParsingAgent"):
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent"):
                with patch("src.agents.orchestrator.FeedbackController"):
                    return Orchestrator(engine, mock_llm)

    def test_check_requirement_satisfied_with_nonexistent_node(
        self, orchestrator, engine
    ):
        """_check_and_fire_requirement_satisfied should handle nonexistent node."""
        # Should not raise
        orchestrator._check_and_fire_requirement_satisfied("nonexistent_id")

    def test_check_requirement_satisfied_with_non_requirement_node(
        self, orchestrator, engine
    ):
        """_check_and_fire_requirement_satisfied should ignore non-requirement nodes."""
        contract = Contract(
            id="contract_001",
            description="Test",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Should not raise, just return early
        orchestrator._check_and_fire_requirement_satisfied("contract_001")

    def test_check_requirement_satisfied_with_no_contracts(self, orchestrator, engine):
        """_check_and_fire_requirement_satisfied should handle requirement with no contracts."""
        req = Requirement(
            id="req_001",
            description="Test requirement",
            statement="System SHALL...",
        )
        engine.add_node(req)

        # Should not raise, no contracts satisfy this requirement
        orchestrator._check_and_fire_requirement_satisfied("req_001")

    def test_check_requirement_satisfied_fires_when_all_contracts_satisfied(
        self, orchestrator, engine
    ):
        """_check_and_fire_requirement_satisfied should fire trigger when all satisfied."""
        # Add requirement
        req = Requirement(
            id="req_001",
            description="Test requirement",
            statement="System SHALL...",
        )
        engine.add_node(req)

        # Add satisfied contract with SATISFIES edge
        contract = Contract(
            id="contract_001",
            description="Test contract",
            inputs={},
            outputs={},
            guarantees=[],
            status=ContractStatus.SATISFIED,
        )
        engine.add_node(contract)
        engine.add_edge("contract_001", "req_001", EdgeType.SATISFIES)

        triggers_routed = []

        def track_route(trigger):
            triggers_routed.append(trigger.trigger_type)
            return []

        orchestrator.route_trigger = track_route

        orchestrator._check_and_fire_requirement_satisfied("req_001")

        # REQUIREMENT_SATISFIED should have been fired
        assert TriggerType.REQUIREMENT_SATISFIED in triggers_routed

    def test_check_requirement_satisfied_not_fired_when_contracts_not_satisfied(
        self, orchestrator, engine
    ):
        """_check_and_fire_requirement_satisfied should not fire when contracts not satisfied."""
        req = Requirement(
            id="req_001",
            description="Test requirement",
            statement="System SHALL...",
        )
        engine.add_node(req)

        # Add unsatisfied contract
        contract = Contract(
            id="contract_001",
            description="Test contract",
            inputs={},
            outputs={},
            guarantees=[],
            status=ContractStatus.DRAFT,  # Not satisfied
        )
        engine.add_node(contract)
        engine.add_edge("contract_001", "req_001", EdgeType.SATISFIES)

        triggers_routed = []

        def track_route(trigger):
            triggers_routed.append(trigger.trigger_type)
            return []

        orchestrator.route_trigger = track_route

        orchestrator._check_and_fire_requirement_satisfied("req_001")

        # REQUIREMENT_SATISFIED should NOT have been fired
        assert TriggerType.REQUIREMENT_SATISFIED not in triggers_routed


class TestOrchestratorGetSummary:
    """Tests for Orchestrator._get_summary() method."""

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
        return mock

    @pytest.fixture
    def orchestrator(self, engine, mock_llm):
        """Create orchestrator."""
        with patch("src.agents.orchestrator.IntentParsingAgent"):
            with patch("src.agents.orchestrator.AmbiguityDetectionAgent"):
                with patch("src.agents.orchestrator.FeedbackController"):
                    return Orchestrator(engine, mock_llm)

    def test_get_summary_counts_nodes_by_type(self, orchestrator, engine):
        """_get_summary should count nodes by type."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        contract1 = Contract(
            id="contract_001", description="C1", inputs={}, outputs={}, guarantees=[]
        )
        contract2 = Contract(
            id="contract_002", description="C2", inputs={}, outputs={}, guarantees=[]
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)

        summary = orchestrator._get_summary()

        assert summary["total_nodes"] == 3
        assert summary["node_counts"]["intent"] == 1
        assert summary["node_counts"]["contract"] == 2

    def test_get_summary_counts_edges(self, orchestrator, engine):
        """_get_summary should count edges."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        contract = Contract(
            id="contract_001", description="C1", inputs={}, outputs={}, guarantees=[]
        )

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        summary = orchestrator._get_summary()

        assert summary["total_edges"] == 1
