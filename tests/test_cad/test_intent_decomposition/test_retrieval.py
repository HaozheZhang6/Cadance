"""Tests for Phase 3: RAG retrieval system.

Tests embeddings, vector store, API catalog, and retriever components.
Includes tests for confidence scoring and error pattern matching for
uncertainty propagation in the hypergraph.
"""

import tempfile
from pathlib import Path

import pytest

from src.cad.intent_decomposition.operations.operation_types import (
    CADOperation,
    OperationSequence,
)
from src.cad.intent_decomposition.operations.primitives import (
    CADPrimitive,
)
from src.cad.intent_decomposition.retrieval.api_catalog.base import (
    APIConfidence,
    APIEntry,
    CatalogMetadata,
    ErrorPattern,
    IntegrationLevel,
)
from src.cad.intent_decomposition.retrieval.api_catalog.cadquery_catalog import (
    CadQueryAPICatalog,
)
from src.cad.intent_decomposition.retrieval.embeddings.base import MockEmbeddingClient
from src.cad.intent_decomposition.retrieval.embeddings.local_embeddings import (
    LocalEmbeddingCache,
)
from src.cad.intent_decomposition.retrieval.retriever import (
    APIRetriever,
    MockAPIRetriever,
    OperationContext,
    RetrievalContext,
    RetrievedAPI,
)
from src.cad.intent_decomposition.retrieval.vector_store import (
    InMemoryVectorStore,
)

# =============================================================================
# MockEmbeddingClient Tests
# =============================================================================


class TestMockEmbeddingClient:
    """Tests for MockEmbeddingClient."""

    def test_embed_returns_correct_dimension(self):
        """embed should return vector of correct dimension."""
        client = MockEmbeddingClient(dimension=256)
        embedding = client.embed("test text")
        assert len(embedding) == 256

    def test_embed_deterministic(self):
        """Same text should produce same embedding."""
        client = MockEmbeddingClient()
        e1 = client.embed("hello world")
        e2 = client.embed("hello world")
        assert e1 == e2

    def test_embed_different_for_different_text(self):
        """Different text should produce different embeddings."""
        client = MockEmbeddingClient()
        e1 = client.embed("hello")
        e2 = client.embed("world")
        assert e1 != e2

    def test_embed_batch(self):
        """embed_batch should embed multiple texts."""
        client = MockEmbeddingClient(dimension=128)
        texts = ["text1", "text2", "text3"]
        embeddings = client.embed_batch(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 128

    def test_embed_count_tracked(self):
        """Embed count should be tracked."""
        client = MockEmbeddingClient()
        assert client.embed_count == 0

        client.embed("test1")
        assert client.embed_count == 1

        client.embed_batch(["test2", "test3"])
        assert client.embed_count == 3

    def test_dimension_property(self):
        """dimension property should return configured dimension."""
        client = MockEmbeddingClient(dimension=512)
        assert client.dimension == 512

    def test_model_name_property(self):
        """model_name should return mock identifier."""
        client = MockEmbeddingClient()
        assert client.model_name == "mock-embedding"


# =============================================================================
# InMemoryVectorStore Tests
# =============================================================================


class TestInMemoryVectorStore:
    """Tests for InMemoryVectorStore."""

    def test_add_and_get(self):
        """Should add and retrieve embeddings."""
        store = InMemoryVectorStore()
        embedding = [0.1, 0.2, 0.3]

        store.add("id1", embedding, {"name": "test"})
        result = store.get("id1")

        assert result is not None
        assert result[0] == embedding
        assert result[1] == {"name": "test"}

    def test_get_nonexistent(self):
        """Should return None for nonexistent ID."""
        store = InMemoryVectorStore()
        assert store.get("nonexistent") is None

    def test_dimension_tracking(self):
        """Should track embedding dimension."""
        store = InMemoryVectorStore()
        assert store.dimension is None

        store.add("id1", [0.1, 0.2, 0.3], None)
        assert store.dimension == 3

    def test_dimension_mismatch_error(self):
        """Should raise error on dimension mismatch."""
        store = InMemoryVectorStore()
        store.add("id1", [0.1, 0.2, 0.3], None)

        with pytest.raises(ValueError, match="dimension"):
            store.add("id2", [0.1, 0.2], None)

    def test_search_cosine_similarity(self):
        """Should search by cosine similarity."""
        store = InMemoryVectorStore()

        # Add normalized vectors for easy similarity calculation
        store.add("similar", [1.0, 0.0, 0.0], {"name": "similar"})
        store.add("different", [0.0, 1.0, 0.0], {"name": "different"})

        # Query close to "similar"
        results = store.search([0.9, 0.1, 0.0], top_k=2)

        assert len(results) == 2
        assert results[0].id == "similar"
        assert results[0].score > results[1].score

    def test_search_top_k(self):
        """Should return top_k results."""
        store = InMemoryVectorStore()

        for i in range(10):
            store.add(f"id{i}", [float(i), 0.0, 0.0], None)

        results = store.search([5.0, 0.0, 0.0], top_k=3)
        assert len(results) == 3

    def test_search_with_filter(self):
        """Should filter results based on metadata."""
        store = InMemoryVectorStore()
        store.add("a", [1.0, 0.0], {"type": "box"})
        store.add("b", [0.9, 0.1], {"type": "cylinder"})
        store.add("c", [0.8, 0.2], {"type": "box"})

        results = store.search(
            [1.0, 0.0],
            top_k=5,
            filter_fn=lambda m: m.get("type") == "box",
        )

        assert len(results) == 2
        assert all(r.metadata.get("type") == "box" for r in results)

    def test_search_empty_store(self):
        """Should return empty list for empty store."""
        store = InMemoryVectorStore()
        results = store.search([1.0, 0.0, 0.0])
        assert results == []

    def test_remove(self):
        """Should remove embedding by ID."""
        store = InMemoryVectorStore()
        store.add("id1", [1.0, 0.0], None)

        assert "id1" in store
        assert store.remove("id1") is True
        assert "id1" not in store
        assert store.remove("id1") is False

    def test_clear(self):
        """Should clear all embeddings."""
        store = InMemoryVectorStore()
        store.add("id1", [1.0], None)
        store.add("id2", [2.0], None)

        store.clear()
        assert len(store) == 0

    def test_len(self):
        """Should return count of embeddings."""
        store = InMemoryVectorStore()
        assert len(store) == 0

        store.add("id1", [1.0], None)
        assert len(store) == 1

    def test_contains(self):
        """Should check ID existence."""
        store = InMemoryVectorStore()
        store.add("id1", [1.0], None)

        assert "id1" in store
        assert "id2" not in store

    def test_ids_property(self):
        """Should return list of all IDs."""
        store = InMemoryVectorStore()
        store.add("a", [1.0], None)
        store.add("b", [2.0], None)

        ids = store.ids
        assert set(ids) == {"a", "b"}

    def test_add_batch(self):
        """Should add multiple embeddings in batch."""
        store = InMemoryVectorStore()
        items = [
            ("id1", [1.0, 0.0], {"name": "a"}),
            ("id2", [0.0, 1.0], {"name": "b"}),
        ]
        store.add_batch(items)

        assert len(store) == 2
        assert store.get("id1") is not None

    def test_stats(self):
        """Should return store statistics."""
        store = InMemoryVectorStore()
        store.add("id1", [1.0, 2.0, 3.0], None)

        stats = store.stats()
        assert stats["count"] == 1
        assert stats["dimension"] == 3
        assert stats["has_persistence"] is False


class TestInMemoryVectorStorePersistence:
    """Tests for vector store persistence."""

    def test_save_and_load(self):
        """Should persist and reload vectors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Create and save
            store1 = InMemoryVectorStore(persist_path=path)
            store1.add("id1", [1.0, 2.0], {"name": "test"})
            store1.save()

            # Load in new instance
            store2 = InMemoryVectorStore(persist_path=path)

            assert len(store2) == 1
            result = store2.get("id1")
            assert result is not None
            assert result[0] == [1.0, 2.0]
            assert result[1] == {"name": "test"}

    def test_no_persist_path(self):
        """Should work without persistence."""
        store = InMemoryVectorStore()
        store.add("id1", [1.0], None)
        store.save()  # Should not error


# =============================================================================
# LocalEmbeddingCache Tests
# =============================================================================


class TestLocalEmbeddingCache:
    """Tests for LocalEmbeddingCache."""

    def test_cache_hit(self):
        """Should return cached embedding on hit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient(dimension=128)
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            # First call - cache miss
            e1 = cache.embed("test text")
            assert mock.embed_count == 1

            # Second call - cache hit
            e2 = cache.embed("test text")
            assert mock.embed_count == 1  # No new call
            assert e1 == e2

    def test_cache_miss_with_fallback(self):
        """Should call fallback on cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient(dimension=64)
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            embedding = cache.embed("new text")
            assert len(embedding) == 64
            assert mock.embed_count == 1

    def test_cache_miss_without_fallback(self):
        """Should raise error on cache miss without fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalEmbeddingCache(cache_path=Path(tmpdir))

            with pytest.raises(RuntimeError, match="Cache miss"):
                cache.embed("new text")

    def test_embed_batch_partial_cache(self):
        """Should use cache for some and fallback for others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient(dimension=64)
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            # Cache one text
            cache.embed("cached")

            # Batch with mix
            embeddings = cache.embed_batch(["cached", "new1", "new2"])

            assert len(embeddings) == 3
            # 1 initial + 2 new = 3
            assert mock.embed_count == 3

    def test_dimension_from_fallback(self):
        """Should get dimension from fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient(dimension=256)
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            assert cache.dimension == 256

    def test_model_name(self):
        """Should include cached prefix in model name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient()
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            assert "cached" in cache.model_name

    def test_save_and_reload(self):
        """Should persist cache across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            mock = MockEmbeddingClient(dimension=64)

            # First instance
            cache1 = LocalEmbeddingCache(cache_path=path, fallback=mock)
            e1 = cache1.embed("test")
            cache1.save_cache()

            # Second instance (no fallback - offline mode)
            cache2 = LocalEmbeddingCache(cache_path=path)
            e2 = cache2.embed("test")  # Should hit cache

            assert e1 == e2

    def test_clear_cache(self):
        """Should clear all cached embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient()
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            cache.embed("test")
            cache.clear_cache()

            # Should need to call fallback again
            cache.embed("test")
            assert mock.embed_count == 2

    def test_cache_stats(self):
        """Should return cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock = MockEmbeddingClient(dimension=128)
            cache = LocalEmbeddingCache(
                cache_path=Path(tmpdir),
                fallback=mock,
            )

            cache.embed("test1")
            cache.embed("test2")

            stats = cache.cache_stats()
            assert stats["count"] == 2
            assert stats["dimension"] == 128
            assert stats["has_fallback"] is True


# =============================================================================
# APIEntry Tests
# =============================================================================


class TestAPIEntry:
    """Tests for APIEntry dataclass."""

    def test_str_representation(self):
        """Should format as name -> [primitives]."""
        entry = APIEntry(
            name="box",
            signature="box(l, w, h)",
            description="Create a box",
            primitives=[CADPrimitive.BOX],
        )

        assert "box" in str(entry)
        assert "box" in str(entry)  # primitive value

    def test_to_embedding_text(self):
        """Should generate embedding text."""
        entry = APIEntry(
            name="hole",
            signature="hole(diameter, depth)",
            description="Create a cylindrical hole",
            primitives=[CADPrimitive.HOLE],
            parameters={"diameter": "Hole diameter", "depth": "Hole depth"},
        )

        text = entry.to_embedding_text()

        assert "API: hole" in text
        assert "cylindrical hole" in text
        assert "diameter" in text
        assert "hole" in text  # primitive

    def test_defaults(self):
        """Should have sensible defaults."""
        entry = APIEntry(
            name="test",
            signature="test()",
            description="Test API",
        )

        assert entry.examples == []
        assert entry.primitives == []
        assert entry.parameters == {}
        assert entry.notes is None

    def test_confidence_default(self):
        """Should default to DOCUMENTED confidence."""
        entry = APIEntry(
            name="test",
            signature="test()",
            description="Test API",
        )
        assert entry.confidence == APIConfidence.DOCUMENTED
        assert entry.confidence_score == 0.8

    def test_confidence_score_property(self):
        """Should return numerical confidence score."""
        entry = APIEntry(
            name="test",
            signature="test()",
            description="Test API",
            confidence=APIConfidence.VERIFIED,
        )
        assert entry.confidence_score == 0.95

    def test_error_pattern_matching(self):
        """Should match error patterns."""
        entry = APIEntry(
            name="test",
            signature="test()",
            description="Test API",
            error_patterns=[
                ErrorPattern(
                    pattern=r"dimension.*zero",
                    cause="Zero dimension",
                    resolution="Use positive values",
                ),
                ErrorPattern(
                    pattern=r"invalid.*type",
                    cause="Wrong type",
                    resolution="Use correct type",
                ),
            ],
        )

        match = entry.get_error_resolution("Error: dimension is zero")
        assert match is not None
        assert match.cause == "Zero dimension"

        match = entry.get_error_resolution("Error: invalid type provided")
        assert match is not None
        assert match.cause == "Wrong type"

        match = entry.get_error_resolution("Unknown error")
        assert match is None

    def test_fallback_api(self):
        """Should support fallback API specification."""
        entry = APIEntry(
            name="fillet",
            signature="fillet(r)",
            description="Add fillet",
            fallback_api="chamfer",
        )
        assert entry.fallback_api == "chamfer"


# =============================================================================
# APIConfidence Tests
# =============================================================================


class TestAPIConfidence:
    """Tests for APIConfidence enum."""

    def test_confidence_scores(self):
        """Should have correct confidence scores."""
        assert APIConfidence.VERIFIED.confidence_score == 0.95
        assert APIConfidence.DOCUMENTED.confidence_score == 0.80
        assert APIConfidence.INFERRED.confidence_score == 0.60
        assert APIConfidence.EXPERIMENTAL.confidence_score == 0.40

    def test_confidence_ordering(self):
        """Higher confidence should have higher scores."""
        assert (
            APIConfidence.VERIFIED.confidence_score
            > APIConfidence.DOCUMENTED.confidence_score
        )
        assert (
            APIConfidence.DOCUMENTED.confidence_score
            > APIConfidence.INFERRED.confidence_score
        )
        assert (
            APIConfidence.INFERRED.confidence_score
            > APIConfidence.EXPERIMENTAL.confidence_score
        )


# =============================================================================
# IntegrationLevel Tests
# =============================================================================


class TestIntegrationLevel:
    """Tests for IntegrationLevel enum."""

    def test_integration_levels_exist(self):
        """Should have all expected integration levels."""
        assert IntegrationLevel.FULL_SOURCE.value == "full_source"
        assert IntegrationLevel.API_WITH_TRACEBACKS.value == "api_with_tracebacks"
        assert IntegrationLevel.MINIMAL_API.value == "minimal_api"


# =============================================================================
# ErrorPattern Tests
# =============================================================================


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""

    def test_error_pattern_creation(self):
        """Should create error pattern with defaults."""
        pattern = ErrorPattern(
            pattern=r"test.*error",
            cause="Test cause",
            resolution="Test resolution",
        )
        assert pattern.confidence == 0.8

    def test_error_pattern_custom_confidence(self):
        """Should accept custom confidence."""
        pattern = ErrorPattern(
            pattern=r"test",
            cause="Cause",
            resolution="Resolution",
            confidence=0.95,
        )
        assert pattern.confidence == 0.95


# =============================================================================
# CatalogMetadata Tests
# =============================================================================


class TestCatalogMetadata:
    """Tests for CatalogMetadata dataclass."""

    def test_metadata_creation(self):
        """Should create metadata with defaults."""
        metadata = CatalogMetadata(tool_name="test_tool")
        assert metadata.tool_name == "test_tool"
        assert metadata.integration_level == IntegrationLevel.API_WITH_TRACEBACKS

    def test_metadata_full_source(self):
        """Should support full source configuration."""
        metadata = CatalogMetadata(
            tool_name="cadquery",
            tool_version="2.4.0",
            integration_level=IntegrationLevel.FULL_SOURCE,
            documentation_url="https://cadquery.readthedocs.io",
            verification_method="source_code_inspection",
        )
        assert metadata.integration_level == IntegrationLevel.FULL_SOURCE


# =============================================================================
# CadQueryAPICatalog Tests
# =============================================================================


class TestCadQueryAPICatalog:
    """Tests for CadQueryAPICatalog."""

    def test_get_all_entries(self):
        """Should return all API entries."""
        catalog = CadQueryAPICatalog()
        entries = catalog.get_all_entries()

        assert len(entries) > 0
        assert all(isinstance(e, APIEntry) for e in entries)

    def test_tool_name(self):
        """Should return cadquery as tool name."""
        catalog = CadQueryAPICatalog()
        assert catalog.tool_name == "cadquery"

    def test_len(self):
        """Should return number of entries."""
        catalog = CadQueryAPICatalog()
        assert len(catalog) > 0
        assert len(catalog) == len(catalog.get_all_entries())

    def test_get_by_name(self):
        """Should retrieve API by name."""
        catalog = CadQueryAPICatalog()

        box = catalog.get_by_name("box")
        assert box is not None
        assert box.name == "box"
        assert CADPrimitive.BOX in box.primitives

    def test_get_by_name_not_found(self):
        """Should return None for unknown name."""
        catalog = CadQueryAPICatalog()
        assert catalog.get_by_name("nonexistent") is None

    def test_get_by_primitive_box(self):
        """Should find box API for BOX primitive."""
        catalog = CadQueryAPICatalog()
        apis = catalog.get_by_primitive(CADPrimitive.BOX)

        assert len(apis) > 0
        assert any(api.name == "box" for api in apis)

    def test_get_by_primitive_hole(self):
        """Should find hole APIs for HOLE primitive."""
        catalog = CadQueryAPICatalog()
        apis = catalog.get_by_primitive(CADPrimitive.HOLE)

        assert len(apis) > 0
        assert any(api.name == "hole" for api in apis)

    def test_get_by_primitive_counterbore(self):
        """Should find cboreHole for HOLE_COUNTERBORE primitive."""
        catalog = CadQueryAPICatalog()
        apis = catalog.get_by_primitive(CADPrimitive.HOLE_COUNTERBORE)

        assert len(apis) > 0
        assert any(api.name == "cboreHole" for api in apis)

    def test_get_by_primitive_empty(self):
        """Should return empty list for unmapped primitive."""
        catalog = CadQueryAPICatalog()
        # HOLE_TAPPED might not be directly mapped
        apis = catalog.get_by_primitive(CADPrimitive.HOLE_TAPPED)
        # Could be empty or have fallbacks
        assert isinstance(apis, list)

    def test_coverage_report(self):
        """Should generate coverage report."""
        catalog = CadQueryAPICatalog()
        report = catalog.coverage_report()

        assert "covered" in report
        assert "not_covered" in report
        assert "coverage_percent" in report
        assert isinstance(report["coverage_percent"], float)

    def test_all_primitives_covered_property(self):
        """Should return set of covered primitives."""
        catalog = CadQueryAPICatalog()
        covered = catalog.all_primitives_covered

        assert isinstance(covered, set)
        assert CADPrimitive.BOX in covered

    def test_api_has_examples(self):
        """Key APIs should have examples."""
        catalog = CadQueryAPICatalog()

        box = catalog.get_by_name("box")
        assert box.examples, "box should have examples"

        hole = catalog.get_by_name("hole")
        assert hole.examples, "hole should have examples"

    def test_api_has_parameters(self):
        """APIs should have parameter descriptions."""
        catalog = CadQueryAPICatalog()

        box = catalog.get_by_name("box")
        assert box.parameters, "box should have parameters"
        assert "length" in box.parameters or "height" in box.parameters

    def test_fillet_requires_edge_selection(self):
        """Fillet API should note edge selection requirement."""
        catalog = CadQueryAPICatalog()

        fillet = catalog.get_by_name("fillet")
        assert fillet is not None
        assert fillet.notes is not None
        assert "edge" in fillet.notes.lower()

    def test_metadata_property(self):
        """Should have catalog metadata."""
        catalog = CadQueryAPICatalog()
        metadata = catalog.metadata

        assert metadata.tool_name == "cadquery"
        assert metadata.tool_version is not None
        assert metadata.integration_level == IntegrationLevel.FULL_SOURCE
        assert metadata.documentation_url is not None

    def test_integration_level_property(self):
        """Should return integration level."""
        catalog = CadQueryAPICatalog()
        assert catalog.integration_level == IntegrationLevel.FULL_SOURCE

    def test_average_confidence(self):
        """Should calculate average confidence across entries."""
        catalog = CadQueryAPICatalog()
        avg = catalog.average_confidence()

        # Should be between 0 and 1
        assert 0.0 <= avg <= 1.0
        # CadQuery is well-documented, should have decent average
        assert avg >= 0.7  # At least 70% average confidence

    def test_confidence_distribution(self):
        """Should return confidence distribution."""
        catalog = CadQueryAPICatalog()
        dist = catalog.confidence_distribution()

        # Should have at least some entries
        assert sum(dist.values()) == len(catalog)
        # All keys should be valid confidence levels
        valid_levels = {c.value for c in APIConfidence}
        assert all(level in valid_levels for level in dist.keys())

    def test_verified_apis_have_error_patterns(self):
        """Key verified APIs should have error patterns."""
        catalog = CadQueryAPICatalog()

        box = catalog.get_by_name("box")
        assert box.confidence == APIConfidence.VERIFIED
        assert len(box.error_patterns) > 0

        hole = catalog.get_by_name("hole")
        assert hole.confidence == APIConfidence.VERIFIED
        assert len(hole.error_patterns) > 0

    def test_fillet_has_fallback(self):
        """Fillet should have chamfer as fallback."""
        catalog = CadQueryAPICatalog()
        fillet = catalog.get_by_name("fillet")
        assert fillet.fallback_api == "chamfer"

    def test_verified_apis_have_source_url(self):
        """Verified APIs should have documentation URL."""
        catalog = CadQueryAPICatalog()

        box = catalog.get_by_name("box")
        assert box.source_url is not None
        assert "cadquery" in box.source_url

    def test_confidence_propagation_values(self):
        """Confidence scores should be usable for propagation."""
        catalog = CadQueryAPICatalog()

        # Get confidence scores for common operations
        box = catalog.get_by_name("box")
        hole = catalog.get_by_name("hole")
        extrude = catalog.get_by_name("extrude")

        # These are verified - should have high confidence
        assert box.confidence_score >= 0.9
        assert hole.confidence_score >= 0.9
        assert extrude.confidence_score >= 0.9

    def test_get_core_apis(self):
        """Should return core positioning/transformation APIs."""
        catalog = CadQueryAPICatalog()
        core_apis = catalog.get_core_apis()

        # Should have multiple core APIs
        assert len(core_apis) >= 4

        # Should include key positioning APIs
        core_names = [api.name for api in core_apis]
        assert "transformed" in core_names
        assert "center" in core_names
        assert "moveTo" in core_names
        assert "workplane" in core_names

    def test_pushpoints_in_catalog(self):
        """pushPoints should be in catalog for positioning multiple features."""
        catalog = CadQueryAPICatalog()
        pushPoints = catalog.get_by_name("pushPoints")

        assert pushPoints is not None
        assert "pnts" in pushPoints.parameters
        assert len(pushPoints.examples) >= 1
        assert CADPrimitive.HOLE in pushPoints.primitives


# =============================================================================
# MockAPIRetriever Tests
# =============================================================================


class TestMockAPIRetriever:
    """Tests for MockAPIRetriever."""

    def test_retrieve_for_primitive(self):
        """Should retrieve APIs for a primitive."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        apis = retriever.retrieve_for_primitive(CADPrimitive.BOX)

        assert len(apis) > 0
        assert all(isinstance(a, RetrievedAPI) for a in apis)
        assert apis[0].source == "primitive_match"

    def test_retrieve_for_operation_sequence(self):
        """Should retrieve APIs for operation sequence."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a box",
                    parameters={"length": 10, "width": 20, "height": 5},
                ),
                CADOperation(
                    primitive=CADPrimitive.HOLE,
                    description="Add a hole",
                    parameters={"diameter": 5},
                ),
            ]
        )

        context = retriever.retrieve(operations)

        assert isinstance(context, RetrievalContext)
        assert len(context.operations) == 2

    def test_is_indexed_always_true(self):
        """Mock retriever should always report as indexed."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)
        assert retriever.is_indexed is True

    def test_stats(self):
        """Should return statistics."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        stats = retriever.stats()
        assert stats["mock"] is True
        assert stats["tool"] == "cadquery"


# =============================================================================
# APIRetriever Tests
# =============================================================================


class TestAPIRetriever:
    """Tests for APIRetriever with full embedding search."""

    def test_build_index(self):
        """Should build vector index from catalog."""
        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore()

        retriever = APIRetriever(catalog, embeddings, store)
        assert retriever.is_indexed is False

        retriever.build_index()

        assert retriever.is_indexed is True
        assert len(store) == len(catalog)

    def test_build_index_cache_reuse(self, tmp_path):
        """Should reuse cached embeddings when catalog hash matches."""
        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore(persist_path=tmp_path / "vectors")

        retriever = APIRetriever(catalog, embeddings, store)
        retriever.build_index()
        first_embed_count = embeddings.embed_count

        # Second build should skip embedding (cache hit)
        retriever.build_index()
        assert embeddings.embed_count == first_embed_count

    def test_build_index_cache_invalidation(self, tmp_path):
        """Should rebuild when catalog content changes (hash mismatch)."""
        from unittest.mock import patch

        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore(persist_path=tmp_path / "vectors")

        retriever = APIRetriever(catalog, embeddings, store)
        retriever.build_index()
        first_embed_count = embeddings.embed_count

        # Force hash change — simulates catalog content change
        with patch.object(
            retriever, "_compute_catalog_hash", return_value="changed_hash"
        ):
            retriever.build_index()
        assert embeddings.embed_count > first_embed_count

    def test_retrieve_for_primitive(self):
        """Should retrieve APIs using hybrid search."""
        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore()

        retriever = APIRetriever(catalog, embeddings, store)
        apis = retriever.retrieve_for_primitive(
            CADPrimitive.BOX,
            description="Create a rectangular box",
        )

        assert len(apis) > 0
        # Box should be among top results
        names = [a.entry.name for a in apis]
        assert "box" in names

    def test_retrieve_for_operation_sequence(self):
        """Should retrieve context for operation sequence."""
        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore()

        retriever = APIRetriever(catalog, embeddings, store)

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.CYLINDER,
                    description="Create a cylinder",
                    parameters={"height": 20, "radius": 5},
                ),
                CADOperation(
                    primitive=CADPrimitive.FILLET,
                    description="Add fillets to edges",
                    parameters={"radius": 2},
                ),
            ]
        )

        context = retriever.retrieve(operations)

        assert len(context.operations) == 2
        assert context.operations[0].top_api is not None
        assert context.operations[1].top_api is not None

    def test_stats(self):
        """Should return retriever statistics."""
        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore()

        retriever = APIRetriever(catalog, embeddings, store)
        retriever.build_index()

        stats = retriever.stats()
        assert stats["indexed"] is True
        assert stats["catalog_size"] == len(catalog)
        assert stats["embedding_dimension"] == 128


# =============================================================================
# RetrievalContext Tests
# =============================================================================


class TestRetrievalContext:
    """Tests for RetrievalContext."""

    def test_get_all_apis(self):
        """Should return unique APIs across all operations."""
        # Create a context with some duplicate APIs
        box_entry = APIEntry(
            name="box",
            signature="box()",
            description="Create box",
        )
        hole_entry = APIEntry(
            name="hole",
            signature="hole()",
            description="Create hole",
        )

        context = RetrievalContext(
            operations=[
                OperationContext(
                    operation=CADOperation(
                        primitive=CADPrimitive.BOX,
                        description="box",
                        parameters={},
                    ),
                    retrieved_apis=[
                        RetrievedAPI(entry=box_entry, score=1.0, source="test")
                    ],
                ),
                OperationContext(
                    operation=CADOperation(
                        primitive=CADPrimitive.BOX,
                        description="another box",
                        parameters={},
                    ),
                    retrieved_apis=[
                        RetrievedAPI(entry=box_entry, score=0.9, source="test"),
                        RetrievedAPI(entry=hole_entry, score=0.5, source="test"),
                    ],
                ),
            ]
        )

        apis = context.get_all_apis()
        names = [a.name for a in apis]

        assert len(apis) == 2  # Unique
        assert "box" in names
        assert "hole" in names

    def test_to_prompt_context(self):
        """Should generate prompt-ready context string."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create base box",
                    parameters={"length": 50},
                ),
            ]
        )

        context = retriever.retrieve(operations)
        prompt = context.to_prompt_context()

        assert "CadQuery" in prompt
        assert "box" in prompt.lower()
        assert "Signature" in prompt

    def test_core_apis_in_context(self):
        """Should include core APIs in retrieval context."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.HOLE,
                    description="Create a mounting hole",
                    parameters={"diameter": 5},
                ),
            ]
        )

        context = retriever.retrieve(operations)

        # Core APIs should be populated
        assert len(context.core_apis) >= 4
        core_names = [api.name for api in context.core_apis]
        assert "transformed" in core_names
        assert "center" in core_names

    def test_core_apis_in_prompt(self):
        """Should include core positioning APIs section in prompt."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.HOLE,
                    description="Create a hole",
                    parameters={"diameter": 5},
                ),
            ]
        )

        context = retriever.retrieve(operations)
        prompt = context.to_prompt_context()

        # Should have core APIs section
        assert "Core Positioning APIs" in prompt
        assert "transformed" in prompt
        assert "center" in prompt

    def test_get_all_apis_includes_core(self):
        """get_all_apis should include core APIs."""
        catalog = CadQueryAPICatalog()
        retriever = MockAPIRetriever(catalog)

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create box",
                    parameters={},
                ),
            ]
        )

        context = retriever.retrieve(operations)
        all_apis = context.get_all_apis()
        api_names = [api.name for api in all_apis]

        # Should include both core and operation-specific APIs
        assert "transformed" in api_names
        assert "box" in api_names


class TestOperationContext:
    """Tests for OperationContext."""

    def test_top_api(self):
        """Should return highest-scored API."""
        entry1 = APIEntry(name="api1", signature="", description="")
        entry2 = APIEntry(name="api2", signature="", description="")

        op_ctx = OperationContext(
            operation=CADOperation(
                primitive=CADPrimitive.BOX,
                description="test",
                parameters={},
            ),
            retrieved_apis=[
                RetrievedAPI(entry=entry1, score=0.9, source="test"),
                RetrievedAPI(entry=entry2, score=0.8, source="test"),
            ],
        )

        assert op_ctx.top_api == entry1

    def test_top_api_empty(self):
        """Should return None when no APIs."""
        op_ctx = OperationContext(
            operation=CADOperation(
                primitive=CADPrimitive.BOX,
                description="test",
                parameters={},
            ),
            retrieved_apis=[],
        )

        assert op_ctx.top_api is None

    def test_get_examples(self):
        """Should collect all examples from retrieved APIs."""
        entry1 = APIEntry(
            name="api1",
            signature="",
            description="",
            examples=["example1", "example2"],
        )
        entry2 = APIEntry(
            name="api2",
            signature="",
            description="",
            examples=["example3"],
        )

        op_ctx = OperationContext(
            operation=CADOperation(
                primitive=CADPrimitive.BOX,
                description="test",
                parameters={},
            ),
            retrieved_apis=[
                RetrievedAPI(entry=entry1, score=1.0, source="test"),
                RetrievedAPI(entry=entry2, score=0.5, source="test"),
            ],
        )

        examples = op_ctx.get_examples()
        assert len(examples) == 3
        assert "example1" in examples


# =============================================================================
# RetrievedAPI Tests
# =============================================================================


class TestRetrievedAPI:
    """Tests for RetrievedAPI dataclass."""

    def test_str_representation(self):
        """Should format as name with score and source."""
        entry = APIEntry(name="test_api", signature="", description="")
        retrieved = RetrievedAPI(entry=entry, score=0.85, source="semantic_search")

        s = str(retrieved)
        assert "test_api" in s
        assert "0.85" in s
        assert "semantic_search" in s


# =============================================================================
# Integration Tests
# =============================================================================


class TestRetrievalIntegration:
    """Integration tests for the full retrieval pipeline."""

    def test_full_pipeline_with_mock(self):
        """Test full retrieval pipeline with mock embeddings."""
        # Setup
        catalog = CadQueryAPICatalog()
        embeddings = MockEmbeddingClient(dimension=128)
        store = InMemoryVectorStore()
        retriever = APIRetriever(catalog, embeddings, store)

        # Create operations
        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a base plate 100x50x10mm",
                    parameters={"length": 100, "width": 50, "height": 10},
                ),
                CADOperation(
                    primitive=CADPrimitive.SELECT_FACE,
                    description="Select the top face",
                    parameters={"selector": ">Z"},
                ),
                CADOperation(
                    primitive=CADPrimitive.HOLE,
                    description="Create mounting holes",
                    parameters={"diameter": 5},
                    dependencies=[1],
                ),
                CADOperation(
                    primitive=CADPrimitive.FILLET,
                    description="Round the edges",
                    parameters={"radius": 2},
                ),
            ]
        )

        # Retrieve
        context = retriever.retrieve(operations)

        # Verify
        assert len(context.operations) == 4

        # Check box operation
        box_ctx = context.operations[0]
        assert box_ctx.top_api is not None
        assert "box" in box_ctx.top_api.name.lower()

        # Check face selection
        face_ctx = context.operations[1]
        assert face_ctx.top_api is not None
        assert "face" in face_ctx.top_api.name.lower()

        # Check hole operation
        hole_ctx = context.operations[2]
        assert hole_ctx.top_api is not None
        assert "hole" in hole_ctx.top_api.name.lower()

        # Generate prompt context
        prompt = context.to_prompt_context()
        assert len(prompt) > 100  # Should have substantial content

    def test_catalog_primitive_coverage(self):
        """Verify catalog covers essential primitives."""
        catalog = CadQueryAPICatalog()

        essential_primitives = [
            CADPrimitive.BOX,
            CADPrimitive.CYLINDER,
            CADPrimitive.SPHERE,
            CADPrimitive.EXTRUDE,
            CADPrimitive.HOLE,
            CADPrimitive.FILLET,
            CADPrimitive.CHAMFER,
            CADPrimitive.SELECT_FACE,
            CADPrimitive.SELECT_EDGE,
        ]

        for primitive in essential_primitives:
            apis = catalog.get_by_primitive(primitive)
            assert len(apis) > 0, f"No APIs found for essential primitive: {primitive}"
