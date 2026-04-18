"""Tests for feedback module."""

from src.agents.schemas import Ambiguity
from src.feedback.classifier import get_tier
from src.feedback.prioritizer import batch_questions, calculate_priority
from src.feedback.types import FeedbackTier, Question

# ============================================================================
# Tier Classification Tests
# ============================================================================


def test_get_tier_critical_is_t4():
    """CRITICAL severity -> EXPLICIT_SIGNOFF regardless of confidence."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="CRITICAL",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],
    )
    assert get_tier(amb, 0.95) == FeedbackTier.EXPLICIT_SIGNOFF


def test_get_tier_incompleteness_is_t3():
    """INCOMPLETENESS type -> MUST_ASK regardless of confidence."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="INCOMPLETENESS",
        severity="LOW",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],
    )
    assert get_tier(amb, 0.95) == FeedbackTier.MUST_ASK


def test_get_tier_high_confidence_is_t1():
    """High confidence (>=0.9) -> AUTO_APPLY for non-critical, non-incomplete."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="LOW",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],
    )
    assert get_tier(amb, 0.95) == FeedbackTier.AUTO_APPLY
    assert get_tier(amb, 0.90) == FeedbackTier.AUTO_APPLY


def test_get_tier_medium_confidence_is_t2():
    """Medium confidence (0.7-0.9) -> SOFT_CONFIRM."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="MEDIUM",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],
    )
    assert get_tier(amb, 0.85) == FeedbackTier.SOFT_CONFIRM
    assert get_tier(amb, 0.70) == FeedbackTier.SOFT_CONFIRM


def test_get_tier_low_confidence_is_t3():
    """Low confidence (<0.7) -> MUST_ASK."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="MEDIUM",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],
    )
    assert get_tier(amb, 0.69) == FeedbackTier.MUST_ASK
    assert get_tier(amb, 0.50) == FeedbackTier.MUST_ASK


# ============================================================================
# Priority Calculation Tests
# ============================================================================


def test_calculate_priority_formula():
    """Verify priority formula components."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="HIGH",  # risk_factor = 0.75
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=["a", "b"],  # cognitive_cost = 2 * 0.1 + 0.2 = 0.4
    )
    # node_confidence = 0.5
    # info_gain = 0.9 - 0.5 = 0.4
    # confidence_gap = 1.0 - 0.5 = 0.5
    # priority = (0.4 * 0.5 * 0.75) / 0.4 = 0.375
    p = calculate_priority(amb, 0.5, 0.9)
    assert abs(p - 0.375) < 0.001


def test_priority_no_division_by_zero():
    """Min cognitive_cost = 0.1 when no options."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="HIGH",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],  # cognitive_cost = max(0.1, 0 * 0.1 + 0.2) = 0.2
    )
    # Should not raise, should return valid value
    p = calculate_priority(amb, 0.5, 0.9)
    assert 0 <= p <= 1


def test_priority_bounded_0_to_1():
    """Priority always in [0, 1] range."""
    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="CRITICAL",  # risk_factor = 1.0
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=1.0,
        options=[],
    )
    # Extreme case: low confidence, max info gain
    p = calculate_priority(amb, 0.0, 1.0)
    assert 0 <= p <= 1


def test_priority_risk_factor_mapping():
    """Verify risk factor mapping by severity."""
    base_amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="LOW",
        location="x",
        suggested_resolution="y",
        confidence_if_resolved=0.9,
        options=[],
    )

    # Calculate for each severity
    p_low = calculate_priority(base_amb, 0.5, 0.9)

    base_amb.severity = "MEDIUM"
    p_med = calculate_priority(base_amb, 0.5, 0.9)

    base_amb.severity = "HIGH"
    p_high = calculate_priority(base_amb, 0.5, 0.9)

    base_amb.severity = "CRITICAL"
    p_crit = calculate_priority(base_amb, 0.5, 0.9)

    # Higher severity = higher priority
    assert p_low < p_med < p_high < p_crit


# ============================================================================
# Question Batching Tests
# ============================================================================


def test_batch_questions_max_5():
    """No batch exceeds 5 questions."""
    questions = [
        Question(
            id=f"q{i}",
            node_id="n1",
            field=f"f{i}",
            text=f"Q{i}",
            tier=FeedbackTier.MUST_ASK,
            topic="general",
        )
        for i in range(12)
    ]
    batches = batch_questions(questions)
    for batch in batches:
        assert len(batch.questions) <= 5


def test_batch_questions_by_topic():
    """Questions grouped correctly by topic."""
    questions = [
        Question(
            id="q1",
            node_id="n1",
            field="f1",
            text="Q1",
            tier=FeedbackTier.MUST_ASK,
            topic="materials",
        ),
        Question(
            id="q2",
            node_id="n1",
            field="f2",
            text="Q2",
            tier=FeedbackTier.MUST_ASK,
            topic="dimensions",
        ),
        Question(
            id="q3",
            node_id="n1",
            field="f3",
            text="Q3",
            tier=FeedbackTier.MUST_ASK,
            topic="materials",
        ),
    ]
    batches = batch_questions(questions)

    # Should have 2 batches (materials, dimensions)
    topics = {b.topic for b in batches}
    assert topics == {"materials", "dimensions"}

    # Find materials batch
    materials_batch = next(b for b in batches if b.topic == "materials")
    assert len(materials_batch.questions) == 2


def test_batch_questions_priority_sorted():
    """Questions sorted by priority within batch."""
    questions = [
        Question(
            id="q1",
            node_id="n1",
            field="f1",
            text="Q1",
            tier=FeedbackTier.MUST_ASK,
            priority_score=0.3,
            topic="general",
        ),
        Question(
            id="q2",
            node_id="n1",
            field="f2",
            text="Q2",
            tier=FeedbackTier.MUST_ASK,
            priority_score=0.9,
            topic="general",
        ),
        Question(
            id="q3",
            node_id="n1",
            field="f3",
            text="Q3",
            tier=FeedbackTier.MUST_ASK,
            priority_score=0.5,
            topic="general",
        ),
    ]
    batches = batch_questions(questions)
    batch = batches[0]

    # Should be sorted descending by priority
    priorities = [q.priority_score for q in batch.questions]
    assert priorities == [0.9, 0.5, 0.3]


def test_batch_questions_empty_list():
    """Empty input returns empty batches."""
    batches = batch_questions([])
    assert batches == []


# ============================================================================
# FeedbackController Tests
# ============================================================================


def test_feedback_controller_init():
    """Controller initializes with propagator."""
    from unittest.mock import MagicMock

    from src.feedback.controller import FeedbackController

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)
    assert controller.name == "FeedbackController"
    assert controller._propagator is not None


def test_feedback_controller_trigger_types():
    """Controller responds to correct triggers."""
    from unittest.mock import MagicMock

    from src.agents.base import TriggerType
    from src.feedback.controller import FeedbackController

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)
    assert TriggerType.GOALS_EXTRACTED in controller.trigger_types
    assert TriggerType.FEEDBACK_PROVIDED in controller.trigger_types


def test_confidence_update_formula():
    """Verify confidence update formula: new = old + boost * (1 - old)."""
    from unittest.mock import MagicMock

    from src.feedback.controller import FeedbackController
    from src.feedback.types import Resolution

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)

    # auto boost = 0.05
    resolution = Resolution(field="x", value="y", source="auto")
    new_conf = controller.update_confidence("n1", resolution, 0.8)
    # new = 0.8 + 0.05 * (1 - 0.8) = 0.8 + 0.05 * 0.2 = 0.81
    assert abs(new_conf - 0.81) < 0.001

    # user_explicit boost = 0.20
    resolution = Resolution(field="x", value="y", source="user_explicit")
    new_conf = controller.update_confidence("n1", resolution, 0.5)
    # new = 0.5 + 0.20 * (1 - 0.5) = 0.5 + 0.1 = 0.6
    assert abs(new_conf - 0.6) < 0.001


def test_tier1_inference_logged():
    """T1 inferences logged to node.metadata."""
    from unittest.mock import MagicMock

    from src.feedback.controller import FeedbackController
    from src.hypergraph.models import Node, NodeType

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)

    # Create mock node
    node = Node(
        id="n1",
        node_type=NodeType.GOAL,
        description="Test goal",
        metadata={},
        confidence=0.95,
    )

    amb = Ambiguity(
        reasoning="test",
        ambiguity_type="VAGUENESS",
        severity="LOW",
        location="material",
        suggested_resolution="assume aluminum",
        confidence_if_resolved=0.98,
        options=["aluminum", "steel"],
    )

    resolution = controller.handle_tier1(amb, node)

    # Check update_node was called with tier1_inferences
    engine.update_node.assert_called_once()
    call_args = engine.update_node.call_args
    assert call_args[0][0] == "n1"  # node_id
    metadata = call_args[1]["metadata"]
    assert "tier1_inferences" in metadata
    assert len(metadata["tier1_inferences"]) == 1
    assert metadata["tier1_inferences"][0]["ambiguity_id"] == "material"
    assert metadata["tier1_inferences"][0]["applied_value"] == "aluminum"

    # Resolution returned
    assert resolution.source == "auto"
    assert resolution.value == "aluminum"


def test_all_ambiguities_resolved():
    """_all_ambiguities_resolved returns True when all resolved."""
    from unittest.mock import MagicMock

    from src.feedback.controller import FeedbackController

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)

    # Initially empty
    assert controller._all_ambiguities_resolved()

    # Add some ambiguity IDs
    controller._all_ambiguity_ids = {"n1:x", "n1:y", "n2:z"}
    assert not controller._all_ambiguities_resolved()

    # Resolve some
    controller._resolved = {"n1:x", "n1:y"}
    assert not controller._all_ambiguities_resolved()

    # Resolve all
    controller._resolved = {"n1:x", "n1:y", "n2:z"}
    assert controller._all_ambiguities_resolved()

    # Extra resolved is OK (superset)
    controller._resolved = {"n1:x", "n1:y", "n2:z", "extra"}
    assert controller._all_ambiguities_resolved()


def test_analyze_and_route_with_ambiguities():
    """_analyze_and_route routes ambiguities to correct tiers."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController
    from src.hypergraph.models import Node, NodeType

    engine = MagicMock()
    llm = MagicMock()

    # Create node with ambiguity
    node = Node(
        id="n1",
        node_type=NodeType.GOAL,
        description="Test goal",
        metadata={
            "ambiguities": [
                {
                    "reasoning": "test",
                    "ambiguity_type": "VAGUENESS",
                    "severity": "LOW",
                    "location": "material",
                    "suggested_resolution": "use aluminum",
                    "confidence_if_resolved": 0.9,
                    "options": ["aluminum", "steel"],
                }
            ]
        },
        confidence=0.95,
    )
    engine.nodes = {"n1": node}

    controller = FeedbackController(engine, llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED, data={})

    controller.propose_mutation(trigger)

    # T1 should auto-apply for high confidence
    assert "n1:material" in controller._resolved
    assert len(controller._pending_questions) == 0


def test_analyze_and_route_low_confidence():
    """_analyze_and_route creates questions for low confidence ambiguities."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController
    from src.hypergraph.models import Node, NodeType

    engine = MagicMock()
    llm = MagicMock()

    # Create node with low confidence
    node = Node(
        id="n1",
        node_type=NodeType.GOAL,
        description="Test goal",
        metadata={
            "ambiguities": [
                {
                    "reasoning": "test",
                    "ambiguity_type": "VAGUENESS",
                    "severity": "MEDIUM",
                    "location": "material",
                    "suggested_resolution": "need to know material",
                    "confidence_if_resolved": 0.9,
                    "options": ["aluminum", "steel"],
                }
            ]
        },
        confidence=0.5,  # Low confidence -> T3 MUST_ASK
    )
    engine.nodes = {"n1": node}

    controller = FeedbackController(engine, llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED, data={})

    controller.propose_mutation(trigger)

    # Low confidence should create question
    assert "n1:material" in controller._all_ambiguity_ids
    assert len(controller._pending_questions) == 1
    assert controller._pending_questions[0].node_id == "n1"


def test_process_response_updates_node():
    """_process_response updates node with resolution."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController
    from src.hypergraph.models import Node, NodeType

    engine = MagicMock()
    llm = MagicMock()

    # Create mock node
    node = Node(
        id="n1",
        node_type=NodeType.GOAL,
        description="Test goal",
        metadata={"tbd_fields": ["material"]},
        confidence=0.7,
    )
    engine.get_node.return_value = node
    engine.nodes = {"n1": node}
    # Mock get_children to return empty list (leaf node)
    engine.get_children.return_value = []

    controller = FeedbackController(engine, llm)
    controller._all_ambiguity_ids = {"q1"}

    trigger = Trigger(
        trigger_type=TriggerType.FEEDBACK_PROVIDED,
        data={
            "node_id": "n1",
            "question_id": "q1",
            "resolution": {
                "field": "material",
                "value": "aluminum",
                "source": "user_explicit",
            },
        },
    )

    controller.propose_mutation(trigger)

    # Resolution should be marked
    assert "q1" in controller._resolved
    # Node confidence should be updated
    engine.update_node.assert_called()


def test_process_response_missing_data():
    """_process_response handles missing data gracefully."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)

    # Missing resolution data
    trigger = Trigger(
        trigger_type=TriggerType.FEEDBACK_PROVIDED,
        data={"node_id": "n1"},
    )

    mutation = controller.propose_mutation(trigger)

    # Should return empty mutation, not crash
    assert mutation.nodes_to_add == []
    assert mutation.edges_to_add == []


def test_get_pending_batches():
    """get_pending_batches returns batched questions."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController
    from src.hypergraph.models import Node, NodeType

    engine = MagicMock()
    llm = MagicMock()

    # Create node with multiple low-confidence ambiguities
    node = Node(
        id="n1",
        node_type=NodeType.GOAL,
        description="Test goal",
        metadata={
            "ambiguities": [
                {
                    "reasoning": "test1",
                    "ambiguity_type": "VAGUENESS",
                    "severity": "MEDIUM",
                    "location": "material",
                    "suggested_resolution": "choose material",
                    "confidence_if_resolved": 0.9,
                    "options": ["aluminum", "steel"],
                },
                {
                    "reasoning": "test2",
                    "ambiguity_type": "VAGUENESS",
                    "severity": "MEDIUM",
                    "location": "thickness",
                    "suggested_resolution": "choose thickness",
                    "confidence_if_resolved": 0.9,
                    "options": ["1mm", "2mm"],
                },
            ],
            "topic": "materials",
        },
        confidence=0.5,
    )
    engine.nodes = {"n1": node}

    controller = FeedbackController(engine, llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED, data={})

    controller.propose_mutation(trigger)

    batches = controller.get_pending_batches()
    assert len(batches) >= 1
    # All questions should be in batches
    total_questions = sum(len(b.questions) for b in batches)
    assert total_questions == 2


def test_handle_tier2_returns_none():
    """handle_tier2 returns None (deferred to CLI)."""
    from unittest.mock import MagicMock

    from src.feedback.controller import FeedbackController
    from src.feedback.types import FeedbackTier, Question

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)

    question = Question(
        id="q1",
        node_id="n1",
        field="material",
        text="Choose material",
        tier=FeedbackTier.SOFT_CONFIRM,
        topic="general",
    )

    result = controller.handle_tier2(question)
    assert result is None


def test_analyze_and_route_skips_resolved():
    """_analyze_and_route skips already resolved ambiguities."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController
    from src.hypergraph.models import Node, NodeType

    engine = MagicMock()
    llm = MagicMock()

    node = Node(
        id="n1",
        node_type=NodeType.GOAL,
        description="Test goal",
        metadata={
            "ambiguities": [
                {
                    "reasoning": "test",
                    "ambiguity_type": "VAGUENESS",
                    "severity": "MEDIUM",
                    "location": "material",
                    "suggested_resolution": "use aluminum",
                    "confidence_if_resolved": 0.9,
                    "options": ["aluminum", "steel"],
                }
            ]
        },
        confidence=0.5,
    )
    engine.nodes = {"n1": node}

    controller = FeedbackController(engine, llm)
    # Pre-resolve the ambiguity
    controller._resolved = {"n1:material"}

    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED, data={})

    controller.propose_mutation(trigger)

    # Should not create new question for resolved ambiguity
    assert len(controller._pending_questions) == 0


def test_analyze_and_route_empty_nodes():
    """_analyze_and_route handles empty nodes gracefully."""
    from unittest.mock import MagicMock

    from src.agents.base import Trigger, TriggerType
    from src.feedback.controller import FeedbackController

    engine = MagicMock()
    engine.nodes = {}
    llm = MagicMock()

    controller = FeedbackController(engine, llm)
    trigger = Trigger(trigger_type=TriggerType.GOALS_EXTRACTED, data={})

    controller.propose_mutation(trigger)

    assert len(controller._pending_questions) == 0
    assert len(controller._batches) == 0
