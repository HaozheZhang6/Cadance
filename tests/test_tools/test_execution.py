"""Tests for tool execution manager."""

from pathlib import Path

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import EdgeType, NodeType
from src.hypergraph.store import HypergraphStore
from src.tools.execution import ToolExecutionManager
from src.tools.mech_verify import MechVerifyTool
from src.tools.registry import ToolRegistry


def test_tool_execution_manager_creates_invocation_and_artifacts(tmp_path):
    """Execution manager should create tool invocation + artifacts."""
    store = HypergraphStore(tmp_path / "graph.json")
    engine = HypergraphEngine(store)

    registry = ToolRegistry()
    registry.register(MechVerifyTool())

    artifacts_dir = tmp_path / "artifacts"
    manager = ToolExecutionManager(
        engine=engine, registry=registry, artifact_store_dir=artifacts_dir
    )

    ops_path = Path("tests/dfm_test_cases/L2_thin_wall_ops.json")
    result = manager.execute(
        tool_name="mech-verify",
        inputs={"mode": "ops_program", "ops_program_path": str(ops_path)},
    )

    assert result.tool_result.success is True
    mutation = result.mutation

    invocation_nodes = [
        n for n in mutation.nodes_to_add if n.node_type == NodeType.TOOL_INVOCATION
    ]
    artifact_nodes = [
        n for n in mutation.nodes_to_add if n.node_type == NodeType.ARTIFACT
    ]
    generated_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.GENERATED
    ]

    assert invocation_nodes
    assert artifact_nodes
    assert generated_edges
