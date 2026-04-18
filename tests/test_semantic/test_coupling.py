"""Tests for coupling registry with REFINES/ALIASES edges."""

import dataclasses

import pytest

from src.hypergraph.models import EdgeType
from src.verification.semantic.coupling import (
    CouplingRegistry,
    create_alias_edge,
    create_refines_edge,
)
from src.verification.semantic.scoped_symbol_table import ScopedKey


class TestCouplingEdgeFactory:
    """Tests for create_refines_edge factory."""

    def test_create_refines_edge_valid(self):
        """Factory creates valid CouplingEdge with REFINES type."""
        key = ScopedKey("bracket", "normal", "plate_thickness")
        edge = create_refines_edge(
            source_spec_id="spec_002",
            target_spec_id="spec_001",
            scoped_key=key,
            justification="Tighter tolerance from manufacturing constraint",
        )

        assert edge.source_spec_id == "spec_002"
        assert edge.target_spec_id == "spec_001"
        assert edge.edge_type == EdgeType.REFINES
        assert edge.scoped_key == key
        assert edge.justification == "Tighter tolerance from manufacturing constraint"
        assert edge.created_by == "contract"  # default

    def test_create_refines_edge_with_user_creator(self):
        """Factory accepts user as creator."""
        key = ScopedKey("bracket", "normal", "hole_diameter")
        edge = create_refines_edge(
            source_spec_id="spec_003",
            target_spec_id="spec_001",
            scoped_key=key,
            justification="User override",
            created_by="user",
        )
        assert edge.created_by == "user"


class TestAliasEdgeFactory:
    """Tests for create_alias_edge factory."""

    def test_create_alias_edge_valid(self):
        """Factory creates valid AliasEdge."""
        k1 = ScopedKey("bracket", "normal", "plate_thickness")
        k2 = ScopedKey("housing", "normal", "plate_thickness")
        edge = create_alias_edge(
            source_key=k1,
            target_key=k2,
            justification="Same physical part",
            created_by="user",
        )

        assert edge.source_key == k1
        assert edge.target_key == k2
        assert edge.justification == "Same physical part"
        assert edge.created_by == "user"

    def test_create_alias_edge_rejects_llm(self):
        """Factory rejects created_by='llm' (CPL-02)."""
        k1 = ScopedKey("a", "b", "c")
        k2 = ScopedKey("d", "e", "c")
        with pytest.raises(ValueError, match="cannot be created by LLM"):
            create_alias_edge(k1, k2, "auto-detected similarity", "llm")

    def test_create_alias_edge_accepts_contract(self):
        """Factory accepts contract as creator."""
        k1 = ScopedKey("bracket", "normal", "mass")
        k2 = ScopedKey("bracket", "shock", "mass")
        edge = create_alias_edge(
            source_key=k1,
            target_key=k2,
            justification="Mass invariant across regimes",
            created_by="contract",
        )
        assert edge.created_by == "contract"


class TestCouplingEdgeImmutable:
    """Tests for dataclass immutability."""

    def test_coupling_edge_immutable(self):
        """CouplingEdge is frozen (immutable)."""
        key = ScopedKey("bracket", "normal", "plate_thickness")
        edge = create_refines_edge("s1", "s2", key, "reason")
        with pytest.raises(dataclasses.FrozenInstanceError):
            edge.source_spec_id = "s3"

    def test_alias_edge_immutable(self):
        """AliasEdge is frozen (immutable)."""
        k1 = ScopedKey("a", "b", "c")
        k2 = ScopedKey("d", "e", "f")
        edge = create_alias_edge(k1, k2, "reason", "user")
        with pytest.raises(dataclasses.FrozenInstanceError):
            edge.justification = "changed"


class TestCouplingRegistry:
    """Tests for CouplingRegistry."""

    def test_registry_add_and_query_refines(self):
        """Registry stores and retrieves REFINES edges."""
        registry = CouplingRegistry()
        key = ScopedKey("bracket", "normal", "plate_thickness")
        edge = create_refines_edge("spec_002", "spec_001", key, "tighter bounds")

        registry.add_refines(edge)

        assert registry.refines_count == 1
        edges = registry.get_refines_for_spec("spec_001")
        assert len(edges) == 1
        assert edges[0] == edge

    def test_registry_add_and_query_aliases(self):
        """Registry stores and retrieves ALIASES edges."""
        registry = CouplingRegistry()
        k1 = ScopedKey("bracket", "normal", "plate_thickness")
        k2 = ScopedKey("housing", "normal", "plate_thickness")
        edge = create_alias_edge(k1, k2, "same part", "user")

        registry.add_alias(edge)

        assert registry.aliases_count == 1
        aliased = registry.get_aliases_for_key(k1)
        assert len(aliased) == 1
        assert aliased[0] == k2

    def test_registry_get_aliases_bidirectional(self):
        """Alias lookup works from either direction."""
        registry = CouplingRegistry()
        k1 = ScopedKey("bracket", "normal", "mass")
        k2 = ScopedKey("bracket", "shock", "mass")
        edge = create_alias_edge(k1, k2, "mass invariant", "contract")

        registry.add_alias(edge)

        # Query from source
        aliased_from_k1 = registry.get_aliases_for_key(k1)
        assert k2 in aliased_from_k1

        # Query from target
        aliased_from_k2 = registry.get_aliases_for_key(k2)
        assert k1 in aliased_from_k2

    def test_registry_get_refines_for_spec_source_or_target(self):
        """get_refines_for_spec finds edges where spec is source or target."""
        registry = CouplingRegistry()
        key = ScopedKey("bracket", "normal", "hole_diameter")

        # spec_002 refines spec_001
        edge1 = create_refines_edge("spec_002", "spec_001", key, "tighter")
        # spec_003 refines spec_002
        edge2 = create_refines_edge("spec_003", "spec_002", key, "even tighter")

        registry.add_refines(edge1)
        registry.add_refines(edge2)

        # spec_002 appears in both edges
        edges_002 = registry.get_refines_for_spec("spec_002")
        assert len(edges_002) == 2
        assert edge1 in edges_002
        assert edge2 in edges_002

    def test_registry_resolve_unified_key_no_aliases(self):
        """resolve_unified_key returns original if no aliases."""
        registry = CouplingRegistry()
        key = ScopedKey("bracket", "normal", "plate_thickness")

        resolved = registry.resolve_unified_key(key)
        assert resolved == key

    def test_registry_resolve_unified_key_deterministic(self):
        """resolve_unified_key returns lexicographically smallest key."""
        registry = CouplingRegistry()
        # z_entity comes after a_entity lexicographically
        k1 = ScopedKey("z_entity", "normal", "mass")
        k2 = ScopedKey("a_entity", "normal", "mass")
        edge = create_alias_edge(k1, k2, "same quantity", "user")
        registry.add_alias(edge)

        # Both should resolve to k2 (a_entity... < z_entity...)
        resolved1 = registry.resolve_unified_key(k1)
        resolved2 = registry.resolve_unified_key(k2)

        assert resolved1 == k2
        assert resolved2 == k2
        # Determinism: same result regardless of query order
        assert resolved1 == resolved2

    def test_registry_empty_counts(self):
        """New registry has zero counts."""
        registry = CouplingRegistry()
        assert registry.refines_count == 0
        assert registry.aliases_count == 0
