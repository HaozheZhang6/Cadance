"""Tests for hypergraph JSON persistence."""

import json

from src.hypergraph.models import (
    Contract,
    Edge,
    EdgeType,
    Intent,
    Node,
    NodeType,
    Unknown,
)
from src.hypergraph.store import HypergraphStore


class TestHypergraphStore:
    """Tests for HypergraphStore."""

    def test_store_creation(self, tmp_path):
        """Store should be creatable with a path."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        assert store.path == store_path

    def test_store_save_empty_graph(self, tmp_path):
        """Store should save empty graph."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        store.save(nodes={}, edges={})
        assert store_path.exists()

    def test_store_load_empty_graph(self, tmp_path):
        """Store should load empty graph from non-existent file."""
        store_path = tmp_path / "nonexistent.json"
        store = HypergraphStore(store_path)
        nodes, edges = store.load()
        assert nodes == {}
        assert edges == {}

    def test_store_save_and_load_nodes(self, tmp_path):
        """Store should save and load nodes correctly."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
        )
        nodes = {"intent_001": intent}
        store.save(nodes=nodes, edges={})

        loaded_nodes, loaded_edges = store.load()
        assert "intent_001" in loaded_nodes
        assert loaded_nodes["intent_001"].id == "intent_001"
        assert loaded_nodes["intent_001"].node_type == NodeType.INTENT

    def test_store_save_and_load_edges(self, tmp_path):
        """Store should save and load edges correctly."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        edge = Edge(
            id="edge_001",
            source_id="node_001",
            target_id="node_002",
            edge_type=EdgeType.HAS_CHILD,
        )
        edges = {"edge_001": edge}
        store.save(nodes={}, edges=edges)

        loaded_nodes, loaded_edges = store.load()
        assert "edge_001" in loaded_edges
        assert loaded_edges["edge_001"].source_id == "node_001"
        assert loaded_edges["edge_001"].edge_type == EdgeType.HAS_CHILD

    def test_store_preserves_node_types(self, tmp_path):
        """Store should preserve specialized node types."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
            constraints=["constraint1"],
        )
        contract = Contract(
            id="contract_001",
            description="Test contract",
            inputs={"input1": "desc1"},
            outputs={"output1": "desc2"},
            guarantees=["guarantee1"],
        )
        unknown = Unknown(
            id="unknown_001",
            description="Test unknown",
            reason="Test reason",
            candidates=["opt1", "opt2"],
        )

        nodes = {
            "intent_001": intent,
            "contract_001": contract,
            "unknown_001": unknown,
        }
        store.save(nodes=nodes, edges={})

        loaded_nodes, _ = store.load()

        # Check Intent
        loaded_intent = loaded_nodes["intent_001"]
        assert loaded_intent.node_type == NodeType.INTENT
        assert hasattr(loaded_intent, "goal")
        assert loaded_intent.goal == "Test goal"

        # Check Contract
        loaded_contract = loaded_nodes["contract_001"]
        assert loaded_contract.node_type == NodeType.CONTRACT
        assert hasattr(loaded_contract, "guarantees")

        # Check Unknown
        loaded_unknown = loaded_nodes["unknown_001"]
        assert loaded_unknown.node_type == NodeType.UNKNOWN
        assert hasattr(loaded_unknown, "candidates")

    def test_store_creates_directory(self, tmp_path):
        """Store should create parent directories if they don't exist."""
        store_path = tmp_path / "nested" / "dir" / "test_graph.json"
        store = HypergraphStore(store_path)

        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
        )
        store.save(nodes={"intent_001": intent}, edges={})

        assert store_path.exists()
        assert store_path.parent.exists()

    def test_store_json_is_readable(self, tmp_path):
        """Store should produce human-readable JSON."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
        )
        store.save(nodes={"intent_001": intent}, edges={})

        # Should be readable as JSON
        with open(store_path) as f:
            data = json.load(f)
            assert "nodes" in data
            assert "edges" in data
            assert "intent_001" in data["nodes"]

    def test_store_handles_metadata(self, tmp_path):
        """Store should preserve node/edge metadata."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        node = Node(
            id="node_001",
            node_type=NodeType.CONTRACT,
            description="Test node",
            metadata={"key": "value", "nested": {"inner": 1}},
        )
        store.save(nodes={"node_001": node}, edges={})

        loaded_nodes, _ = store.load()
        assert loaded_nodes["node_001"].metadata == {
            "key": "value",
            "nested": {"inner": 1},
        }

    def test_store_versioned_commits(self, tmp_path):
        """Store should support versioned commits with metadata."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
        )
        # Save with version metadata
        store.save(
            nodes={"intent_001": intent},
            edges={},
            version="v1",
            commit_message="Initial commit",
        )

        # Load should include version info
        nodes, edges, metadata = store.load_with_metadata()
        assert metadata.get("version") == "v1"
        assert metadata.get("commit_message") == "Initial commit"
