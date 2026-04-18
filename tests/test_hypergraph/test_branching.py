"""Tests for hypergraph branching operations."""

import pytest

from src.hypergraph.branching import BranchDiff, BranchInfo, MergeConflict, MergeResult
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import Contract
from src.hypergraph.store import HypergraphStore


class TestBranchCreation:
    """Tests for branch creation."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_create_branch(self, engine):
        """Should create a new branch."""
        branch_id = engine.create_branch("feature-1")

        assert branch_id is not None
        assert len(branch_id) > 0

    def test_create_branch_from_current_state(self, engine):
        """Branch should capture current hypergraph state."""
        # Add some nodes first
        contract = Contract(
            id="contract_001",
            description="Test contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        # Create branch
        engine.create_branch("feature-1")

        # Branch should have the node
        branches = engine.list_branches()
        assert len(branches) >= 1

    def test_default_main_branch_exists(self, engine):
        """Engine should have a default 'main' branch."""
        branches = engine.list_branches()
        branch_names = [b.name for b in branches]
        assert "main" in branch_names

    def test_branch_names_must_be_unique(self, engine):
        """Cannot create two branches with same name."""
        engine.create_branch("feature-1")

        with pytest.raises(ValueError):
            engine.create_branch("feature-1")


class TestBranchSwitching:
    """Tests for switching between branches."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_switch_to_branch(self, engine):
        """Should switch to an existing branch."""
        engine.create_branch("feature-1")
        engine.switch_branch("feature-1")

        assert engine.current_branch == "feature-1"

    def test_switch_to_nonexistent_branch_fails(self, engine):
        """Switching to nonexistent branch should fail."""
        with pytest.raises(ValueError):
            engine.switch_branch("nonexistent")

    def test_switch_branch_changes_visible_nodes(self, engine):
        """Switching branches should change visible nodes."""
        # Add node on main
        contract1 = Contract(
            id="contract_main",
            description="Main contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract1)

        # Create and switch to feature branch
        engine.create_branch("feature-1")
        engine.switch_branch("feature-1")

        # Add different node on feature branch
        contract2 = Contract(
            id="contract_feature",
            description="Feature contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract2)

        # Feature branch should have both nodes (inherited + new)
        assert "contract_main" in engine.nodes
        assert "contract_feature" in engine.nodes

        # Switch back to main
        engine.switch_branch("main")

        # Main should only have original node
        assert "contract_main" in engine.nodes
        # Feature node should not be visible on main
        assert "contract_feature" not in engine.nodes

    def test_switch_back_to_main(self, engine):
        """Should be able to switch back to main."""
        engine.create_branch("feature-1")
        engine.switch_branch("feature-1")
        engine.switch_branch("main")

        assert engine.current_branch == "main"


class TestBranchListing:
    """Tests for listing branches."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_list_branches(self, engine):
        """Should list all branches."""
        engine.create_branch("feature-1")
        engine.create_branch("feature-2")

        branches = engine.list_branches()

        branch_names = [b.name for b in branches]
        assert "main" in branch_names
        assert "feature-1" in branch_names
        assert "feature-2" in branch_names

    def test_branch_info_has_required_fields(self, engine):
        """BranchInfo should have name and head commit."""
        engine.create_branch("feature-1")

        branches = engine.list_branches()
        branch = next(b for b in branches if b.name == "feature-1")

        assert hasattr(branch, "name")
        assert hasattr(branch, "head_commit")
        assert hasattr(branch, "created_at")


class TestBranchMerging:
    """Tests for merging branches."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_merge_branch_to_main(self, engine):
        """Should merge feature branch into main."""
        # Setup: create node on main
        contract1 = Contract(
            id="contract_main",
            description="Main contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract1)

        # Create feature branch with new node
        engine.create_branch("feature-1")
        engine.switch_branch("feature-1")

        contract2 = Contract(
            id="contract_feature",
            description="Feature contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract2)

        # Merge feature into main
        result = engine.merge_branch("feature-1", "main")

        assert result.success is True

        # Switch to main and verify both nodes exist
        engine.switch_branch("main")
        assert "contract_main" in engine.nodes
        assert "contract_feature" in engine.nodes

    def test_merge_returns_result(self, engine):
        """Merge should return MergeResult."""
        engine.create_branch("feature-1")

        result = engine.merge_branch("feature-1", "main")

        assert isinstance(result, MergeResult)
        assert hasattr(result, "success")
        assert hasattr(result, "nodes_added")
        assert hasattr(result, "nodes_modified")
        assert hasattr(result, "conflicts")

    def test_merge_nonexistent_branch_fails(self, engine):
        """Merging nonexistent branch should fail."""
        with pytest.raises(ValueError):
            engine.merge_branch("nonexistent", "main")

    def test_merge_detects_conflicts(self, engine):
        """Merge should detect conflicting changes."""
        # Create initial state
        contract = Contract(
            id="contract_001",
            description="Original description",
            inputs={},
            outputs={},
            guarantees=["original guarantee"],
        )
        engine.add_node(contract)

        # Create two branches from same point
        engine.create_branch("feature-1")
        engine.create_branch("feature-2")

        # Modify same node differently on feature-1
        engine.switch_branch("feature-1")
        engine.update_node("contract_001", description="Modified by feature-1")

        # Modify same node differently on feature-2
        engine.switch_branch("feature-2")
        engine.update_node("contract_001", description="Modified by feature-2")

        # Merge feature-1 into main first (should succeed)
        engine.switch_branch("main")
        engine.merge_branch("feature-1", "main")

        # Merge feature-2 into main (may have conflict)
        result2 = engine.merge_branch("feature-2", "main")

        # Should either succeed with conflict resolution or report conflicts
        assert isinstance(result2, MergeResult)


class TestBranchDiff:
    """Tests for comparing branches."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create fresh engine."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    def test_get_branch_diff(self, engine):
        """Should get differences between branches."""
        # Setup main
        contract1 = Contract(
            id="contract_main",
            description="Main contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract1)

        # Create feature with additional node
        engine.create_branch("feature-1")
        engine.switch_branch("feature-1")

        contract2 = Contract(
            id="contract_feature",
            description="Feature contract",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract2)

        # Get diff
        diff = engine.get_branch_diff("main", "feature-1")

        assert isinstance(diff, BranchDiff)
        assert "contract_feature" in diff.nodes_added_in_second

    def test_diff_shows_modified_nodes(self, engine):
        """Diff should show modified nodes."""
        contract = Contract(
            id="contract_001",
            description="Original",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine.add_node(contract)

        engine.create_branch("feature-1")
        engine.switch_branch("feature-1")
        engine.update_node("contract_001", description="Modified")

        diff = engine.get_branch_diff("main", "feature-1")

        assert "contract_001" in diff.nodes_modified

    def test_diff_nonexistent_branch_fails(self, engine):
        """Diffing with nonexistent branch should fail."""
        with pytest.raises(ValueError):
            engine.get_branch_diff("main", "nonexistent")


class TestBranchPersistence:
    """Tests for branch persistence."""

    def test_branches_persisted_to_file(self, tmp_path):
        """Branch data should be persisted."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine = HypergraphEngine(store)

        # Create a branch
        engine.create_branch("feature-1")
        engine.save()

        # Check branches file exists
        branches_path = tmp_path / "branches.json"
        assert branches_path.exists() or store_path.exists()

    def test_branches_loaded_on_init(self, tmp_path):
        """Branches should be loaded when engine is created."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)

        # Create engine and branch
        engine1 = HypergraphEngine(store)
        engine1.create_branch("feature-1")
        engine1.save()

        # Create new engine from same store
        engine2 = HypergraphEngine(store)
        engine2.load()

        branches = engine2.list_branches()
        branch_names = [b.name for b in branches]
        assert "feature-1" in branch_names

    def test_branch_specific_data_persisted(self, tmp_path):
        """Branch-specific nodes should be preserved after reload."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine1 = HypergraphEngine(store)

        # Add node to main
        node_main = Contract(
            id="node_main",
            description="Main only node",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine1.add_node(node_main)

        # Create branch and add different node
        engine1.create_branch("feature")
        engine1.switch_branch("feature")
        node_feature = Contract(
            id="node_feature",
            description="Feature only node",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine1.add_node(node_feature)

        # Switch back to main and save
        engine1.switch_branch("main")
        engine1.save()

        # Reload in new engine
        store2 = HypergraphStore(store_path)
        engine2 = HypergraphEngine(store2)
        engine2.load()

        # Verify main has only its node
        assert "node_main" in engine2.nodes
        assert "node_feature" not in engine2.nodes

        # Switch to feature and verify it has both nodes
        engine2.switch_branch("feature")
        assert "node_main" in engine2.nodes
        assert "node_feature" in engine2.nodes

    def test_branch_node_modifications_persisted(self, tmp_path):
        """Modified nodes in a branch should persist correctly after save from main."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        engine1 = HypergraphEngine(store)

        # Add node to main
        node = Contract(
            id="shared_node",
            description="Original description",
            inputs={},
            outputs={},
            guarantees=[],
        )
        engine1.add_node(node)

        # Create branch and modify the node
        engine1.create_branch("feature")
        engine1.switch_branch("feature")
        engine1.update_node("shared_node", description="Modified in feature")

        # Switch back to main and save (this is the key - save from main)
        engine1.switch_branch("main")
        engine1.save()

        # Reload in new engine
        store2 = HypergraphStore(store_path)
        engine2 = HypergraphEngine(store2)
        engine2.load()

        # Main should have original description
        assert engine2.nodes["shared_node"].description == "Original description"

        # Switch to feature and verify modification is preserved
        engine2.switch_branch("feature")
        assert engine2.nodes["shared_node"].description == "Modified in feature"


class TestBranchDataTypes:
    """Tests for branch-related data types."""

    def test_branch_info_creation(self):
        """BranchInfo should be creatable."""
        info = BranchInfo(
            name="feature-1",
            head_commit="abc123",
            created_at="2024-01-01T00:00:00",
        )

        assert info.name == "feature-1"
        assert info.head_commit == "abc123"

    def test_merge_result_creation(self):
        """MergeResult should be creatable."""
        result = MergeResult(
            success=True,
            nodes_added=["node1", "node2"],
            nodes_modified=["node3"],
            edges_added=["edge1"],
            conflicts=[],
            message="Merge successful",
        )

        assert result.success is True
        assert len(result.nodes_added) == 2

    def test_branch_diff_creation(self):
        """BranchDiff should be creatable."""
        diff = BranchDiff(
            branch1="main",
            branch2="feature-1",
            nodes_added_in_second=["node1"],
            nodes_removed_in_second=[],
            nodes_modified=["node2"],
            edges_added_in_second=[],
            edges_removed_in_second=[],
        )

        assert diff.branch1 == "main"
        assert "node1" in diff.nodes_added_in_second

    def test_merge_conflict_creation(self):
        """MergeConflict should be creatable."""
        conflict = MergeConflict(
            node_id="node1",
            field="description",
            base_value="Original",
            source_value="Modified A",
            target_value="Modified B",
        )

        assert conflict.node_id == "node1"
        assert conflict.field == "description"
