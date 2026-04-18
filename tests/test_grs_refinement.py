"""TDD tests for GRSRefinementAgent.

Tests Goal->Requirement->Specification tree generation from intent.
"""

import json

import pytest

from src.agents.grs_refinement import (
    GRSRefinementAgent,
    RefinementState,
    apply_changes_to_engine,
)
from src.agents.llm import MockLLMClient
from src.agents.schemas import (
    AssumptionOutput,
    GoalOutput,
    GRSChange,
    GRSTreeOutput,
    RequirementOutput,
    SpecOutput,
    SpecParameterOutput,
)
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import EdgeType, SpecParameter
from src.hypergraph.store import HypergraphStore


@pytest.fixture
def engine(tmp_path):
    """Fresh hypergraph engine for each test."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    return HypergraphEngine(store)


@pytest.fixture
def mock_llm_with_grs_tree():
    """Mock LLM returning valid GRS tree."""
    response = json.dumps(
        {
            "goals": [
                {
                    "id": "G1",
                    "description": "Support 5kg load safely",
                    "goal_type": "ACHIEVE",
                    "requirements": [
                        {
                            "id": "R1.1",
                            "statement": "System SHALL support 5kg static load",
                            "rationale": "Primary functional requirement",
                            "specifications": [
                                {
                                    "id": "S1.1.1",
                                    "description": "Use steel bracket with 10mm thickness",
                                    "parameters": [
                                        {
                                            "name": "thickness",
                                            "value": "10",
                                            "unit": "mm",
                                            "tolerance": "±0.5",
                                        }
                                    ],
                                    "verification_criteria": ["Load test to 7.5kg"],
                                }
                            ],
                        }
                    ],
                }
            ],
            "assumptions": [
                {
                    "id": "A1",
                    "text": "Assuming static load only, no vibration",
                    "confidence": "Likely",
                    "reasoning": "Intent doesn't mention dynamic loading",
                    "affects": "S1.1.1",
                }
            ],
        }
    )
    return MockLLMClient(default_response=response)


def test_grs_schemas_valid():
    """Test GRS schemas are valid and accessible."""
    # Create sample tree
    spec = SpecOutput(
        id="S1.1.1",
        description="Use 10mm steel bracket",
        parameters=[
            SpecParameterOutput(
                name="thickness", value="10", unit="mm", tolerance="±0.5"
            )
        ],
        verification_criteria=["Load test to 7.5kg"],
    )

    requirement = RequirementOutput(
        id="R1.1",
        statement="System SHALL support 5kg load",
        rationale="Primary functional requirement",
        specifications=[spec],
    )

    goal = GoalOutput(
        id="G1",
        description="Support 5kg load safely",
        goal_type="ACHIEVE",
        requirements=[requirement],
    )

    assumption = AssumptionOutput(
        id="A1",
        text="Assuming static load only",
        confidence="Likely",
        reasoning="Intent doesn't mention dynamics",
        affects="S1.1.1",
    )

    tree = GRSTreeOutput(goals=[goal], assumptions=[assumption])

    # Assert all fields accessible
    assert tree.goals[0].id == "G1"
    assert tree.goals[0].requirements[0].id == "R1.1"
    assert tree.goals[0].requirements[0].specifications[0].id == "S1.1.1"
    assert tree.assumptions[0].id == "A1"
    assert tree.assumptions[0].confidence == "Likely"

    # Assert model_dump returns valid dict
    data = tree.model_dump()
    assert isinstance(data, dict)
    assert "goals" in data
    assert "assumptions" in data


def test_grs_agent_initialization(engine):
    """Test GRSRefinementAgent initializes correctly."""
    mock_llm = MockLLMClient()
    agent = GRSRefinementAgent(engine, mock_llm)

    assert agent.name == "GRSRefinementAgent"
    assert agent.state == RefinementState.GENERATING
    assert agent._iteration_count == 0
    assert agent._current_tree is None


def test_generate_initial_calls_llm(engine, mock_llm_with_grs_tree):
    """Test generate_initial() calls LLM and returns valid tree."""
    agent = GRSRefinementAgent(engine, mock_llm_with_grs_tree)

    intent = "Design a mounting bracket for a 5kg load"
    tree = agent.generate_initial(intent)

    # Assert LLM was called (MockLLMClient tracks call count)
    assert mock_llm_with_grs_tree.call_count == 1

    # Assert returned tree has goals
    assert isinstance(tree, GRSTreeOutput)
    assert len(tree.goals) > 0
    assert tree.goals[0].id == "G1"
    assert tree.goals[0].goal_type == "ACHIEVE"

    # Assert nested structure
    assert len(tree.goals[0].requirements) > 0
    assert tree.goals[0].requirements[0].id == "R1.1"
    assert "SHALL" in tree.goals[0].requirements[0].statement

    assert len(tree.goals[0].requirements[0].specifications) > 0
    assert tree.goals[0].requirements[0].specifications[0].id == "S1.1.1"

    # Assert assumptions
    assert len(tree.assumptions) > 0
    assert tree.assumptions[0].confidence in ["Confident", "Likely", "Uncertain"]

    # Assert state transition
    assert agent.state == RefinementState.AWAITING_FEEDBACK
    assert agent._current_tree == tree


def test_save_to_hypergraph_creates_edges():
    """Verify HAS_CHILD edges link G->R->S hierarchy."""
    from unittest.mock import MagicMock

    # Mock engine
    mock_engine = MagicMock()
    mock_engine._generate_id = MagicMock(side_effect=lambda prefix: f"{prefix}_123")

    # Create agent
    agent = GRSRefinementAgent(mock_engine, MagicMock())

    # Create test tree
    tree = GRSTreeOutput(
        goals=[
            GoalOutput(
                id="G1",
                description="Test goal",
                goal_type="ACHIEVE",
                requirements=[
                    RequirementOutput(
                        id="R1.1",
                        statement="The system SHALL test",
                        specifications=[
                            SpecOutput(
                                id="S1.1.1",
                                description="Test spec",
                                parameters=[
                                    SpecParameterOutput(
                                        name="test",
                                        value="1",
                                        unit="mm",
                                        tolerance="0.1",
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
        assumptions=[],
    )

    # Call save
    agent.save_to_hypergraph(tree)

    # Verify edges created
    add_edge_calls = mock_engine.add_edge.call_args_list
    assert len(add_edge_calls) >= 2, "Should create G->R and R->S edges"

    # Check edge types are HAS_CHILD
    for call in add_edge_calls:
        assert call.kwargs.get("edge_type") == EdgeType.HAS_CHILD or (
            call.args[2] == EdgeType.HAS_CHILD if len(call.args) > 2 else True
        )


# ==============================================================================
# apply_changes_to_engine tests
# ==============================================================================


class TestApplyChangesToEngine:
    """Tests for apply_changes_to_engine() in-place node updates."""

    def _populate_engine(self, engine):
        """Add G1->R1.1->S1.1.1 to engine, return grs_mapping."""
        from src.agents.llm import MockLLMClient

        agent = GRSRefinementAgent(engine, MockLLMClient())
        agent._intent = "test"
        tree = GRSTreeOutput(
            goals=[
                GoalOutput(
                    id="G1",
                    description="Test goal",
                    goal_type="ACHIEVE",
                    requirements=[
                        RequirementOutput(
                            id="R1.1",
                            statement="System SHALL do X",
                            rationale="Because",
                            specifications=[
                                SpecOutput(
                                    id="S1.1.1",
                                    description="Original spec desc",
                                    parameters=[
                                        SpecParameterOutput(
                                            name="thickness",
                                            value="10",
                                            unit="mm",
                                            tolerance="+/- 0.5",
                                        )
                                    ],
                                    verification_criteria=["Test A"],
                                )
                            ],
                        )
                    ],
                )
            ],
            assumptions=[],
        )
        mapping = agent.save_to_hypergraph(tree)
        return mapping

    def test_modify_requirement_statement(self, engine):
        """Modify statement updates both statement + description."""
        mapping = self._populate_engine(engine)
        hg_id = mapping["R1.1"]
        old_node = engine.nodes[hg_id]
        assert old_node.statement == "System SHALL do X"

        changes = [
            GRSChange(
                action="modify",
                target_id="R1.1",
                field="statement",
                new_value="System SHALL do Y at 49.05 N",
                reason="Clarify",
            )
        ]
        modified = apply_changes_to_engine(engine, changes, mapping)

        assert hg_id in modified
        node = engine.nodes[hg_id]
        assert node.statement == "System SHALL do Y at 49.05 N"
        assert "R1.1:" in node.description

    def test_modify_spec_description(self, engine):
        """Modify spec description updates in-place."""
        mapping = self._populate_engine(engine)
        hg_id = mapping["S1.1.1"]

        changes = [
            GRSChange(
                action="modify",
                target_id="S1.1.1",
                field="description",
                new_value="Updated spec desc",
                reason="Clarify",
            )
        ]
        modified = apply_changes_to_engine(engine, changes, mapping)

        assert hg_id in modified
        assert engine.nodes[hg_id].description == "Updated spec desc"

    def test_skip_add_action(self, engine):
        """Add actions are skipped with warning."""
        mapping = self._populate_engine(engine)
        changes = [
            GRSChange(
                action="add",
                target_id="R1.2",
                field="statement",
                new_value="New req",
                reason="Add",
            )
        ]
        modified = apply_changes_to_engine(engine, changes, mapping)
        assert len(modified) == 0

    def test_skip_remove_action(self, engine):
        """Remove actions are skipped with warning."""
        mapping = self._populate_engine(engine)
        changes = [
            GRSChange(
                action="remove",
                target_id="R1.1",
                field="statement",
                reason="Remove",
            )
        ]
        modified = apply_changes_to_engine(engine, changes, mapping)
        assert len(modified) == 0

    def test_unknown_grs_id_skipped(self, engine):
        """Unknown GRS ID skipped gracefully."""
        mapping = self._populate_engine(engine)
        changes = [
            GRSChange(
                action="modify",
                target_id="R99.99",
                field="statement",
                new_value="X",
                reason="X",
            )
        ]
        modified = apply_changes_to_engine(engine, changes, mapping)
        assert len(modified) == 0

    def test_ids_preserved_after_modify(self, engine):
        """Node IDs remain unchanged after in-place modify."""
        mapping = self._populate_engine(engine)
        ids_before = set(engine.nodes.keys())

        changes = [
            GRSChange(
                action="modify",
                target_id="S1.1.1",
                field="description",
                new_value="Changed",
                reason="Test",
            )
        ]
        apply_changes_to_engine(engine, changes, mapping)

        ids_after = set(engine.nodes.keys())
        assert ids_before == ids_after

    def test_modify_spec_parameters_coerces_to_models(self, engine):
        """Parameter updates are coerced to SpecParameter models."""
        mapping = self._populate_engine(engine)
        hg_id = mapping["S1.1.1"]

        changes = [
            GRSChange(
                action="modify",
                target_id="S1.1.1",
                field="parameters",
                new_value=json.dumps(
                    [
                        {
                            "name": "thickness",
                            "value": 8.0,
                            "unit": "mm",
                            "tolerance": "+/- 0.5",
                            "quantity_id": "plate_thickness",
                            "term_class": "structured",
                        }
                    ]
                ),
                reason="Clarify parameter values",
            )
        ]

        modified = apply_changes_to_engine(engine, changes, mapping)
        assert hg_id in modified
        node = engine.nodes[hg_id]
        assert len(node.parameters) == 1
        assert isinstance(node.parameters[0], SpecParameter)
        assert node.parameters[0].name == "thickness"

    def test_invalid_spec_parameters_payload_keeps_existing(self, engine):
        """Malformed parameter payload should not corrupt existing spec params."""
        mapping = self._populate_engine(engine)
        hg_id = mapping["S1.1.1"]
        original = engine.nodes[hg_id].parameters

        changes = [
            GRSChange(
                action="modify",
                target_id="S1.1.1",
                field="parameters",
                new_value=json.dumps([{"value": 8.0, "unit": "mm"}]),  # missing name
                reason="Bad payload",
            )
        ]

        apply_changes_to_engine(engine, changes, mapping)
        node = engine.nodes[hg_id]
        assert len(node.parameters) == len(original)
        assert node.parameters[0].name == original[0].name
