"""Tests for OntologyStore."""

import tempfile
from pathlib import Path

import pytest

from src.ontology import (
    ConfidenceSource,
    EntityType,
    FailureMode,
    MaterialEntity,
    OntologyRelation,
    OntologyStore,
    PartEntity,
    PhysicsPhenomenon,
    RelationType,
)


@pytest.fixture
def store():
    """Create empty ontology store."""
    return OntologyStore()


@pytest.fixture
def populated_store():
    """Create store with sample entities."""
    store = OntologyStore()

    # Add parts
    bracket = PartEntity(
        id="part-bracket-001",
        name="Mounting Bracket",
        description="Steel mounting bracket for 5kg loads",
        category="bracket",
        typical_materials=["steel", "aluminum"],
        standards=["ISO 4762"],
        confidence=0.85,
        source="test",
        source_type=ConfidenceSource.DATASHEET,
        tags=["structural", "mounting"],
    )
    store.add_entity(bracket)

    fastener = PartEntity(
        id="part-fastener-001",
        name="M8 Socket Head Cap Screw",
        description="Metric socket head cap screw",
        category="fastener",
        typical_materials=["steel"],
        standards=["ISO 4762", "DIN 912"],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.STANDARD,
        tags=["fastener", "metric"],
    )
    store.add_entity(fastener)

    # Add materials
    steel = MaterialEntity(
        id="mat-steel-001",
        name="1020 Steel",
        description="Low carbon steel",
        category="metal",
        mechanical_properties={
            "yield_strength": {"value": 350, "unit": "MPa"},
            "tensile_strength": {"value": 420, "unit": "MPa"},
        },
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(steel)

    # Add failure modes
    fatigue = FailureMode(
        id="fm-fatigue-001",
        name="Fatigue Failure",
        description="Material failure due to cyclic loading",
        domain="mechanical",
        severity="high",
        causes=["cyclic loading", "stress concentration"],
        effects=["crack initiation", "fracture"],
        mitigations=["reduce stress concentration", "improve surface finish"],
        confidence=0.85,
        source="test",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(fatigue)

    # Add physics
    stress = PhysicsPhenomenon(
        id="phys-stress-001",
        name="Stress Concentration",
        description="Localized increase in stress",
        domain="mechanical",
        parameters=["stress concentration factor", "notch radius"],
        keywords=["stress", "notch", "fillet", "corner"],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(stress)

    # Add relations
    rel1 = OntologyRelation(
        id="rel-001",
        relation_type=RelationType.MADE_OF,
        source_id="part-bracket-001",
        target_id="mat-steel-001",
        confidence=0.85,
    )
    store.add_relation(rel1)

    rel2 = OntologyRelation(
        id="rel-002",
        relation_type=RelationType.FAILURE_MODE_OF,
        source_id="fm-fatigue-001",
        target_id="part-bracket-001",
        confidence=0.8,
    )
    store.add_relation(rel2)

    rel3 = OntologyRelation(
        id="rel-003",
        relation_type=RelationType.GOVERNED_BY,
        source_id="fm-fatigue-001",
        target_id="phys-stress-001",
        confidence=0.9,
    )
    store.add_relation(rel3)

    return store


class TestStoreBasicOperations:
    """Test basic CRUD operations."""

    def test_add_entity(self, store):
        """Test adding an entity."""
        part = PartEntity(
            id="part-001",
            name="Test Part",
            description="A test part",
            category="test",
            confidence=0.8,
        )
        entity_id = store.add_entity(part)

        assert entity_id == "part-001"
        assert store.get_entity("part-001") is not None
        assert store.get_entity("part-001").name == "Test Part"

    def test_add_entity_generates_id(self, store):
        """Test that entities get IDs if not provided."""
        part = PartEntity(
            id="",
            name="Auto ID Part",
            description="Part with auto-generated ID",
            category="test",
        )
        # Manually set ID since model requires it
        part.id = store._generate_id("part", part.name)
        entity_id = store.add_entity(part)

        assert entity_id.startswith("part-")
        assert store.get_entity(entity_id) is not None

    def test_get_nonexistent_entity(self, store):
        """Test getting a nonexistent entity returns None."""
        assert store.get_entity("nonexistent") is None

    def test_update_entity(self, populated_store):
        """Test updating an entity."""
        result = populated_store.update_entity(
            "part-bracket-001",
            {"description": "Updated description", "confidence": 0.95},
        )

        assert result is True
        entity = populated_store.get_entity("part-bracket-001")
        assert entity.description == "Updated description"
        assert entity.confidence == 0.95

    def test_delete_entity(self, populated_store):
        """Test deleting an entity."""
        result = populated_store.delete_entity("part-fastener-001")

        assert result is True
        assert populated_store.get_entity("part-fastener-001") is None

    def test_delete_entity_removes_relations(self, populated_store):
        """Test that deleting an entity removes its relations."""
        # Delete bracket which has relations
        populated_store.delete_entity("part-bracket-001")

        # Relations should be gone
        steel = populated_store.get_entity("mat-steel-001")
        incoming = populated_store.get_incoming_relations(steel.id)
        assert len(incoming) == 0


class TestRelationOperations:
    """Test relation operations."""

    def test_add_relation(self, store):
        """Test adding a relation."""
        # Add two entities first
        part = PartEntity(id="part-001", name="Part", description="", category="")
        mat = MaterialEntity(id="mat-001", name="Material", description="", category="")
        store.add_entity(part)
        store.add_entity(mat)

        rel = OntologyRelation(
            id="rel-001",
            relation_type=RelationType.MADE_OF,
            source_id="part-001",
            target_id="mat-001",
            confidence=0.9,
        )
        rel_id = store.add_relation(rel)

        assert rel_id == "rel-001"
        assert store.get_relation("rel-001") is not None

    def test_get_outgoing_relations(self, populated_store):
        """Test getting outgoing relations."""
        relations = populated_store.get_outgoing_relations("part-bracket-001")

        assert len(relations) == 1
        assert relations[0].relation_type == RelationType.MADE_OF

    def test_get_incoming_relations(self, populated_store):
        """Test getting incoming relations."""
        relations = populated_store.get_incoming_relations("part-bracket-001")

        assert len(relations) == 1
        assert relations[0].relation_type == RelationType.FAILURE_MODE_OF

    def test_get_neighbors(self, populated_store):
        """Test getting neighboring entities."""
        neighbors = populated_store.get_neighbors("part-bracket-001")

        names = {n.name for n in neighbors}
        assert "1020 Steel" in names
        assert "Fatigue Failure" in names


class TestEntityQueries:
    """Test entity query operations."""

    def test_get_entities_by_type(self, populated_store):
        """Test getting entities by type."""
        parts = populated_store.get_entities_by_type(EntityType.PART)
        assert len(parts) == 2

        materials = populated_store.get_entities_by_type(EntityType.MATERIAL)
        assert len(materials) == 1

        failure_modes = populated_store.get_entities_by_type(EntityType.FAILURE_MODE)
        assert len(failure_modes) == 1

    def test_get_entities_by_tag(self, populated_store):
        """Test getting entities by tag."""
        structural = populated_store.get_entities_by_tag("structural")
        assert len(structural) == 1
        assert structural[0].name == "Mounting Bracket"

        fasteners = populated_store.get_entities_by_tag("fastener")
        assert len(fasteners) == 1


class TestGraphTraversal:
    """Test graph traversal operations."""

    def test_traverse_bfs(self, populated_store):
        """Test BFS traversal."""
        visited = populated_store.traverse_bfs("part-bracket-001", max_depth=2)

        assert "part-bracket-001" in visited
        assert visited["part-bracket-001"] == 0
        assert "mat-steel-001" in visited
        assert "fm-fatigue-001" in visited

    def test_find_paths(self, populated_store):
        """Test path finding."""
        paths = populated_store.find_paths(
            "part-bracket-001",
            "phys-stress-001",
            max_depth=3,
        )

        # Should find path: bracket -> fatigue -> stress
        assert len(paths) >= 1
        for path in paths:
            assert path[0] == "part-bracket-001"
            assert path[-1] == "phys-stress-001"


class TestKeywordSearch:
    """Test keyword search."""

    def test_keyword_search_basic(self, populated_store):
        """Test basic keyword search."""
        results = populated_store.keyword_search(["bracket", "mounting"])

        assert len(results) > 0
        names = [e.name for e, _ in results]
        assert "Mounting Bracket" in names

    def test_keyword_search_by_type(self, populated_store):
        """Test keyword search filtered by type."""
        results = populated_store.keyword_search(
            ["steel"],
            entity_types=[EntityType.MATERIAL],
        )

        assert len(results) == 1
        assert results[0][0].name == "1020 Steel"


class TestPersistence:
    """Test persistence operations."""

    def test_save_and_load(self, populated_store):
        """Test saving and loading ontology."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ontology.json"

            # Save
            populated_store.save(path)
            assert path.exists()

            # Load into new store
            new_store = OntologyStore(path)

            # Verify entities
            assert len(new_store._entities) == len(populated_store._entities)

            bracket = new_store.get_entity("part-bracket-001")
            assert bracket is not None
            assert bracket.name == "Mounting Bracket"

            # Verify relations
            assert len(new_store._relations) == len(populated_store._relations)

    def test_save_load_preserves_subclass_fields(self, populated_store):
        """Test that subclass-specific fields are preserved after save/load.

        Regression test for: Entity subclass data lost after save/load.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ontology.json"
            populated_store.save(path)

            new_store = OntologyStore(path)

            # Verify PartEntity subclass fields preserved
            bracket = new_store.get_entity("part-bracket-001")
            assert (
                type(bracket) is PartEntity
            ), f"Expected PartEntity, got {type(bracket)}"
            assert bracket.category == "bracket"
            assert bracket.typical_materials == ["steel", "aluminum"]
            assert bracket.standards == ["ISO 4762"]

            # Verify MaterialEntity subclass fields preserved
            steel = new_store.get_entity("mat-steel-001")
            assert (
                type(steel) is MaterialEntity
            ), f"Expected MaterialEntity, got {type(steel)}"
            assert steel.category == "metal"
            assert steel.mechanical_properties["yield_strength"]["value"] == 350
            assert steel.mechanical_properties["yield_strength"]["unit"] == "MPa"

            # Verify FailureMode subclass fields preserved
            fatigue = new_store.get_entity("fm-fatigue-001")
            assert (
                type(fatigue) is FailureMode
            ), f"Expected FailureMode, got {type(fatigue)}"
            assert fatigue.domain == "mechanical"
            assert fatigue.severity == "high"
            assert "cyclic loading" in fatigue.causes
            assert "crack initiation" in fatigue.effects
            assert "reduce stress concentration" in fatigue.mitigations

            # Verify PhysicsPhenomenon subclass fields preserved
            stress = new_store.get_entity("phys-stress-001")
            assert (
                type(stress) is PhysicsPhenomenon
            ), f"Expected PhysicsPhenomenon, got {type(stress)}"
            assert stress.domain == "mechanical"
            assert "stress concentration factor" in stress.parameters


class TestStats:
    """Test statistics."""

    def test_stats(self, populated_store):
        """Test getting stats."""
        stats = populated_store.stats()

        assert stats["total_entities"] == 5
        assert stats["total_relations"] == 3
        assert stats["entity_types"]["part"] == 2
        assert stats["entity_types"]["material"] == 1
        assert stats["entity_types"]["failure_mode"] == 1
