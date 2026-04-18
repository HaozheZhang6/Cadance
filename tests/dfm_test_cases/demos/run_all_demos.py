#!/usr/bin/env python
"""Run all demo ops programs through verification pipeline and save results."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def _setup_project_root() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    os.chdir(project_root)
    return project_root


def hash_file(path: Path) -> str:
    """Generate SHA256 hash of file."""
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_verification(ops_path: Path, results_dir: Path) -> dict:
    """Run verification on an ops program and return results."""
    from src.agents.base import Trigger, TriggerType
    from src.agents.mechanical_verification import MechanicalVerificationAgent
    from src.hypergraph.engine import HypergraphEngine
    from src.hypergraph.models import (
        ArtifactNode,
        Contract,
        ContractStatus,
        EdgeType,
        NodeType,
    )
    from src.hypergraph.store import HypergraphStore

    # Create fresh store for each demo
    store_path = results_dir / f"{ops_path.stem}_graph.json"
    store = HypergraphStore(str(store_path))
    engine = HypergraphEngine(store)

    # Create contract
    ops_name = ops_path.stem.replace("_ops", "")
    contract = Contract(
        id=f"contract_{ops_name}",
        description=f"Verify {ops_name} design",
        assumptions=["Manufacturing process: CNC machining"],
        guarantees=["Part meets DFM requirements"],
        status=ContractStatus.DRAFT,
    )
    engine.add_node(contract)

    # Create artifact node
    sha = hash_file(ops_path)
    artifact_node = ArtifactNode(
        id=f"artifact_{sha[:8]}",
        description="ops_program artifact",
        artifact_type="ops_program",
        path=str(ops_path),
        sha256=sha,
        media_type="application/json",
        role="input",
        size_bytes=ops_path.stat().st_size,
    )
    engine.add_node(artifact_node)
    engine.add_edge(contract.id, artifact_node.id, EdgeType.HAS_CHILD)
    engine.save()

    # Run verification
    mech_agent = MechanicalVerificationAgent(
        engine=engine, llm=None, artifact_store_dir=results_dir / "artifacts"
    )

    trigger = Trigger(
        trigger_type=TriggerType.MANUAL,
        data={"target_id": contract.id, "artifact_id": artifact_node.id},
    )

    mutation = mech_agent.propose_mutation(trigger)

    # Apply mutation
    for node in mutation.nodes_to_add:
        engine.add_node(node)
    for edge in mutation.edges_to_add:
        engine.add_edge(edge.source_id, edge.target_id, edge.edge_type)
    for node_id, updates in mutation.nodes_to_update.items():
        node = engine.get_node(node_id)
        if node:
            for k, v in updates.items():
                setattr(node, k, v)
    engine.save()

    # Gather results
    evidence = engine.get_nodes_by_type(NodeType.EVIDENCE)
    unknowns = engine.get_nodes_by_type(NodeType.UNKNOWN)
    invocations = engine.get_nodes_by_type(NodeType.TOOL_INVOCATION)

    contract_node = engine.get_node(contract.id)

    return {
        "ops_file": ops_path.name,
        "store_path": str(store_path),
        "contract_status": str(contract_node.status) if contract_node else "N/A",
        "contract_confidence": getattr(contract_node, "confidence", 0),
        "evidence_count": len(evidence),
        "unknown_count": len(unknowns),
        "invocation_count": len(invocations),
        "evidence": [
            {
                "description": e.description,
                "evidence_type": e.evidence_type,
                "provenance": e.provenance,
            }
            for e in evidence
        ],
        "unknowns": [
            {"description": u.description, "reason": u.reason} for u in unknowns
        ],
    }


def main():
    _setup_project_root()
    demos_dir = Path(__file__).parent
    results_dir = demos_dir / "results"
    results_dir.mkdir(exist_ok=True)

    # Find all ops files
    ops_files = sorted(demos_dir.glob("*_ops.json"))

    print(f"Found {len(ops_files)} demo ops programs")
    print("=" * 60)

    all_results = {
        "timestamp": datetime.now().isoformat(),
        "total_demos": len(ops_files),
        "demos": [],
    }

    for ops_path in ops_files:
        print(f"\nProcessing: {ops_path.name}")
        try:
            result = run_verification(ops_path, results_dir)
            all_results["demos"].append(result)

            status_emoji = "✅" if "SATISFIED" in result["contract_status"] else "⚠️"
            print(f"  {status_emoji} Status: {result['contract_status']}")
            print(f"     Confidence: {result['contract_confidence']:.2f}")
            print(
                f"     Evidence: {result['evidence_count']}, Unknowns: {result['unknown_count']}"
            )

        except Exception as e:
            print(f"  ❌ Error: {e}")
            all_results["demos"].append({"ops_file": ops_path.name, "error": str(e)})

    # Save summary
    summary_path = results_dir / "demo_results_summary.json"
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 60)
    print(f"Results saved to: {summary_path}")

    # Print summary table
    print("\n📊 Summary:")
    print("-" * 60)
    for demo in all_results["demos"]:
        name = demo.get("ops_file", "?")
        if "error" in demo:
            print(f"  ❌ {name}: ERROR")
        else:
            status = demo.get("contract_status", "?")
            conf = demo.get("contract_confidence", 0)
            unknowns = demo.get("unknown_count", 0)
            emoji = "✅" if "SATISFIED" in status else "⚠️"
            print(f"  {emoji} {name}: {status} (conf={conf:.2f}, unknowns={unknowns})")


if __name__ == "__main__":
    main()
