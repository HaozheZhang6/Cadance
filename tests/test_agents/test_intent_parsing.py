"""TDD tests for IntentParsingAgent.

Tests KAOS goal tree extraction from natural language intent.
"""

import json

import pytest

from src.agents.base import Trigger, TriggerType
from src.agents.intent_parsing import AgentState, IntentParsingAgent
from src.agents.llm import MockLLMClient
from src.agents.schemas import (
    ExtractedGoalTree,
    ObstacleAnalysis,
)
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import EdgeType, GoalNode, ObstacleNode
from src.hypergraph.store import HypergraphStore


@pytest.fixture
def engine(tmp_path):
    """Fresh hypergraph engine for each test."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    return HypergraphEngine(store)


@pytest.fixture
def mock_llm_achieve():
    """Mock LLM returning ACHIEVE type goal tree."""
    response = json.dumps(
        {
            "root_description": "Design a mounting bracket for 5kg load",
            "root_type": "ACHIEVE",
            "refinement_type": "AND",
            "subgoals": [
                {"description": "Support 5kg static load", "goal_type": "ACHIEVE"},
                {"description": "Fit within 100mm envelope", "goal_type": "ACHIEVE"},
            ],
        }
    )
    return MockLLMClient(default_response=response)


@pytest.fixture
def mock_llm_maintain():
    """Mock LLM returning MAINTAIN type goal tree."""
    response = json.dumps(
        {
            "root_description": "Keep system temperature below 50C",
            "root_type": "MAINTAIN",
            "refinement_type": "AND",
            "subgoals": [
                {"description": "Monitor temperature sensors", "goal_type": "MAINTAIN"},
            ],
        }
    )
    return MockLLMClient(default_response=response)


@pytest.fixture
def mock_llm_avoid():
    """Mock LLM returning AVOID type goal tree."""
    response = json.dumps(
        {
            "root_description": "Prevent motor overheating",
            "root_type": "AVOID",
            "refinement_type": "OR",
            "subgoals": [
                {"description": "Implement thermal cutoff", "goal_type": "ACHIEVE"},
                {"description": "Add cooling system", "goal_type": "ACHIEVE"},
            ],
        }
    )
    return MockLLMClient(default_response=response)


@pytest.fixture
def mock_llm_obstacles():
    """Mock LLM for obstacle extraction."""
    response = json.dumps(
        {
            "obstacles": [
                {
                    "description": "Material fatigue under cyclic loading",
                    "severity": "HIGH",
                    "threatened_goals": ["Support 5kg static load"],
                },
                {
                    "description": "Thermal expansion mismatch",
                    "severity": "MEDIUM",
                    "threatened_goals": ["Fit within 100mm envelope"],
                },
            ]
        }
    )
    return MockLLMClient(default_response=response)


# Test 1: Extract goals from simple intent -> ACHIEVE type
def test_extract_goals_simple_intent(engine, mock_llm_achieve):
    """Extract goals from simple intent returns ExtractedGoalTree with ACHIEVE type."""
    agent = IntentParsingAgent(engine, mock_llm_achieve)

    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Design a mounting bracket for 5kg load"},
    )

    agent.propose_mutation(trigger)

    # Agent should have extracted goal tree (pending confirmation)
    assert len(agent._pending_goals) > 0
    root = agent._pending_goals[0]
    assert root.goal_type == "ACHIEVE"
    assert "bracket" in root.description.lower()


# Test 2: Extract goals from "keep/maintain" intent -> MAINTAIN type
def test_extract_goals_maintain_intent(engine, mock_llm_maintain):
    """Extract goals from maintain intent returns MAINTAIN type."""
    agent = IntentParsingAgent(engine, mock_llm_maintain)

    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Keep system temperature below 50C"},
    )

    agent.propose_mutation(trigger)

    root = agent._pending_goals[0]
    assert root.goal_type == "MAINTAIN"


# Test 3: Extract goals from "prevent" intent -> AVOID type
def test_extract_goals_avoid_intent(engine, mock_llm_avoid):
    """Extract goals from prevent intent returns AVOID type."""
    agent = IntentParsingAgent(engine, mock_llm_avoid)

    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Prevent motor overheating"},
    )

    agent.propose_mutation(trigger)

    root = agent._pending_goals[0]
    assert root.goal_type == "AVOID"


# Test 4: Extract subgoals with AND/OR refinement
def test_extract_subgoals_and_refinement(engine, mock_llm_achieve):
    """Root has subgoals with AND refinement type."""
    agent = IntentParsingAgent(engine, mock_llm_achieve)

    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Design a mounting bracket for 5kg load"},
    )

    agent.propose_mutation(trigger)

    root = agent._pending_goals[0]
    assert root.refinement_type == "AND"
    # Subgoals are extracted but not yet in pending (level-by-level)
    assert len(agent._extracted_subgoals) == 2


# Test 5: Extract obstacles with severity
def test_extract_obstacles(engine, mock_llm_obstacles):
    """Extract obstacles returns ObstacleAnalysis with severity."""
    agent = IntentParsingAgent(engine, mock_llm_obstacles)

    # Simulate already having goals and moving to obstacle extraction
    agent._state = AgentState.EXTRACTING_OBSTACLES
    agent._root_goal_id = "goal_001"
    agent._goal_map = {
        "Support 5kg static load": "goal_002",
        "Fit within 100mm envelope": "goal_003",
    }

    trigger = Trigger(
        trigger_type=TriggerType.FEEDBACK_PROVIDED,
        data={"action": "extract_obstacles"},
    )

    agent.propose_mutation(trigger)

    # Should have pending obstacles
    assert len(agent._pending_obstacles) == 2
    obs = agent._pending_obstacles[0]
    assert obs.severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# Test 6: Agent creates GoalNodes
def test_agent_creates_goal_nodes(engine, mock_llm_achieve):
    """Agent propose_mutation creates GoalNodes."""
    agent = IntentParsingAgent(engine, mock_llm_achieve)

    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Design a bracket"},
    )

    agent.propose_mutation(trigger)

    # Confirm to commit goals
    confirm_trigger = Trigger(
        trigger_type=TriggerType.FEEDBACK_PROVIDED,
        data={"action": "confirm"},
    )

    mutation = agent.propose_mutation(confirm_trigger)

    # Mutation should contain GoalNodes
    goal_nodes = [n for n in mutation.nodes_to_add if isinstance(n, GoalNode)]
    assert len(goal_nodes) >= 1
    assert all(n.goal_type in ["ACHIEVE", "MAINTAIN", "AVOID"] for n in goal_nodes)


# Test 7: Agent creates HAS_CHILD edges (parent -> child direction)
def test_agent_creates_derives_from_edges(engine, mock_llm_achieve):
    """HAS_CHILD edges link parent goal to child (parent is source)."""
    agent = IntentParsingAgent(engine, mock_llm_achieve)

    # Extract root
    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Design a bracket"},
    )
    agent.propose_mutation(trigger)

    # Confirm root
    agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "confirm"})
    )

    # Extract subgoals
    agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "extract_subgoals"})
    )

    # Confirm subgoals
    mutation = agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "confirm"})
    )

    # Check HAS_CHILD edges (not DERIVES_FROM - that's for Requirement->Intent)
    has_child_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.HAS_CHILD
    ]
    assert len(has_child_edges) >= 1

    # Edge direction: parent (source) HAS_CHILD subgoal (target)
    for edge in has_child_edges:
        # Source should be root, target should be subgoal
        assert edge.source_id == agent._root_goal_id


# Test 8: Agent creates ObstacleNodes with severity
def test_agent_creates_obstacle_nodes(engine, mock_llm_obstacles):
    """ObstacleNodes created with severity classification."""
    agent = IntentParsingAgent(engine, mock_llm_obstacles)

    # Setup: simulate goals already extracted
    agent._state = AgentState.EXTRACTING_OBSTACLES
    agent._root_goal_id = "goal_001"
    agent._goal_map = {
        "Support 5kg static load": "goal_002",
        "Fit within 100mm envelope": "goal_003",
    }

    # Extract obstacles
    agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "extract_obstacles"})
    )

    # Confirm obstacles
    mutation = agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "confirm"})
    )

    # Check ObstacleNodes
    obstacle_nodes = [n for n in mutation.nodes_to_add if isinstance(n, ObstacleNode)]
    assert len(obstacle_nodes) >= 1
    assert all(
        n.severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] for n in obstacle_nodes
    )


# Test 9: Obstacle edges - MITIGATES is Requirement->Obstacle, not Obstacle->Goal
def test_agent_creates_mitigates_edges(engine, mock_llm_obstacles):
    """MITIGATES edges are Requirement->Obstacle, not created from obstacle extraction.

    Obstacle->Goal edges would need OBSTRUCTS edge type.
    Threatened goals are stored in obstacle metadata instead.
    """
    agent = IntentParsingAgent(engine, mock_llm_obstacles)

    # Setup: simulate goals already extracted
    agent._state = AgentState.EXTRACTING_OBSTACLES
    agent._root_goal_id = "goal_001"
    agent._goal_map = {
        "Support 5kg static load": "goal_002",
        "Fit within 100mm envelope": "goal_003",
    }

    # Extract obstacles
    agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "extract_obstacles"})
    )

    # Confirm obstacles
    mutation = agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "confirm"})
    )

    # No MITIGATES edges created - MITIGATES is Requirement->Obstacle
    mitigates_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.MITIGATES
    ]
    assert len(mitigates_edges) == 0

    # Obstacles have threatened_goals in metadata
    obstacle_nodes = [n for n in mutation.nodes_to_add if isinstance(n, ObstacleNode)]
    assert len(obstacle_nodes) >= 1
    for obs in obstacle_nodes:
        assert "threatened_goals" in obs.metadata


# Test 10: Agent state transitions correctly
def test_agent_state_transitions(engine, mock_llm_achieve):
    """Agent state machine transitions correctly through extraction flow."""
    agent = IntentParsingAgent(engine, mock_llm_achieve)

    # Initial state
    assert agent._state == AgentState.EXTRACTING

    # Extract root -> AWAITING_GOAL_CONFIRMATION
    trigger = Trigger(
        trigger_type=TriggerType.INTENT_CREATED,
        data={"description": "Design a bracket"},
    )
    agent.propose_mutation(trigger)
    assert agent._state == AgentState.AWAITING_GOAL_CONFIRMATION

    # Confirm -> back to EXTRACTING (for subgoals) or EXTRACTING_OBSTACLES
    agent.propose_mutation(
        Trigger(TriggerType.FEEDBACK_PROVIDED, data={"action": "confirm"})
    )
    # State should progress (either extracting subgoals or obstacles)
    assert agent._state in [
        AgentState.EXTRACTING,
        AgentState.EXTRACTING_OBSTACLES,
        AgentState.AWAITING_GOAL_CONFIRMATION,
    ]


# Test 11: Schema generates valid JSON schema
def test_extracted_goal_tree_schema():
    """ExtractedGoalTree generates valid JSON schema for OpenAI."""
    schema = ExtractedGoalTree.model_json_schema()

    assert "properties" in schema
    assert "root_description" in schema["properties"]
    assert "root_type" in schema["properties"]
    assert "refinement_type" in schema["properties"]
    assert "subgoals" in schema["properties"]


# Test 12: Schema validates correctly
def test_schema_validation():
    """Schemas validate LLM responses correctly."""
    valid_tree = {
        "root_description": "Test goal",
        "root_type": "ACHIEVE",
        "refinement_type": "AND",
        "subgoals": [{"description": "Subgoal 1", "goal_type": "ACHIEVE"}],
    }

    tree = ExtractedGoalTree.model_validate(valid_tree)
    assert tree.root_type == "ACHIEVE"
    assert len(tree.subgoals) == 1


# Test 13: ObstacleAnalysis schema works
def test_obstacle_analysis_schema():
    """ObstacleAnalysis schema validates obstacle list."""
    valid_analysis = {
        "obstacles": [
            {
                "description": "Test obstacle",
                "severity": "HIGH",
                "threatened_goals": ["Goal 1"],
            }
        ]
    }

    analysis = ObstacleAnalysis.model_validate(valid_analysis)
    assert len(analysis.obstacles) == 1
    assert analysis.obstacles[0].severity == "HIGH"


# Test 14: Agent name and trigger_types properties
def test_agent_interface_properties(engine):
    """Agent implements BaseAgent interface correctly."""
    mock_llm = MockLLMClient()
    agent = IntentParsingAgent(engine, mock_llm)

    assert agent.name == "IntentParsingAgent"
    assert TriggerType.INTENT_CREATED in agent.trigger_types
    assert TriggerType.FEEDBACK_PROVIDED in agent.trigger_types
