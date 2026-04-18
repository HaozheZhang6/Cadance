"""Tests for uncertainty propagation."""

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    Contract,
    EdgeType,
    Intent,
    Unknown,
)
from src.hypergraph.store import HypergraphStore
from src.uncertainty.propagation import UncertaintyPropagator


class TestUncertaintyPropagator:
    """Tests for UncertaintyPropagator."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine for each test."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def propagator(self, engine):
        """Create propagator instance."""
        return UncertaintyPropagator(engine)

    def test_propagator_creation(self, propagator):
        """Propagator should be creatable."""
        assert propagator is not None

    def test_weakest_link_rule(self, propagator, engine):
        """Parent confidence should be bounded by min child confidence."""
        # Create parent and children
        intent = Intent(
            id="intent_001",
            description="Parent",
            goal="Goal",
            confidence=1.0,  # Will be reduced
        )
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.5,  # Weakest link
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        computed = propagator.compute_confidence("intent_001")
        assert computed <= 0.5  # Bounded by weakest child

    def test_interface_penalty(self, propagator, engine):
        """More children should apply a slight confidence penalty."""
        intent = Intent(
            id="intent_001",
            description="Parent with many children",
            goal="Goal",
            confidence=1.0,
        )
        engine.add_node(intent)

        # Add 5 children all with same confidence
        for i in range(5):
            contract = Contract(
                id=f"contract_{i:03d}",
                description=f"Child {i}",
                inputs={},
                outputs={},
                guarantees=[],
                confidence=0.8,
            )
            engine.add_node(contract)
            engine.add_edge("intent_001", f"contract_{i:03d}", EdgeType.HAS_CHILD)

        computed = propagator.compute_confidence("intent_001")
        # Should be < 0.8 due to interface penalty
        assert computed < 0.8

    def test_unknown_cap(self, propagator, engine):
        """Child with confidence < 0.3 should cap parent at 0.5."""
        intent = Intent(
            id="intent_001",
            description="Parent",
            goal="Goal",
            confidence=1.0,
        )
        contract = Contract(
            id="contract_001",
            description="Confident child",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.9,
        )
        unknown = Unknown(
            id="unknown_001",
            description="Uncertain child",
            reason="Unknown",
            confidence=0.2,  # Below 0.3 threshold
        )

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_node(unknown)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "unknown_001", EdgeType.HAS_CHILD)

        computed = propagator.compute_confidence("intent_001")
        assert computed <= 0.5  # Capped due to unknown

    def test_leaf_node_unchanged(self, propagator, engine):
        """Leaf nodes should keep their original confidence."""
        contract = Contract(
            id="contract_001",
            description="Leaf node",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.75,
        )
        engine.add_node(contract)

        computed = propagator.compute_confidence("contract_001")
        assert computed == 0.75

    def test_propagate_all(self, propagator, engine):
        """Propagator should update all node confidences."""
        # Create hierarchy
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
            confidence=1.0,
        )
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.6,
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        results = propagator.propagate_all()

        assert "intent_001" in results
        assert results["intent_001"] <= 0.6

    def test_get_confidence_tree(self, propagator, engine):
        """Propagator should return confidence tree structure."""
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
            confidence=1.0,
        )
        contract = Contract(
            id="contract_001",
            description="Child",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.7,
        )

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        tree = propagator.get_confidence_tree("intent_001")

        assert tree["id"] == "intent_001"
        assert "computed_confidence" in tree
        assert "children" in tree
        assert len(tree["children"]) == 1
        assert tree["children"][0]["id"] == "contract_001"

    def test_deep_hierarchy_propagation(self, propagator, engine):
        """Propagation should work through deep hierarchies."""
        # Create 3-level hierarchy
        intent = Intent(
            id="intent_001",
            description="Level 1",
            goal="Goal",
            confidence=1.0,
        )
        contract1 = Contract(
            id="contract_001",
            description="Level 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=1.0,
        )
        contract2 = Contract(
            id="contract_002",
            description="Level 3",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.6,
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("contract_001", "contract_002", EdgeType.HAS_CHILD)

        # Level 2 should be bounded by level 3
        level2_confidence = propagator.compute_confidence("contract_001")
        assert level2_confidence <= 0.6

        # Level 1 should be bounded by level 2
        level1_confidence = propagator.compute_confidence("intent_001")
        assert level1_confidence <= level2_confidence

    def test_suggest_improvements(self, propagator, engine):
        """Propagator should suggest improvements for low confidence."""
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
            confidence=1.0,
        )
        unknown = Unknown(
            id="unknown_001",
            description="Uncertain",
            reason="Needs analysis",
            confidence=0.2,
        )

        engine.add_node(intent)
        engine.add_node(unknown)
        engine.add_edge("intent_001", "unknown_001", EdgeType.HAS_CHILD)

        suggestions = propagator.suggest_improvements("intent_001")

        assert len(suggestions) > 0
        assert any("unknown_001" in s["node_id"] for s in suggestions)


class TestMemoization:
    """Tests for memoization in uncertainty propagation."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine for each test."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def propagator(self, engine):
        """Create propagator instance."""
        return UncertaintyPropagator(engine)

    def test_memoization_prevents_recomputation(self, propagator, engine):
        """Same node should not be recomputed multiple times."""
        # Create a tree where we call compute_confidence multiple times
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
            confidence=1.0,
        )
        contract = Contract(
            id="contract_001",
            description="Child",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )

        engine.add_node(intent)
        engine.add_node(contract)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)

        # Use shared cache
        cache: dict[str, float] = {}
        result1 = propagator.compute_confidence("intent_001", _cache=cache)
        result2 = propagator.compute_confidence("intent_001", _cache=cache)

        assert result1 == result2
        # Both nodes should be cached
        assert "intent_001" in cache
        assert "contract_001" in cache

    def test_propagate_all_uses_memoization(self, propagator, engine):
        """propagate_all should use memoization internally."""
        # Create tree with shared subtree pattern
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
            confidence=1.0,
        )
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.7,
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        # propagate_all should work efficiently
        results = propagator.propagate_all()

        assert len(results) == 3
        assert "intent_001" in results
        assert "contract_001" in results
        assert "contract_002" in results


class TestCycleDetection:
    """Tests for cycle detection in uncertainty propagation."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine for each test."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def propagator(self, engine):
        """Create propagator instance."""
        return UncertaintyPropagator(engine)

    def test_cycle_detection_raises_error(self, propagator, engine):
        """Cycle in graph should raise ValueError."""
        # Create nodes
        contract1 = Contract(
            id="contract_001",
            description="Node A",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Node B",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.7,
        )
        contract3 = Contract(
            id="contract_003",
            description="Node C",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.6,
        )

        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_node(contract3)

        # Create cycle: A -> B -> C -> A
        engine.add_edge("contract_001", "contract_002", EdgeType.HAS_CHILD)
        engine.add_edge("contract_002", "contract_003", EdgeType.HAS_CHILD)
        engine.add_edge("contract_003", "contract_001", EdgeType.HAS_CHILD)

        with pytest.raises(ValueError, match="[Cc]ycle"):
            propagator.compute_confidence("contract_001")

    def test_self_loop_raises_error(self, propagator, engine):
        """Self-referencing node should raise ValueError."""
        contract = Contract(
            id="contract_001",
            description="Self-loop",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )

        engine.add_node(contract)
        # Create self-loop
        engine.add_edge("contract_001", "contract_001", EdgeType.HAS_CHILD)

        with pytest.raises(ValueError, match="[Cc]ycle"):
            propagator.compute_confidence("contract_001")

    def test_no_false_positive_on_dag(self, propagator, engine):
        """DAG without cycles should work normally."""
        # Create simple tree (no cycles)
        intent = Intent(
            id="intent_001",
            description="Root",
            goal="Goal",
            confidence=1.0,
        )
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.7,
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        # Should not raise
        result = propagator.compute_confidence("intent_001")
        assert result > 0
