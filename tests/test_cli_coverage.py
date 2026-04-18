"""Tests for CLI coverage - interactive paths and edge cases."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli import _print_node_full, _print_node_summary, cli
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Budget,
    Contract,
    EdgeType,
    GoalNode,
    Intent,
    Requirement,
    RequirementStatus,
    SpecificationNode,
    Unknown,
)
from src.hypergraph.store import HypergraphStore


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


class TestPipelineCommand:
    """Tests for pipeline command coverage."""

    def test_pipeline_empty_intent_shows_error(self, runner, tmp_path):
        """Pipeline should show error for empty intent."""
        store_path = tmp_path / "test_graph.json"

        result = runner.invoke(
            cli,
            ["pipeline", "--intent", "   ", "--output", str(store_path)],
        )

        assert "ERROR" in result.output
        assert "empty" in result.output.lower()


class TestRefineGrsCommand:
    """Tests for refine-grs command coverage."""

    def test_refine_grs_empty_intent_shows_error(self, runner, tmp_path):
        """refine-grs should show error for empty intent."""
        store_path = tmp_path / "test_graph.json"

        result = runner.invoke(
            cli,
            ["refine-grs", "--intent", "  ", "--output", str(store_path)],
        )

        assert "ERROR" in result.output
        assert "empty" in result.output.lower()

    def test_refine_grs_no_api_key_shows_error(self, runner, tmp_path):
        """refine-grs should show error when no API key."""
        store_path = tmp_path / "test_graph.json"

        with patch("src.cli.LLMClient") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.is_configured.return_value = False
            mock_llm_class.return_value = mock_llm

            result = runner.invoke(
                cli,
                ["refine-grs", "--intent", "Test intent", "--output", str(store_path)],
            )

            assert "ERROR" in result.output
            assert "API key" in result.output or "OPENAI_API_KEY" in result.output


class TestExtractContractsCommand:
    """Tests for extract-contracts command coverage."""

    def test_extract_contracts_no_api_key_shows_error(self, runner, tmp_path):
        """extract-contracts should show error when no API key."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        engine.save()

        with patch("src.cli.LLMClient") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.is_configured.return_value = False
            mock_llm_class.return_value = mock_llm

            result = runner.invoke(
                cli,
                ["extract-contracts", "--input", str(store_path)],
            )

            assert "ERROR" in result.output
            assert "API key" in result.output or "OPENAI_API_KEY" in result.output

    def test_extract_contracts_no_grs_nodes(self, runner, tmp_path):
        """extract-contracts should warn when no GRS nodes."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        # Add only a contract, no GRS nodes
        contract = Contract(
            id="contract_001",
            description="Test",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)
        engine.save()

        with patch("src.cli.LLMClient") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.is_configured.return_value = True
            mock_llm_class.return_value = mock_llm

            result = runner.invoke(
                cli,
                ["extract-contracts", "--input", str(store_path)],
            )

            assert "No GRS nodes found" in result.output
            assert "refine-grs first" in result.output


class TestPrintNodeFull:
    """Tests for _print_node_full helper covering all node types."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create engine for tests."""
        store_path = tmp_path / "test.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_print_node_full_goal_node(self, engine, capsys):
        """_print_node_full should display GoalNode fields."""
        from rich.console import Console

        goal = GoalNode(
            id="goal_001",
            description="Achieve safety",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="System",
            confidence=0.9,
        )
        engine.add_node(goal)

        # Use console to capture output
        console = Console(force_terminal=True)
        with patch("src.cli.console", console):
            _print_node_full(goal, engine)

    def test_print_node_full_specification_node(self, engine, capsys):
        """_print_node_full should display SpecificationNode fields."""
        from src.hypergraph.models import SpecParameter

        spec = SpecificationNode(
            id="spec_001",
            description="Material spec",
            parameters=[
                SpecParameter(name="thickness", value="6mm", unit="mm"),
                SpecParameter(name="material", value="aluminum"),
            ],
            verification_criteria=["Test method A", "Analysis B"],
            confidence=0.85,
        )
        engine.add_node(spec)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(spec, engine)
            # Verify Parameters and Verification Criteria are printed
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Parameters" in str(c) for c in calls)

    def test_print_node_full_contract_with_inputs_outputs(self, engine):
        """_print_node_full should display Contract inputs/outputs."""
        contract = Contract(
            id="contract_001",
            description="Test contract",
            inputs={"load": "50N", "temp": "25C"},
            outputs={"stress": "100MPa"},
            guarantees=["stress < yield"],
            assumptions=["static loading"],
            confidence=0.8,
        )
        engine.add_node(contract)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(contract, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Inputs" in str(c) for c in calls)
            assert any("Outputs" in str(c) for c in calls)
            assert any("Guarantees" in str(c) for c in calls)
            assert any("Assumptions" in str(c) for c in calls)

    def test_print_node_full_intent_with_constraints(self, engine):
        """_print_node_full should display Intent constraints."""
        intent = Intent(
            id="intent_001",
            description="Design bracket",
            goal="Support 5kg load",
            constraints=["Cost < $100", "Weight < 500g"],
            confidence=1.0,
        )
        engine.add_node(intent)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(intent, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Goal" in str(c) for c in calls)
            assert any("Constraints" in str(c) for c in calls)

    def test_print_node_full_requirement_with_all_fields(self, engine):
        """_print_node_full should display all Requirement fields."""
        req = Requirement(
            id="req_001",
            description="Structural requirement",
            statement="System SHALL support 50N",
            status=RequirementStatus.VALIDATED,
            rationale="Safety critical",
            assumptions=["Static load", "Room temperature"],
            verification_method="TEST",
            is_testable=True,
            is_unambiguous=True,
            is_complete=False,
            confidence=0.9,
        )
        engine.add_node(req)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(req, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Statement" in str(c) for c in calls)
            assert any("Rationale" in str(c) for c in calls)
            assert any("Assumptions" in str(c) for c in calls)
            assert any("Verification" in str(c) for c in calls)
            assert any("Validation" in str(c) for c in calls)

    def test_print_node_full_unknown_with_candidates(self, engine):
        """_print_node_full should display Unknown candidates."""
        unknown = Unknown(
            id="unknown_001",
            description="Material selection unknown",
            reason="Need analysis",
            candidates=["Aluminum 6061", "Steel 304", "Titanium"],
            confidence=0.5,
        )
        engine.add_node(unknown)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(unknown, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Reason" in str(c) for c in calls)
            assert any("Candidates" in str(c) for c in calls)

    def test_print_node_full_budget_with_all_fields(self, engine):
        """_print_node_full should display Budget fields."""
        budget = Budget(
            id="budget_001",
            description="Cost budget",
            resource_type="cost",
            total=1000.0,
            consumed=250.0,
            unit="USD",
            confidence=0.95,
        )
        engine.add_node(budget)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(budget, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Resource" in str(c) for c in calls)
            assert any("Total" in str(c) for c in calls)
            assert any("Consumed" in str(c) for c in calls)

    def test_print_node_full_shows_parents_and_children(self, engine):
        """_print_node_full should display parent and child relationships."""
        parent = Intent(id="parent_001", description="Parent", goal="Goal")
        child = Contract(
            id="child_001",
            description="Child",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(parent)
        engine.add_node(child)
        engine.add_edge("parent_001", "child_001", EdgeType.HAS_CHILD)

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_full(child, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Parents" in str(c) for c in calls)

        with patch("src.cli.console", console):
            _print_node_full(parent, engine)
            calls = [str(c) for c in console.print.call_args_list]
            assert any("Children" in str(c) for c in calls)


class TestPrintNodeSummary:
    """Tests for _print_node_summary helper."""

    def test_print_node_summary_truncates_long_description(self):
        """_print_node_summary should truncate long descriptions."""
        node = Contract(
            id="contract_001",
            description="A" * 100,  # 100 character description
            inputs={},
            outputs={},
            guarantees=[],
        )

        console = MagicMock()
        with patch("src.cli.console", console):
            _print_node_summary(node)
            calls = [str(c) for c in console.print.call_args_list]
            # Should have truncation indicator
            assert any("..." in str(c) for c in calls)


class TestListNodesFullNodeTypes:
    """Additional tests for list-nodes --full with various node types."""

    @pytest.fixture
    def hypergraph_with_spec_and_goal(self, tmp_path):
        """Create hypergraph with SpecificationNode and GoalNode."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        from src.hypergraph.models import SpecParameter

        goal = GoalNode(
            id="goal_001",
            description="Achieve target",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="System",
        )
        spec = SpecificationNode(
            id="spec_001",
            description="Material spec",
            parameters=[SpecParameter(name="value", value="100")],
            verification_criteria=["Test A"],
        )

        engine.add_node(goal)
        engine.add_node(spec)
        engine.save()

        return store_path

    def test_list_nodes_full_goal(self, runner, hypergraph_with_spec_and_goal):
        """list-nodes goal --full should show goal-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "goal",
                "--full",
                "--input",
                str(hypergraph_with_spec_and_goal),
            ],
        )

        assert result.exit_code == 0
        assert "goal_001" in result.output
        assert "Goal Type:" in result.output or "ACHIEVE" in result.output

    def test_list_nodes_full_specification(self, runner, hypergraph_with_spec_and_goal):
        """list-nodes specification --full should show spec-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "specification",
                "--full",
                "--input",
                str(hypergraph_with_spec_and_goal),
            ],
        )

        assert result.exit_code == 0
        assert "spec_001" in result.output
        assert "Parameters:" in result.output or "value" in result.output


class TestCLIIntentFlag:
    """Tests for --intent flag on main CLI."""

    def test_intent_flag_invokes_pipeline(self, runner, tmp_path):
        """--intent flag should invoke pipeline command."""
        store_path = tmp_path / "test_graph.json"

        with patch("src.cli.LLMClient") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.is_configured.return_value = False
            mock_llm_class.return_value = mock_llm

            with patch("src.cli.HYPERGRAPH_STORE_PATH", store_path):
                result = runner.invoke(
                    cli,
                    ["--intent", "Test intent"],
                )

                # Should show pipeline step or API key error
                assert (
                    "Step 1" in result.output
                    or "API key" in result.output
                    or "ERROR" in result.output
                )
