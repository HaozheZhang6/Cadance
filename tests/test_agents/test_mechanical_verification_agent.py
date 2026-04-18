"""Tests for MechanicalVerificationAgent."""

from pathlib import Path

from src.agents.base import Trigger, TriggerType
from src.agents.mechanical_verification import MechanicalVerificationAgent
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    ArtifactNode,
    Contract,
    EdgeType,
    NodeType,
    SpecificationNode,
)
from src.hypergraph.store import HypergraphStore


def test_mech_verification_agent_creates_evidence_and_updates_contract(tmp_path):
    """Agent should create evidence nodes and update contract status."""
    store = HypergraphStore(tmp_path / "graph.json")
    engine = HypergraphEngine(store)

    contract = Contract(
        id="contract_001",
        description="Bracket contract",
        inputs={},
        outputs={},
        guarantees=["hole diameter >= 1.0mm"],
    )
    ops_path = Path(
        "src/verifier_core/test_projects/mech_hole_too_small/ops_program.json"
    )
    artifact = ArtifactNode(
        id="artifact_001",
        description="Ops program",
        artifact_type="ops_program",
        path=str(ops_path),
        media_type="application/json",
        role="input",
    )

    engine.add_node(contract)
    engine.add_node(artifact)
    engine.add_edge(contract.id, artifact.id, EdgeType.HAS_CHILD)

    agent = MechanicalVerificationAgent(
        engine=engine, llm=None, artifact_store_dir=tmp_path / "artifacts"
    )
    trigger = Trigger(trigger_type=TriggerType.CONTRACTS_EXTRACTED)
    mutation = agent.propose_mutation(trigger)

    assert any(n.node_type == NodeType.TOOL_INVOCATION for n in mutation.nodes_to_add)
    assert any(n.node_type == NodeType.EVIDENCE for n in mutation.nodes_to_add)
    assert "contract_001" in mutation.nodes_to_update


def test_build_grs_mapping_from_specs(tmp_path):
    """_build_grs_mapping returns {grs_id: node_id} for all specs."""
    store = HypergraphStore(tmp_path / "graph.json")
    engine = HypergraphEngine(store)

    spec1 = SpecificationNode(
        id="spec_node_001",
        description="Hole diameter spec",
        metadata={"grs_id": "S1.1.1"},
    )
    spec2 = SpecificationNode(
        id="spec_node_002",
        description="Wall thickness spec",
        metadata={"grs_id": "S1.2.1"},
    )
    engine.add_node(spec1)
    engine.add_node(spec2)

    agent = MechanicalVerificationAgent(
        engine=engine, llm=None, artifact_store_dir=tmp_path / "artifacts"
    )
    mapping = agent._build_grs_mapping()

    assert mapping == {"S1.1.1": "spec_node_001", "S1.2.1": "spec_node_002"}


def test_build_grs_mapping_empty_when_no_specs(tmp_path):
    """_build_grs_mapping returns empty dict when no specs exist."""
    store = HypergraphStore(tmp_path / "graph.json")
    engine = HypergraphEngine(store)

    agent = MechanicalVerificationAgent(
        engine=engine, llm=None, artifact_store_dir=tmp_path / "artifacts"
    )
    mapping = agent._build_grs_mapping()
    assert mapping == {}


def test_build_grs_mapping_skips_specs_without_grs_id(tmp_path):
    """Specs without grs_id in metadata are skipped."""
    store = HypergraphStore(tmp_path / "graph.json")
    engine = HypergraphEngine(store)

    spec = SpecificationNode(
        id="spec_no_grs",
        description="No GRS ID",
        metadata={},
    )
    engine.add_node(spec)

    agent = MechanicalVerificationAgent(
        engine=engine, llm=None, artifact_store_dir=tmp_path / "artifacts"
    )
    mapping = agent._build_grs_mapping()
    assert mapping == {}
