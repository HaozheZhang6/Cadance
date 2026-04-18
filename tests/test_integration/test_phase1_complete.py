"""Integration test for Phase 1: Foundation.

Tests all new node types, edge types, Contract fields, orchestrator with no agents.
"""

from src.agents.base import TriggerType
from src.agents.llm import MockLLMClient
from src.agents.orchestrator import Orchestrator
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    ContractParty,
    EdgeType,
    GoalNode,
    NodeType,
    ObstacleNode,
    SoftgoalNode,
    SpecificationNode,
    SpecParameter,
)
from src.hypergraph.store import HypergraphStore


def test_all_new_node_types_in_graph(tmp_path):
    """Test creating all new node types in a single graph."""
    store = HypergraphStore(tmp_path / "test.json")
    engine = HypergraphEngine(store)

    # Create GoalNode
    goal = GoalNode(
        id="goal_001",
        description="Achieve stable temperature",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="IntentRefinementAgent",
        obstacle_ids=["obs_001"],
        tbd_fields=[],
    )
    engine.add_node(goal)

    # Create ObstacleNode
    obstacle = ObstacleNode(
        id="obs_001",
        description="Sensor failure",
        severity="HIGH",
        mitigated_by=["req_001"],
    )
    engine.add_node(obstacle)

    # Create SoftgoalNode
    softgoal = SoftgoalNode(
        id="sg_001",
        description="System reliability",
        name="Reliability",
        type="QUALITY_ATTRIBUTE",
        satisfaction_level="WEAKLY_SATISFIED",
    )
    engine.add_node(softgoal)

    # Create SpecificationNode with parameters
    param = SpecParameter(
        name="temperature",
        value=25.0,
        unit="C",
        tolerance="+-2",
        confidence=0.9,
    )
    spec = SpecificationNode(
        id="spec_001",
        description="Temperature specification",
        derives_from=["goal_001"],
        parameters=[param],
        design_decisions=[
            {
                "decision": "Use PID controller",
                "rationale": "Better accuracy",
                "alternatives": "Bang-bang controller",
            }
        ],
        verification_criteria=["Measure steady-state error"],
        formal_repr="And(temp >= 23.0, temp <= 27.0)",
    )
    engine.add_node(spec)

    # Create Contract with parties
    party1 = ContractParty(
        node_id="spec_001", role="provider", variables=["temperature"]
    )
    party2 = ContractParty(node_id="sensor_001", role="consumer", variables=["reading"])
    contract = Contract(
        id="contract_001",
        description="Temperature sensor interface",
        parties=[party1, party2],
        assumptions=["Sensor calibrated", "Ambient conditions stable"],
        guarantees=["Reading within +-0.5C of true value"],
        formal_repr="Implies(calibrated, abs(reading - temp) <= 0.5)",
        valid_regimes=["normal", "fault_tolerant"],
    )
    engine.add_node(contract)

    # Verify all nodes exist
    assert engine.get_node("goal_001") is not None
    assert engine.get_node("obs_001") is not None
    assert engine.get_node("sg_001") is not None
    assert engine.get_node("spec_001") is not None
    assert engine.get_node("contract_001") is not None

    # Verify node types
    assert isinstance(engine.get_node("goal_001"), GoalNode)
    assert isinstance(engine.get_node("obs_001"), ObstacleNode)
    assert isinstance(engine.get_node("sg_001"), SoftgoalNode)
    assert isinstance(engine.get_node("spec_001"), SpecificationNode)
    assert isinstance(engine.get_node("contract_001"), Contract)


def test_new_edge_types_in_graph(tmp_path):
    """Test creating new edge types."""
    store = HypergraphStore(tmp_path / "test.json")
    engine = HypergraphEngine(store)

    # Create nodes
    goal1 = GoalNode(
        id="goal_parent",
        description="Parent goal",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="TestAgent",
    )
    goal2 = GoalNode(
        id="goal_child",
        description="Child goal",
        goal_type="ACHIEVE",
        refinement_type="OR",
        agent="TestAgent",
    )
    obstacle = ObstacleNode(
        id="obs_001",
        description="Test obstacle",
        severity="MEDIUM",
    )
    spec = SpecificationNode(
        id="spec_001",
        description="Test spec",
        parameters=[],
    )
    softgoal = SoftgoalNode(
        id="sg_001",
        description="Test softgoal",
        name="Performance",
        type="QUALITY_ATTRIBUTE",
    )

    engine.add_node(goal1)
    engine.add_node(goal2)
    engine.add_node(obstacle)
    engine.add_node(spec)
    engine.add_node(softgoal)

    # Create REFINES edge
    refines_id = engine.add_edge(
        source_id="goal_child",
        target_id="goal_parent",
        edge_type=EdgeType.REFINES,
        metadata={"refinement_type": "AND"},
    )
    assert refines_id is not None

    # Create MITIGATES edge (from spec to obstacle, representing requirement mitigation)
    mitigates_id = engine.add_edge(
        source_id="spec_001",
        target_id="obs_001",
        edge_type=EdgeType.MITIGATES,
        metadata={"mitigation_strategy": "Redundancy"},
    )
    assert mitigates_id is not None

    # Create CONTRIBUTES_TO edge with weight
    contributes_id = engine.add_edge(
        source_id="spec_001",
        target_id="sg_001",
        edge_type=EdgeType.CONTRIBUTES_TO,
        metadata={"weight": 0.75, "impact": "positive"},
    )
    assert contributes_id is not None

    # Verify edges exist (access via engine.edges dict)
    refines_edge = engine.edges[refines_id]
    assert refines_edge.edge_type == EdgeType.REFINES

    contributes_edge = engine.edges[contributes_id]
    assert contributes_edge.metadata["weight"] == 0.75


def test_serialization_persistence_round_trip(tmp_path):
    """Test full graph with new types persists and loads correctly."""
    store_path = tmp_path / "full_graph.json"
    store = HypergraphStore(store_path)
    engine = HypergraphEngine(store)

    # Create full graph
    goal = GoalNode(
        id="goal_001",
        description="Test goal",
        goal_type="MAINTAIN",
        refinement_type="OR",
        agent="TestAgent",
        obstacle_ids=["obs_001"],
        tbd_fields=["mitigation_strategy"],
    )
    engine.add_node(goal)
    engine.save()

    # Load in new engine instance
    engine2 = HypergraphEngine(HypergraphStore(store_path))
    engine2.load()
    loaded_goal = engine2.get_node("goal_001")

    assert isinstance(loaded_goal, GoalNode)
    assert loaded_goal.goal_type == "MAINTAIN"
    assert loaded_goal.refinement_type == "OR"
    assert "obs_001" in loaded_goal.obstacle_ids
    assert "mitigation_strategy" in loaded_goal.tbd_fields


def test_orchestrator_empty_agents_doesnt_crash(tmp_path):
    """Test orchestrator with empty agent list (Phase 1 state)."""
    store = HypergraphStore(tmp_path / "test.json")
    engine = HypergraphEngine(store)
    llm = MockLLMClient()
    orchestrator = Orchestrator(engine, llm)

    # process_intent should work without agents (returns AgentResult)
    result = orchestrator.process_intent("Design a mounting bracket")

    assert result.success
    intent_nodes = engine.get_nodes_by_type(NodeType.INTENT)
    assert len(intent_nodes) == 1


def test_new_trigger_types_exist():
    """Test all new trigger types for 7-agent pipeline exist."""
    required_triggers = [
        "GOALS_EXTRACTED",
        "OBSTACLES_IDENTIFIED",
        "AMBIGUITY_DETECTED",
        "FEEDBACK_PROVIDED",
        "REQUIREMENTS_GENERATED",
        "SPECIFICATIONS_DERIVED",
        "CONTRACTS_EXTRACTED",
        "Z3_VERIFIED",
        "ALLOY_VERIFIED",
    ]

    for trigger_name in required_triggers:
        assert hasattr(TriggerType, trigger_name), f"Missing trigger: {trigger_name}"
        trigger_value = getattr(TriggerType, trigger_name)
        assert isinstance(trigger_value, TriggerType)


def test_trigger_type_count():
    """Test total trigger type count is correct (9 original + 12 new = 21)."""
    all_triggers = list(TriggerType)
    assert len(all_triggers) == 21, f"Expected 21 triggers, got {len(all_triggers)}"
