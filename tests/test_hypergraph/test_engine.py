"""Tests for hypergraph engine."""

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    EdgeType,
    Evidence,
    Intent,
    Node,
    NodeType,
    Unknown,
)
from src.hypergraph.store import HypergraphStore


class TestHypergraphEngine:
    """Tests for HypergraphEngine."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine for each test."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_engine_creation(self, engine):
        """Engine should be creatable with a store."""
        assert engine is not None
        assert len(engine.nodes) == 0
        assert len(engine.edges) == 0

    def test_add_node(self, engine):
        """Engine should add nodes and return node ID."""
        intent = Intent(
            id="intent_001",
            description="Test intent",
            goal="Test goal",
        )
        node_id = engine.add_node(intent)
        assert node_id == "intent_001"
        assert "intent_001" in engine.nodes

    def test_add_node_auto_id(self, engine):
        """Engine should generate ID if not provided."""
        node = Node(
            id="",  # Empty ID
            node_type=NodeType.CONTRACT,
            description="Test node",
        )
        node_id = engine.add_node(node)
        assert node_id is not None
        assert len(node_id) > 0
        assert node_id in engine.nodes

    def test_add_edge(self, engine):
        """Engine should add edges between nodes."""
        # Add nodes first
        intent = Intent(id="intent_001", description="Parent", goal="Goal")
        contract = Contract(
            id="contract_001",
            description="Child",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(intent)
        engine.add_node(contract)

        # Add edge
        edge_id = engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        assert edge_id is not None
        assert edge_id in engine.edges

    def test_add_edge_validates_nodes_exist(self, engine):
        """Engine should reject edges with non-existent nodes."""
        with pytest.raises(ValueError):
            engine.add_edge("nonexistent_1", "nonexistent_2", EdgeType.HAS_CHILD)

    def test_get_node(self, engine):
        """Engine should retrieve nodes by ID."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        retrieved = engine.get_node("intent_001")
        assert retrieved is not None
        assert retrieved.id == "intent_001"

    def test_get_node_not_found(self, engine):
        """Engine should return None for non-existent nodes."""
        retrieved = engine.get_node("nonexistent")
        assert retrieved is None

    def test_get_children(self, engine):
        """Engine should return child nodes."""
        # Create parent and children
        intent = Intent(id="intent_001", description="Parent", goal="Goal")
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)

        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        children = engine.get_children("intent_001")
        assert len(children) == 2
        child_ids = {c.id for c in children}
        assert "contract_001" in child_ids
        assert "contract_002" in child_ids

    def test_get_parents(self, engine):
        """Engine should return parent nodes."""
        intent = Intent(id="intent_001", description="Parent", goal="Goal")
        contract = Contract(
            id="contract_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        parents = engine.get_parents("contract_001")
        assert len(parents) == 1
        assert parents[0].id == "intent_001"

    def test_expand_node(self, engine):
        """Engine should expand a node with children."""
        intent = Intent(id="intent_001", description="Parent", goal="Goal")
        engine.add_node(intent)

        children = [
            Contract(
                id="contract_001",
                description="Child 1",
                inputs={},
                outputs={},
                guarantees=[],
            ),
            Contract(
                id="contract_002",
                description="Child 2",
                inputs={},
                outputs={},
                guarantees=[],
            ),
        ]

        child_ids = engine.expand("intent_001", children)
        assert len(child_ids) == 2

        # Children should be added
        assert "contract_001" in engine.nodes
        assert "contract_002" in engine.nodes

        # Edges should be created
        retrieved_children = engine.get_children("intent_001")
        assert len(retrieved_children) == 2

    def test_contract_nodes(self, engine):
        """Engine should contract multiple nodes into a parent."""
        # Add child nodes
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract1)
        engine.add_node(contract2)

        # Contract into parent
        parent_id = engine.contract(
            ["contract_001", "contract_002"],
            parent_description="Combined contract",
        )

        assert parent_id is not None
        assert parent_id in engine.nodes

        # Parent should have children
        children = engine.get_children(parent_id)
        assert len(children) == 2

    def test_commit_creates_version(self, engine):
        """Engine should support versioned commits."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        version = engine.commit("Initial commit")
        assert version is not None

    def test_get_edges_by_type(self, engine):
        """Engine should filter edges by type."""
        intent = Intent(id="intent_001", description="Parent", goal="Goal")
        contract = Contract(
            id="contract_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )
        evidence = Evidence(
            id="evidence_001",
            description="Test evidence",
            evidence_type="test",
            provenance="test provenance",
            data={},
        )

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_node(evidence)

        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("evidence_001", "contract_001", EdgeType.VALIDATES)

        has_child_edges = engine.get_edges_by_type(EdgeType.HAS_CHILD)
        validates_edges = engine.get_edges_by_type(EdgeType.VALIDATES)

        assert len(has_child_edges) == 1
        assert len(validates_edges) == 1
        assert has_child_edges[0].edge_type == EdgeType.HAS_CHILD
        assert validates_edges[0].edge_type == EdgeType.VALIDATES

    def test_get_nodes_by_type(self, engine):
        """Engine should filter nodes by type."""
        intent = Intent(id="intent_001", description="Intent", goal="Goal")
        contract = Contract(
            id="contract_001",
            description="Contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        unknown = Unknown(id="unknown_001", description="Unknown", reason="Test")

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_node(unknown)

        intents = engine.get_nodes_by_type(NodeType.INTENT)
        contracts = engine.get_nodes_by_type(NodeType.CONTRACT)
        unknowns = engine.get_nodes_by_type(NodeType.UNKNOWN)

        assert len(intents) == 1
        assert len(contracts) == 1
        assert len(unknowns) == 1

    def test_remove_node(self, engine):
        """Engine should remove nodes and their edges."""
        intent = Intent(id="intent_001", description="Parent", goal="Goal")
        contract = Contract(
            id="contract_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )
        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        engine.remove_node("contract_001")

        assert "contract_001" not in engine.nodes
        # Edge should also be removed
        assert len(engine.get_children("intent_001")) == 0

    def test_update_node(self, engine):
        """Engine should update node properties."""
        contract = Contract(
            id="contract_001",
            description="Original",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.5,
        )
        engine.add_node(contract)

        engine.update_node("contract_001", confidence=0.9)

        updated = engine.get_node("contract_001")
        assert updated.confidence == 0.9

    def test_persistence_round_trip(self, engine):
        """Engine should persist and reload graph."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        contract = Contract(
            id="contract_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )
        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        # Save
        engine.save()

        # Create new engine from same store
        new_engine = HypergraphEngine(engine.store)
        new_engine.load()

        assert "intent_001" in new_engine.nodes
        assert "contract_001" in new_engine.nodes
        assert len(new_engine.get_children("intent_001")) == 1

    def test_get_root_nodes(self, engine):
        """Engine should return nodes with no parents."""
        intent = Intent(id="intent_001", description="Root", goal="Goal")
        contract = Contract(
            id="contract_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )
        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        roots = engine.get_root_nodes()
        assert len(roots) == 1
        assert roots[0].id == "intent_001"

    def test_get_leaf_nodes(self, engine):
        """Engine should return nodes with no children."""
        intent = Intent(id="intent_001", description="Root", goal="Goal")
        contract = Contract(
            id="contract_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )
        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        leaves = engine.get_leaf_nodes()
        assert len(leaves) == 1
        assert leaves[0].id == "contract_001"
