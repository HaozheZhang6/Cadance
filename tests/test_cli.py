"""Tests for CLI commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli import cli
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Budget,
    Contract,
    EdgeType,
    Evidence,
    Intent,
    Requirement,
    RequirementStatus,
    Unknown,
)
from src.hypergraph.store import HypergraphStore


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_hypergraph(tmp_path):
    """Create a sample hypergraph for testing."""
    store_path = tmp_path / "test_graph.json"
    store = HypergraphStore(store_path)
    engine = HypergraphEngine(store)

    # Create sample nodes
    intent = Intent(
        id="intent_001",
        description="Design a test bracket",
        goal="Test goal",
        confidence=1.0,
    )
    contract = Contract(
        id="contract_001",
        description="Structural requirements",
        inputs={"load": "50N"},
        outputs={"stress": "MPa"},
        guarantees=["stress < 100 MPa"],
        confidence=0.8,
    )
    evidence = Evidence(
        id="evidence_001",
        description="FEA analysis results",
        evidence_type="simulation",
        provenance="ANSYS 2024",
        data={"max_stress": 45},
        confidence=0.9,
    )

    engine.add_node(intent)
    engine.add_node(contract)
    engine.add_node(evidence)
    engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
    engine.add_edge("evidence_001", "contract_001", EdgeType.VALIDATES)
    engine.save()

    return store_path


class TestExportCommand:
    """Tests for export command."""

    def test_export_creates_json_file(self, runner, sample_hypergraph, tmp_path):
        """Export should create a valid JSON file."""
        output_path = tmp_path / "export.json"

        result = runner.invoke(
            cli,
            ["export", "--output", str(output_path), "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert output_path.exists()
        assert "Exported to" in result.output

    def test_export_contains_nodes_and_edges(self, runner, sample_hypergraph, tmp_path):
        """Exported JSON should contain nodes and edges."""
        output_path = tmp_path / "export.json"

        runner.invoke(
            cli,
            ["export", "--output", str(output_path), "--input", str(sample_hypergraph)],
        )

        with open(output_path) as f:
            data = json.load(f)

        assert "nodes" in data
        assert "edges" in data
        assert "intent_001" in data["nodes"]
        assert "contract_001" in data["nodes"]

    def test_export_requires_output_path(self, runner, sample_hypergraph):
        """Export should fail without output path."""
        result = runner.invoke(
            cli,
            ["export", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_export_handles_empty_graph(self, runner, tmp_path):
        """Export should handle empty hypergraph."""
        # Create empty graph
        store_path = tmp_path / "empty_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        engine.save()

        output_path = tmp_path / "export.json"

        result = runner.invoke(
            cli,
            ["export", "--output", str(output_path), "--input", str(store_path)],
        )

        assert result.exit_code == 0
        with open(output_path) as f:
            data = json.load(f)
        assert data["nodes"] == {}
        assert data["edges"] == {}


class TestVerifyCommand:
    """Tests for verify command."""

    def test_verify_runs_pipeline(self, runner, sample_hypergraph):
        """Verify should run verification pipeline."""
        result = runner.invoke(
            cli,
            ["verify", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert "V0:" in result.output

    def test_verify_shows_summary(self, runner, sample_hypergraph):
        """Verify should show compact tier summary."""
        result = runner.invoke(
            cli,
            ["verify", "--input", str(sample_hypergraph)],
        )

        assert "V0:" in result.output
        assert "V1:" in result.output

    def test_verify_handles_empty_graph(self, runner, tmp_path):
        """Verify should handle empty hypergraph."""
        store_path = tmp_path / "empty_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        engine.save()

        result = runner.invoke(
            cli,
            ["verify", "--input", str(store_path)],
        )

        assert result.exit_code == 0
        assert "V0:" in result.output


class TestShowGraphCommand:
    """Tests for show-graph command."""

    def test_show_graph_displays_nodes(self, runner, sample_hypergraph):
        """Show-graph should display all nodes."""
        result = runner.invoke(
            cli,
            ["show-graph", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert "intent_001" in result.output
        assert "contract_001" in result.output
        assert "evidence_001" in result.output

    def test_show_graph_displays_edges(self, runner, sample_hypergraph):
        """Show-graph should display all edges."""
        result = runner.invoke(
            cli,
            ["show-graph", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert "Edges" in result.output
        assert "has_child" in result.output or "validates" in result.output


def test_attach_artifact_and_verify_mech(runner, tmp_path):
    """Attach artifact and run mech verification via CLI."""
    store_path = tmp_path / "graph.json"
    store = HypergraphStore(store_path)
    engine = HypergraphEngine(store)

    contract = Contract(
        id="contract_001",
        description="Bracket contract",
        inputs={},
        outputs={},
        guarantees=["hole diameter >= 1.0mm"],
    )
    engine.add_node(contract)
    engine.save()

    ops_path = Path("tests/dfm_test_cases/L2_thin_wall_ops.json")

    attach_result = runner.invoke(
        cli,
        [
            "attach-artifact",
            "--target",
            "contract_001",
            "--type",
            "ops_program",
            "--path",
            str(ops_path),
            "--input",
            str(store_path),
        ],
    )
    assert attach_result.exit_code == 0

    verify_result = runner.invoke(
        cli,
        [
            "verify-mech",
            "--target",
            "contract_001",
            "--input",
            str(store_path),
        ],
    )
    assert verify_result.exit_code == 0

    def test_show_graph_displays_node_types(self, runner, sample_hypergraph):
        """Show-graph should display node types."""
        result = runner.invoke(
            cli,
            ["show-graph", "--input", str(sample_hypergraph)],
        )

        assert "[intent]" in result.output
        assert "[contract]" in result.output
        assert "[evidence]" in result.output

    def test_show_graph_handles_empty_graph(self, runner, tmp_path):
        """Show-graph should handle empty hypergraph."""
        store_path = tmp_path / "empty_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        engine.save()

        result = runner.invoke(
            cli,
            ["show-graph", "--input", str(store_path)],
        )

        assert result.exit_code == 0
        assert "Nodes (0)" in result.output


class TestShowNodeCommand:
    """Tests for show-node command."""

    def test_show_node_displays_details(self, runner, sample_hypergraph):
        """Show-node should display node details."""
        result = runner.invoke(
            cli,
            ["show-node", "contract_001", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert "contract_001" in result.output
        assert "Structural requirements" in result.output
        assert "Confidence:" in result.output

    def test_show_node_displays_children(self, runner, sample_hypergraph):
        """Show-node should display children if present."""
        result = runner.invoke(
            cli,
            ["show-node", "intent_001", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert "Children" in result.output
        assert "contract_001" in result.output

    def test_show_node_handles_missing_node(self, runner, sample_hypergraph):
        """Show-node should handle missing node gracefully."""
        result = runner.invoke(
            cli,
            ["show-node", "nonexistent_node", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0
        assert "not found" in result.output

    def test_show_node_requires_node_id(self, runner, sample_hypergraph):
        """Show-node should require node_id argument."""
        result = runner.invoke(
            cli,
            ["show-node", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code != 0


class TestConfidenceTreeCommand:
    """Tests for confidence-tree command."""

    def test_confidence_tree_displays_tree(self, runner, sample_hypergraph):
        """Confidence-tree should display tree structure with explicit root."""
        result = runner.invoke(
            cli,
            [
                "confidence-tree",
                "--root",
                "intent_001",
                "--input",
                str(sample_hypergraph),
            ],
        )

        assert result.exit_code == 0
        assert "intent_001" in result.output
        assert "confidence:" in result.output

    def test_confidence_tree_with_specific_root(self, runner, sample_hypergraph):
        """Confidence-tree should work with specific root node."""
        result = runner.invoke(
            cli,
            [
                "confidence-tree",
                "--root",
                "intent_001",
                "--input",
                str(sample_hypergraph),
            ],
        )

        assert result.exit_code == 0
        assert "intent_001" in result.output

    def test_confidence_tree_shows_computed_values(self, runner, sample_hypergraph):
        """Confidence-tree should show computed confidence values."""
        result = runner.invoke(
            cli,
            [
                "confidence-tree",
                "--root",
                "intent_001",
                "--input",
                str(sample_hypergraph),
            ],
        )

        assert result.exit_code == 0
        # Should contain confidence values like "0.80" or "1.00"
        assert "confidence:" in result.output

    def test_confidence_tree_handles_no_goals(self, runner, tmp_path):
        """Confidence-tree should handle graph with no Goal nodes."""
        store_path = tmp_path / "no_goals.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        # Add only a contract, no goals
        contract = Contract(
            id="contract_001",
            description="Orphan contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)
        engine.save()

        result = runner.invoke(
            cli,
            ["confidence-tree", "--input", str(store_path)],
        )

        assert result.exit_code == 0
        assert "No Goal nodes found" in result.output


class TestVerboseAndQuietFlags:
    """Tests for verbose and quiet flags."""

    def test_verbose_flag_accepted(self, runner, sample_hypergraph):
        """CLI should accept verbose flag."""
        result = runner.invoke(
            cli,
            ["--verbose", "show-graph", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0

    def test_quiet_flag_accepted(self, runner, sample_hypergraph):
        """CLI should accept quiet flag."""
        result = runner.invoke(
            cli,
            ["--quiet", "show-graph", "--input", str(sample_hypergraph)],
        )

        assert result.exit_code == 0


class TestListNodesCommand:
    """Tests for list-nodes command."""

    @pytest.fixture
    def hypergraph_with_all_types(self, tmp_path):
        """Create hypergraph with all node types for testing."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        # Create nodes of different types
        intent = Intent(
            id="intent_001",
            description="Design a test bracket",
            goal="Test goal",
        )
        requirement = Requirement(
            id="req_001",
            description="REQ-001",
            statement="The bracket shall withstand 50N",
            status=RequirementStatus.VALIDATED,
            is_testable=True,
            is_unambiguous=True,
            is_complete=True,
            rationale="Safety requirement",
            verification_method="Load test",
        )
        contract = Contract(
            id="contract_001",
            description="Structural contract",
            inputs={"load": "50N"},
            outputs={"stress": "MPa"},
            guarantees=["stress < 100 MPa"],
        )
        unknown = Unknown(
            id="unknown_001",
            description="Material selection",
            reason="Need analysis",
            candidates=["Aluminum", "Steel"],
        )
        evidence = Evidence(
            id="evidence_001",
            description="FEA results",
            evidence_type="simulation",
            provenance="ANSYS 2024",
        )
        budget = Budget(
            id="budget_001",
            description="Cost budget",
            resource_type="cost",
            total=1000,
            consumed=250,
            unit="USD",
        )

        engine.add_node(intent)
        engine.add_node(requirement)
        engine.add_node(contract)
        engine.add_node(unknown)
        engine.add_node(evidence)
        engine.add_node(budget)
        engine.save()

        return store_path

    def test_list_nodes_accepts_valid_type(self, runner, hypergraph_with_all_types):
        """list-nodes should accept valid node types."""
        valid_types = [
            "intent",
            "requirement",
            "contract",
            "unknown",
            "evidence",
            "budget",
        ]

        for node_type in valid_types:
            result = runner.invoke(
                cli,
                ["list-nodes", node_type, "--input", str(hypergraph_with_all_types)],
            )
            assert result.exit_code == 0
            assert f"{node_type.upper()} Nodes" in result.output

    def test_list_nodes_rejects_invalid_type(self, runner, hypergraph_with_all_types):
        """list-nodes should reject invalid node types."""
        result = runner.invoke(
            cli,
            ["list-nodes", "invalid_type", "--input", str(hypergraph_with_all_types)],
        )

        assert result.exit_code == 0  # Exits gracefully
        assert "Invalid node type" in result.output
        assert "Valid types:" in result.output

    def test_list_nodes_without_type_shows_all(self, runner, hypergraph_with_all_types):
        """list-nodes without type should show all nodes."""
        result = runner.invoke(
            cli,
            ["list-nodes", "--input", str(hypergraph_with_all_types)],
        )

        assert result.exit_code == 0
        assert "All Nodes" in result.output
        # Should show nodes of different types
        assert "intent_001" in result.output
        assert "contract_001" in result.output

    def test_list_nodes_full_shows_requirement_fields(
        self, runner, hypergraph_with_all_types
    ):
        """--full should show requirement-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "requirement",
                "--full",
                "--input",
                str(hypergraph_with_all_types),
            ],
        )

        assert result.exit_code == 0
        assert "req_001" in result.output
        assert "Statement:" in result.output
        assert "withstand 50N" in result.output
        assert "Validation:" in result.output

    def test_list_nodes_full_shows_contract_fields(
        self, runner, hypergraph_with_all_types
    ):
        """--full should show contract-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "contract",
                "--full",
                "--input",
                str(hypergraph_with_all_types),
            ],
        )

        assert result.exit_code == 0
        assert "contract_001" in result.output
        assert "Inputs:" in result.output or "Guarantees:" in result.output

    def test_list_nodes_full_shows_intent_fields(
        self, runner, hypergraph_with_all_types
    ):
        """--full should show intent-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "intent",
                "--full",
                "--input",
                str(hypergraph_with_all_types),
            ],
        )

        assert result.exit_code == 0
        assert "intent_001" in result.output
        assert "Goal:" in result.output

    def test_list_nodes_full_shows_unknown_fields(
        self, runner, hypergraph_with_all_types
    ):
        """--full should show unknown-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "unknown",
                "--full",
                "--input",
                str(hypergraph_with_all_types),
            ],
        )

        assert result.exit_code == 0
        assert "unknown_001" in result.output
        assert "Reason:" in result.output
        assert "Candidates:" in result.output

    def test_list_nodes_full_shows_budget_fields(
        self, runner, hypergraph_with_all_types
    ):
        """--full should show budget-specific fields."""
        result = runner.invoke(
            cli,
            [
                "list-nodes",
                "budget",
                "--full",
                "--input",
                str(hypergraph_with_all_types),
            ],
        )

        assert result.exit_code == 0
        assert "budget_001" in result.output
        assert "Resource:" in result.output or "Total:" in result.output

    def test_list_nodes_handles_empty_type(self, runner, tmp_path):
        """list-nodes should handle empty results for a type."""
        store_path = tmp_path / "empty_type.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        # Add only an intent, no requirements
        intent = Intent(
            id="intent_001",
            description="Test",
            goal="Goal",
        )
        engine.add_node(intent)
        engine.save()

        result = runner.invoke(
            cli,
            ["list-nodes", "requirement", "--input", str(store_path)],
        )

        assert result.exit_code == 0
        assert "REQUIREMENT Nodes (0)" in result.output
        assert "No nodes found" in result.output


class TestPipelineSATGate:
    """Tests for contract SAT gate in pipeline."""

    @pytest.fixture
    def hypergraph_with_contracts(self, tmp_path):
        """Create hypergraph with GRS tree and contracts for SAT gate testing."""
        from src.hypergraph.models import (
            Contract,
            ContractStatus,
            GoalNode,
            SpecificationNode,
        )

        store_path = tmp_path / "test_sat_gate.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        # Create GRS hierarchy
        goal = GoalNode(
            id="goal_001",
            description="Test goal for SAT gate",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="designer",
            metadata={"grs_id": "G1"},
        )
        engine.add_node(goal)

        spec = SpecificationNode(
            id="spec_001",
            description="Test spec",
            metadata={"grs_id": "S1"},
        )
        engine.add_node(spec)
        engine.add_edge(goal.id, spec.id, EdgeType.HAS_CHILD)

        # Create contract
        contract = Contract(
            id="contract_001",
            description="Test contract for SAT gate",
            assumptions=["temp >= 0"],
            guarantees=["stress < 100"],
            status=ContractStatus.DRAFT,
            confidence=1.0,
        )
        engine.add_node(contract)
        engine.add_edge(goal.id, contract.id, EdgeType.SATISFIES)
        engine.save()

        return store_path

    def test_pipeline_sat_gate_exists(self, runner, hypergraph_with_contracts):
        """Pipeline includes Step 2.5 contract verification when contracts exist."""
        result = runner.invoke(
            cli,
            ["verify", "--input", str(hypergraph_with_contracts)],
        )
        assert result.exit_code == 0
        assert "V0:" in result.output

    def test_pre_artifact_gate_runs(self, tmp_path):
        """PreArtifactGate runs with minimal setup (empty graph)."""
        from src.verification.pre_artifact_gate import PreArtifactGate

        store_path = tmp_path / "test_gate.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        engine.save()

        gate = PreArtifactGate(
            engine=engine,
            intent="test",
            store_path=str(store_path),
            llm=None,
            max_attempts=3,
        )
        result = gate.run()

        assert result.success is True
        assert result.attempts == 1

    def test_pre_artifact_gate_with_contract(self, tmp_path):
        """Gate passes with satisfiable numeric contract."""
        from src.hypergraph.models import (
            Contract,
            ContractStatus,
            SpecificationNode,
            SpecParameter,
        )
        from src.verification.pre_artifact_gate import PreArtifactGate

        store_path = tmp_path / "test_sat.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        spec = SpecificationNode(
            id="spec_sat",
            description="Test spec",
            parameters=[
                SpecParameter(
                    name="thickness", value=12.0, unit="mm", tolerance="+/- 1mm"
                )
            ],
            entity_id="bracket",
            regime_id="normal",
        )
        engine.add_node(spec)

        contract = Contract(
            id="contract_sat",
            description="SAT contract",
            assumptions=["thickness >= 10 mm"],
            guarantees=["thickness <= 20 mm"],
            status=ContractStatus.DRAFT,
        )
        engine.add_node(contract)
        engine.save()

        gate = PreArtifactGate(
            engine=engine,
            intent="test",
            store_path=str(store_path),
            llm=None,
            max_attempts=3,
        )
        result = gate.run()

        assert result.success is True

    def test_pre_artifact_gate_unsat_no_llm(self, tmp_path):
        """UNSAT without LLM exhausts max_attempts."""
        from src.hypergraph.models import (
            Contract,
            ContractStatus,
            SpecificationNode,
            SpecParameter,
        )
        from src.verification.pre_artifact_gate import PreArtifactGate

        store_path = tmp_path / "test_unsat.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        spec = SpecificationNode(
            id="spec_conflict",
            description="Spec with conflicting params",
            parameters=[
                SpecParameter(
                    name="diameter",
                    value="10",
                    unit="mm",
                    tolerance_upper="0.5",
                    tolerance_lower="0.5",
                ),
            ],
            entity_id="part",
            regime_id="normal",
        )
        engine.add_node(spec)

        contract = Contract(
            id="contract_unsat",
            description="Contract conflicting with spec",
            assumptions=["diameter >= 5mm"],
            guarantees=["diameter <= 5mm"],
            status=ContractStatus.DRAFT,
            metadata={"entity_id": "part", "regime_id": "normal"},
        )
        engine.add_node(contract)
        engine.save()

        gate = PreArtifactGate(
            engine=engine,
            intent="test",
            store_path=str(store_path),
            llm=None,
            max_attempts=2,
        )
        result = gate.run()

        assert result.attempts <= 2


class TestVerifyCadqueryCommand:
    """Tests for verify-cadquery command."""

    def test_verify_cadquery_requires_input(self, runner):
        """verify-cadquery requires either --step-path or --geometry."""
        result = runner.invoke(cli, ["verify-cadquery"])

        assert result.exit_code == 0  # Graceful exit
        assert "Must provide --step-path or --geometry" in result.output

    def test_verify_cadquery_handles_missing_file(self, runner):
        """verify-cadquery handles missing STEP file gracefully."""
        result = runner.invoke(
            cli, ["verify-cadquery", "--step-path", "/nonexistent/file.step"]
        )

        assert result.exit_code == 0  # Graceful exit
        assert "STEP file not found" in result.output

    def test_verify_cadquery_with_valid_step(self, runner):
        """verify-cadquery works with valid STEP file."""
        step_path = (
            "src/mech_verifier/test_projects/cadquery_golden_pass/inputs/bracket.step"
        )
        if not Path(step_path).exists():
            pytest.skip("CadQuery test STEP file not found")

        result = runner.invoke(cli, ["verify-cadquery", "--step-path", step_path])

        assert result.exit_code == 0
        assert "Status:" in result.output
        assert "Enhanced Confidence:" in result.output
