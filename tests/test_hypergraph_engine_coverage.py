"""Tests for HypergraphEngine coverage - edge cases and branching."""

import json
from datetime import datetime

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    EdgeType,
    Intent,
)
from src.hypergraph.store import HypergraphStore


class TestHypergraphEngineEdgeCases:
    """Tests for HypergraphEngine edge cases."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_add_node_generates_id_when_empty(self, engine):
        """add_node should generate ID when node has empty ID."""
        intent = Intent(id="", description="Test", goal="Goal")
        node_id = engine.add_node(intent)

        assert node_id.startswith("intent_")
        assert len(node_id) > 7  # prefix + uuid

    def test_add_edge_with_nonexistent_target(self, engine):
        """add_edge should raise when target doesn't exist."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        with pytest.raises(ValueError, match="Target node.*does not exist"):
            engine.add_edge("intent_001", "nonexistent", EdgeType.HAS_CHILD)

    def test_expand_with_nonexistent_parent(self, engine):
        """expand should raise when parent doesn't exist."""
        child = Contract(
            id="child_001", description="Child", inputs={}, outputs={}, guarantees=[]
        )

        with pytest.raises(ValueError, match="does not exist"):
            engine.expand("nonexistent", [child])

    def test_contract_with_nonexistent_node(self, engine):
        """contract should raise when any node doesn't exist."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        with pytest.raises(ValueError, match="does not exist"):
            engine.contract(["intent_001", "nonexistent"], "Parent contract")

    def test_update_node_nonexistent(self, engine):
        """update_node should raise when node doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            engine.update_node("nonexistent", description="New description")

    def test_remove_node_already_removed(self, engine):
        """remove_node should silently handle already-removed node."""
        # Should not raise
        engine.remove_node("nonexistent")

    def test_get_children_with_no_children(self, engine):
        """get_children should return empty list for node with no children."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        children = engine.get_children("intent_001")
        assert children == []

    def test_get_parents_with_no_parents(self, engine):
        """get_parents should return empty list for node with no parents."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        parents = engine.get_parents("intent_001")
        assert parents == []


class TestHypergraphEngineBranching:
    """Tests for HypergraphEngine branching operations."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_create_branch_duplicate_raises(self, engine):
        """create_branch should raise for duplicate branch name."""
        engine.create_branch("feature")

        with pytest.raises(ValueError, match="already exists"):
            engine.create_branch("feature")

    def test_switch_branch_nonexistent_raises(self, engine):
        """switch_branch should raise for nonexistent branch."""
        with pytest.raises(ValueError, match="does not exist"):
            engine.switch_branch("nonexistent")

    def test_merge_branch_nonexistent_source_raises(self, engine):
        """merge_branch should raise for nonexistent source branch."""
        with pytest.raises(ValueError, match="Source branch.*does not exist"):
            engine.merge_branch("nonexistent", "main")

    def test_merge_branch_nonexistent_target_raises(self, engine):
        """merge_branch should raise for nonexistent target branch."""
        engine.create_branch("feature")

        with pytest.raises(ValueError, match="Target branch.*does not exist"):
            engine.merge_branch("feature", "nonexistent")

    def test_get_branch_diff_nonexistent_branch1_raises(self, engine):
        """get_branch_diff should raise for nonexistent branch1."""
        with pytest.raises(ValueError, match="does not exist"):
            engine.get_branch_diff("nonexistent", "main")

    def test_get_branch_diff_nonexistent_branch2_raises(self, engine):
        """get_branch_diff should raise for nonexistent branch2."""
        engine.create_branch("feature")

        with pytest.raises(ValueError, match="does not exist"):
            engine.get_branch_diff("feature", "nonexistent")

    def test_branch_preserves_state_on_switch(self, engine):
        """Switching branches should preserve and restore state."""
        # Add node on main
        intent = Intent(id="intent_001", description="Main intent", goal="Goal")
        engine.add_node(intent)

        # Create and switch to feature branch
        engine.create_branch("feature")
        engine.switch_branch("feature")

        # Add different node on feature
        contract = Contract(
            id="contract_001",
            description="Feature contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Switch back to main
        engine.switch_branch("main")

        # Main should only have intent
        assert "intent_001" in engine.nodes
        assert "contract_001" not in engine.nodes

        # Switch to feature
        engine.switch_branch("feature")

        # Feature should have both (inherited + new)
        assert "intent_001" in engine.nodes
        assert "contract_001" in engine.nodes

    def test_merge_branch_adds_new_nodes(self, engine):
        """merge_branch should add nodes from source to target."""
        # Add base node on main
        intent = Intent(id="intent_001", description="Main", goal="Goal")
        engine.add_node(intent)

        # Create feature branch and add node
        engine.create_branch("feature")
        engine.switch_branch("feature")
        contract = Contract(
            id="contract_001",
            description="Feature",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Merge feature into main
        result = engine.merge_branch("feature", "main")

        assert result.success is True
        assert "contract_001" in result.nodes_added

        # Switch to main and verify
        engine.switch_branch("main")
        assert "contract_001" in engine.nodes

    def test_merge_branch_detects_conflicts(self, engine):
        """merge_branch should detect and resolve conflicts."""
        # Add node on main
        intent = Intent(id="intent_001", description="Original", goal="Goal")
        engine.add_node(intent)

        # Create feature and modify the node
        engine.create_branch("feature")
        engine.switch_branch("feature")
        engine.update_node("intent_001", description="Modified in feature")

        # Modify same node on main
        engine.switch_branch("main")
        engine.update_node("intent_001", description="Modified in main")

        # Merge feature into main (source wins)
        result = engine.merge_branch("feature", "main")

        assert result.success is True
        assert len(result.conflicts) > 0
        assert "intent_001" in result.nodes_modified

    def test_get_branch_diff_shows_differences(self, engine):
        """get_branch_diff should show node/edge differences."""
        # Add node on main
        intent = Intent(id="intent_001", description="Main", goal="Goal")
        engine.add_node(intent)

        # Create feature and add different node
        engine.create_branch("feature")
        engine.switch_branch("feature")
        contract = Contract(
            id="contract_001",
            description="Feature",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Get diff
        diff = engine.get_branch_diff("main", "feature")

        assert "contract_001" in diff.nodes_added_in_second

    def test_list_branches_returns_all(self, engine):
        """list_branches should return all branch info."""
        engine.create_branch("feature1")
        engine.create_branch("feature2")

        branches = engine.list_branches()
        branch_names = [b.name for b in branches]

        assert "main" in branch_names
        assert "feature1" in branch_names
        assert "feature2" in branch_names
        assert len(branches) == 3


class TestHypergraphEnginePersistence:
    """Tests for HypergraphEngine save/load with branches."""

    def test_save_and_load_preserves_branches(self, tmp_path):
        """save() and load() should preserve branch state."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        # Add node and create branch
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)
        engine.create_branch("feature")

        # Save
        engine.save()

        # Create new engine and load
        store2 = HypergraphStore(store_path)
        engine2 = HypergraphEngine(store2)
        engine2.load()

        branches = engine2.list_branches()
        branch_names = [b.name for b in branches]

        assert "main" in branch_names
        assert "feature" in branch_names

    def test_load_handles_missing_branch_file(self, tmp_path):
        """load() should handle missing individual branch file."""
        store_path = tmp_path / "test_graph.json"
        branches_path = tmp_path / "branches.json"
        branches_dir = tmp_path / "branches"

        # Create minimal branch metadata
        branches_dir.mkdir()
        branches_metadata = {
            "main": {
                "name": "main",
                "head_commit": "initial",
                "created_at": datetime.now().isoformat(),
                "parent_branch": None,
            },
            "orphan": {
                "name": "orphan",
                "head_commit": "orphan_commit",
                "created_at": datetime.now().isoformat(),
                "parent_branch": "main",
            },
        }

        with open(branches_path, "w") as f:
            json.dump(branches_metadata, f)

        # Create main branch file but not orphan
        main_branch_file = branches_dir / "main.json"
        with open(main_branch_file, "w") as f:
            json.dump({"nodes": {}, "edges": {}}, f)

        # Create empty store file
        with open(store_path, "w") as f:
            json.dump({"nodes": {}, "edges": {}}, f)

        # Load should handle missing orphan.json
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)
        engine.load()

        branches = engine.list_branches()
        assert len(branches) == 2


class TestHypergraphEngineDeserialization:
    """Tests for node/edge deserialization."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_deserialize_node_with_string_datetime(self, engine):
        """_deserialize_node should parse string datetime."""
        node_data = {
            "id": "intent_001",
            "node_type": "intent",
            "description": "Test",
            "goal": "Goal",
            "created_at": "2024-01-01T12:00:00",
            "confidence": 1.0,
            "metadata": {},
        }

        node = engine._deserialize_node(node_data)

        assert node.id == "intent_001"
        assert isinstance(node.created_at, datetime)

    def test_deserialize_edge_with_string_datetime(self, engine):
        """_deserialize_edge should parse string datetime."""
        edge_data = {
            "id": "edge_001",
            "source_id": "a",
            "target_id": "b",
            "edge_type": "has_child",
            "created_at": "2024-01-01T12:00:00",
            "metadata": {},
        }

        edge = engine._deserialize_edge(edge_data)

        assert edge.id == "edge_001"
        assert edge.edge_type == EdgeType.HAS_CHILD
        assert isinstance(edge.created_at, datetime)


class TestHypergraphEngineCommit:
    """Tests for commit operation."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_commit_increments_version(self, engine):
        """commit should increment version counter."""
        v1 = engine.commit("First commit")
        v2 = engine.commit("Second commit")

        assert v1 == "v1"
        assert v2 == "v2"

    def test_commit_saves_state(self, engine):
        """commit should persist state to store."""
        intent = Intent(id="intent_001", description="Test", goal="Goal")
        engine.add_node(intent)

        engine.commit("Add intent")

        # Reload and verify
        engine2 = HypergraphEngine(engine.store)
        engine2.load()

        assert "intent_001" in engine2.nodes
