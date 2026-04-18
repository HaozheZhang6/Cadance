"""TDD tests for AmbiguityDetectionAgent.

Tests AT-CoT ambiguity detection on goal trees.
"""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from src.agents.schemas import Ambiguity
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import GoalNode
from src.hypergraph.store import HypergraphStore

# =============================================================================
# Schema Validation Tests
# =============================================================================


@pytest.mark.parametrize(
    "ambiguity_type",
    ["LEXICAL", "SYNTACTIC", "SEMANTIC", "PRAGMATIC", "VAGUENESS", "INCOMPLETENESS"],
)
def test_ambiguity_schema_valid_types(ambiguity_type):
    """Test all 6 ambiguity types are accepted."""
    amb = Ambiguity(
        reasoning="Test reasoning",
        ambiguity_type=ambiguity_type,
        severity="HIGH",
        location="test location",
        suggested_resolution="clarify this",
        confidence_if_resolved=0.9,
    )
    assert amb.ambiguity_type == ambiguity_type


@pytest.mark.parametrize("severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
def test_ambiguity_schema_valid_severities(severity):
    """Test all 4 severity levels are accepted."""
    amb = Ambiguity(
        reasoning="Test reasoning",
        ambiguity_type="VAGUENESS",
        severity=severity,
        location="test location",
        suggested_resolution="clarify",
        confidence_if_resolved=0.8,
    )
    assert amb.severity == severity


def test_ambiguity_schema_rejects_invalid_type():
    """Test invalid ambiguity type raises ValidationError."""
    with pytest.raises(ValidationError):
        Ambiguity(
            reasoning="test",
            ambiguity_type="INVALID_TYPE",
            severity="HIGH",
            location="test",
            suggested_resolution="test",
            confidence_if_resolved=0.5,
        )


def test_ambiguity_schema_rejects_invalid_severity():
    """Test invalid severity raises ValidationError."""
    with pytest.raises(ValidationError):
        Ambiguity(
            reasoning="test",
            ambiguity_type="VAGUENESS",
            severity="INVALID",
            location="test",
            suggested_resolution="test",
            confidence_if_resolved=0.5,
        )


# =============================================================================
# Agent Classification Tests
# =============================================================================


@pytest.fixture
def mock_llm():
    """Mock LLM that returns predictable AmbiguityAnalysis."""
    llm = MagicMock()
    return llm


@pytest.fixture
def engine(tmp_path):
    """Fresh HypergraphEngine for testing."""
    store = HypergraphStore(tmp_path / "hypergraph.json")
    return HypergraphEngine(store)


@pytest.fixture
def vague_goal(engine):
    """Goal with vague term 'lightweight'."""
    goal = GoalNode(
        id="goal_vague",
        description="Design a lightweight bracket",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="test",
    )
    engine.add_node(goal)
    return goal


@pytest.fixture
def incomplete_goal(engine):
    """Goal missing load specification."""
    goal = GoalNode(
        id="goal_incomplete",
        description="Bracket must support the load",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="test",
    )
    engine.add_node(goal)
    return goal


def test_agent_detects_vagueness(engine, vague_goal, mock_llm):
    """Test agent detects VAGUENESS for 'lightweight' without numeric spec."""
    from src.agents.ambiguity_detection import AmbiguityDetectionAgent
    from src.agents.base import Trigger, TriggerType

    # Configure mock LLM response
    mock_llm.complete_json.return_value = {
        "goal_id": "goal_vague",
        "goal_description": "Design a lightweight bracket",
        "ambiguities": [
            {
                "reasoning": "'Lightweight' is subjective. Could mean <1kg, <500g, or relative to alternatives.",
                "ambiguity_type": "VAGUENESS",
                "severity": "HIGH",
                "location": "lightweight",
                "suggested_resolution": "Specify maximum weight in kg/g",
                "options": ["<500g", "<1kg", "lighter than steel alternative"],
                "confidence_if_resolved": 0.9,
            }
        ],
        "overall_confidence": 0.4,
    }

    agent = AmbiguityDetectionAgent(engine, mock_llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    # Verify ambiguity was detected
    node_updates = mutation.nodes_to_update
    assert "goal_vague" in node_updates
    assert "ambiguities" in node_updates["goal_vague"].get("metadata", {})
    ambiguities = node_updates["goal_vague"]["metadata"]["ambiguities"]
    assert len(ambiguities) == 1
    assert ambiguities[0]["ambiguity_type"] == "VAGUENESS"


def test_agent_detects_incompleteness(engine, incomplete_goal, mock_llm):
    """Test agent detects INCOMPLETENESS for missing load value."""
    from src.agents.ambiguity_detection import AmbiguityDetectionAgent
    from src.agents.base import Trigger, TriggerType

    mock_llm.complete_json.return_value = {
        "goal_id": "goal_incomplete",
        "goal_description": "Bracket must support the load",
        "ambiguities": [
            {
                "reasoning": "Load value not specified. Cannot determine structural requirements.",
                "ambiguity_type": "INCOMPLETENESS",
                "severity": "CRITICAL",
                "location": "the load",
                "suggested_resolution": "Specify load in N or kg",
                "options": ["5kg", "10kg", "50N"],
                "confidence_if_resolved": 0.95,
            }
        ],
        "overall_confidence": 0.2,
    }

    agent = AmbiguityDetectionAgent(engine, mock_llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    node_updates = mutation.nodes_to_update
    assert "goal_incomplete" in node_updates
    ambiguities = node_updates["goal_incomplete"]["metadata"]["ambiguities"]
    assert ambiguities[0]["ambiguity_type"] == "INCOMPLETENESS"


def test_agent_assigns_severity(engine, incomplete_goal, mock_llm):
    """Test agent assigns CRITICAL severity for safety-related gaps."""
    from src.agents.ambiguity_detection import AmbiguityDetectionAgent
    from src.agents.base import Trigger, TriggerType

    mock_llm.complete_json.return_value = {
        "goal_id": "goal_incomplete",
        "goal_description": "Bracket must support the load",
        "ambiguities": [
            {
                "reasoning": "Missing load spec is safety-critical.",
                "ambiguity_type": "INCOMPLETENESS",
                "severity": "CRITICAL",
                "location": "the load",
                "suggested_resolution": "Specify load",
                "options": [],
                "confidence_if_resolved": 0.9,
            }
        ],
        "overall_confidence": 0.2,
    }

    agent = AmbiguityDetectionAgent(engine, mock_llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    ambiguities = mutation.nodes_to_update["goal_incomplete"]["metadata"]["ambiguities"]
    assert ambiguities[0]["severity"] == "CRITICAL"


# =============================================================================
# tbd_fields Population Tests
# =============================================================================


def test_agent_populates_tbd_fields(engine, vague_goal, mock_llm):
    """Test ambiguity.location is added to node.tbd_fields."""
    from src.agents.ambiguity_detection import AmbiguityDetectionAgent
    from src.agents.base import Trigger, TriggerType

    mock_llm.complete_json.return_value = {
        "goal_id": "goal_vague",
        "goal_description": "Design a lightweight bracket",
        "ambiguities": [
            {
                "reasoning": "Lightweight is vague",
                "ambiguity_type": "VAGUENESS",
                "severity": "HIGH",
                "location": "lightweight",
                "suggested_resolution": "Specify weight",
                "options": [],
                "confidence_if_resolved": 0.9,
            }
        ],
        "overall_confidence": 0.4,
    }

    agent = AmbiguityDetectionAgent(engine, mock_llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    # Check tbd_fields updated
    node_updates = mutation.nodes_to_update
    assert "goal_vague" in node_updates
    tbd_fields = node_updates["goal_vague"].get("tbd_fields", [])
    assert "lightweight" in tbd_fields


# =============================================================================
# AT-CoT Reasoning Tests
# =============================================================================


def test_ambiguity_has_reasoning(engine, vague_goal, mock_llm):
    """Test each ambiguity includes non-empty reasoning chain."""
    from src.agents.ambiguity_detection import AmbiguityDetectionAgent
    from src.agents.base import Trigger, TriggerType

    mock_llm.complete_json.return_value = {
        "goal_id": "goal_vague",
        "goal_description": "Design a lightweight bracket",
        "ambiguities": [
            {
                "reasoning": "The term 'lightweight' is relative and context-dependent. In aerospace <500g is typical. In automotive <5kg. Without domain context, cannot determine threshold.",
                "ambiguity_type": "VAGUENESS",
                "severity": "HIGH",
                "location": "lightweight",
                "suggested_resolution": "Specify weight limit",
                "options": ["<500g (aerospace)", "<5kg (automotive)"],
                "confidence_if_resolved": 0.9,
            }
        ],
        "overall_confidence": 0.4,
    }

    agent = AmbiguityDetectionAgent(engine, mock_llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    ambiguities = mutation.nodes_to_update["goal_vague"]["metadata"]["ambiguities"]
    assert len(ambiguities[0]["reasoning"]) > 10  # Non-trivial reasoning


def test_agent_handles_no_ambiguities(engine, mock_llm):
    """Test agent handles goals with no ambiguities."""
    from src.agents.ambiguity_detection import AmbiguityDetectionAgent
    from src.agents.base import Trigger, TriggerType

    # Add clear goal
    clear_goal = GoalNode(
        id="goal_clear",
        description="Bracket shall support 5kg static load with 2x safety factor",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="test",
    )
    engine.add_node(clear_goal)

    mock_llm.complete_json.return_value = {
        "goal_id": "goal_clear",
        "goal_description": "Bracket shall support 5kg static load with 2x safety factor",
        "ambiguities": [],
        "overall_confidence": 0.95,
    }

    agent = AmbiguityDetectionAgent(engine, mock_llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    # Should still update node metadata even with no ambiguities
    node_updates = mutation.nodes_to_update
    assert "goal_clear" in node_updates
    assert node_updates["goal_clear"]["metadata"]["ambiguities"] == []
