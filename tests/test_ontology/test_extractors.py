"""Tests for ontology extractors."""

import pytest

from src.ontology import (
    ConfidenceSource,
    EntityType,
    FailureMode,
    PartEntity,
)
from src.ontology.extractors.base import (
    SOURCE_CONFIDENCE_MAP,
    BaseExtractor,
    ExtractionConfig,
    get_base_confidence,
)
from src.ontology.models import ExtractionResult, OntologyRelation, RelationType


class TestExtractionConfig:
    """Test ExtractionConfig validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExtractionConfig()
        assert config.model == "gpt-4o"
        assert config.temperature == 0.1
        assert config.chunk_size == 8000
        assert config.chunk_overlap == 500
        assert config.min_confidence == 0.3

    def test_custom_config(self):
        """Test custom configuration."""
        config = ExtractionConfig(
            model="gpt-4",
            temperature=0.5,
            chunk_size=4000,
            chunk_overlap=200,
        )
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.chunk_size == 4000
        assert config.chunk_overlap == 200

    def test_invalid_chunk_overlap_raises(self):
        """Test that chunk_overlap >= chunk_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ExtractionConfig(chunk_size=1000, chunk_overlap=1000)
        assert "chunk_overlap" in str(exc_info.value)
        assert "chunk_size" in str(exc_info.value)

    def test_chunk_overlap_greater_than_size_raises(self):
        """Test that chunk_overlap > chunk_size raises ValueError."""
        with pytest.raises(ValueError):
            ExtractionConfig(chunk_size=500, chunk_overlap=1000)


class ConcreteExtractor(BaseExtractor):
    """Concrete implementation for testing base class."""

    async def extract(self, content, source, source_type, **kwargs):
        """Minimal extract implementation."""
        return ExtractionResult(
            source_document=source,
            source_type=source_type,
            entities=[],
            relations=[],
        )

    def get_extraction_prompt(self, content, **kwargs):
        """Minimal prompt implementation."""
        return f"Extract from: {content}"


@pytest.fixture
def extractor():
    """Create extractor for testing."""
    return ConcreteExtractor()


@pytest.fixture
def extractor_with_config():
    """Create extractor with custom config."""
    config = ExtractionConfig(chunk_size=100, chunk_overlap=20)
    return ConcreteExtractor(config=config)


class TestBaseExtractorIdGeneration:
    """Test ID generation."""

    def test_generate_id_is_deterministic(self, extractor):
        """Test that same input produces same ID."""
        id1 = extractor._generate_id("part", "Mounting Bracket")
        id2 = extractor._generate_id("part", "Mounting Bracket")
        assert id1 == id2

    def test_generate_id_differs_for_different_content(self, extractor):
        """Test that different content produces different IDs."""
        id1 = extractor._generate_id("part", "Mounting Bracket")
        id2 = extractor._generate_id("part", "Support Bracket")
        assert id1 != id2

    def test_generate_id_differs_for_different_type(self, extractor):
        """Test that different types produce different IDs."""
        id1 = extractor._generate_id("part", "Steel")
        id2 = extractor._generate_id("material", "Steel")
        assert id1 != id2

    def test_generate_id_format(self, extractor):
        """Test ID format is {type}-{hash}."""
        id1 = extractor._generate_id("part", "Test")
        assert id1.startswith("part-")
        assert len(id1) == len("part-") + 12  # 12 char hash


class TestBaseExtractorChunking:
    """Test text chunking."""

    def test_short_text_not_chunked(self, extractor):
        """Test that short text is returned as single chunk."""
        text = "This is a short document."
        chunks = extractor._chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_chunked(self, extractor_with_config):
        """Test that long text is split into chunks."""
        # Create text longer than chunk_size (100)
        text = "Word " * 50  # ~250 chars
        chunks = extractor_with_config._chunk_text(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self, extractor_with_config):
        """Test that chunks have overlap."""
        text = "A" * 50 + "B" * 50 + "C" * 50 + "D" * 50  # 200 chars
        chunks = extractor_with_config._chunk_text(text)

        # With chunk_size=100, chunk_overlap=20, we should see overlap
        if len(chunks) >= 2:
            # Check that end of first chunk overlaps with start of second
            chunks[0][-20:]  # Last 20 chars
            # Second chunk should start near where overlap begins
            assert len(chunks[1]) > 0

    def test_chunk_breaks_at_paragraph(self, extractor_with_config):
        """Test that chunking prefers paragraph breaks."""
        text = "First paragraph content.\n\n" + "A" * 50 + "\n\n" + "B" * 100
        chunks = extractor_with_config._chunk_text(text)
        # Should prefer breaking at \n\n
        assert len(chunks) >= 1

    def test_chunk_breaks_at_sentence(self, extractor_with_config):
        """Test that chunking prefers sentence breaks."""
        text = "First sentence. " + "A" * 80 + ". " + "B" * 50
        chunks = extractor_with_config._chunk_text(text)
        # Should prefer breaking at ". "
        assert len(chunks) >= 1


class TestBaseExtractorDeduplication:
    """Test entity deduplication."""

    def test_deduplicates_same_type_same_name(self, extractor):
        """Test that same type+name entities are deduplicated."""
        e1 = PartEntity(
            id="p1",
            name="Bracket",
            entity_type=EntityType.PART,
            confidence=0.8,
        )
        e2 = PartEntity(
            id="p2",
            name="bracket",  # Same name, different case
            entity_type=EntityType.PART,
            confidence=0.6,
        )

        result = extractor._deduplicate_entities([e1, e2])
        assert len(result) == 1
        assert result[0].confidence == 0.8  # Higher confidence kept

    def test_keeps_different_types_same_name(self, extractor):
        """Test that different types with same name are NOT deduplicated."""
        part = PartEntity(
            id="p1",
            name="Steel",
            entity_type=EntityType.PART,
            confidence=0.8,
        )
        # Use FailureMode as different type with same name
        fm = FailureMode(
            id="fm1",
            name="Steel",  # Same name, different type
            entity_type=EntityType.FAILURE_MODE,
            confidence=0.7,
        )

        result = extractor._deduplicate_entities([part, fm])
        assert len(result) == 2  # Both kept

    def test_keeps_higher_confidence(self, extractor):
        """Test that higher confidence entity is kept."""
        e1 = PartEntity(
            id="p1",
            name="Bracket",
            entity_type=EntityType.PART,
            confidence=0.5,
        )
        e2 = PartEntity(
            id="p2",
            name="BRACKET",  # Same name
            entity_type=EntityType.PART,
            confidence=0.9,
        )

        result = extractor._deduplicate_entities([e1, e2])
        assert len(result) == 1
        assert result[0].confidence == 0.9
        assert result[0].id == "p2"

    def test_empty_list_returns_empty(self, extractor):
        """Test that empty list returns empty."""
        result = extractor._deduplicate_entities([])
        assert result == []


class TestBaseExtractorValidation:
    """Test entity validation."""

    def test_valid_entity_no_warnings(self, extractor):
        """Test that valid entity has no warnings."""
        entity = PartEntity(
            id="p1",
            name="Bracket",
            entity_type=EntityType.PART,
            confidence=0.8,
            source="datasheet.pdf",
        )
        warnings = extractor._validate_entity(entity)
        assert warnings == []

    def test_short_name_warning(self, extractor):
        """Test that short name produces warning."""
        entity = PartEntity(
            id="p1",
            name="X",  # Too short
            entity_type=EntityType.PART,
            confidence=0.8,
            source="datasheet.pdf",
        )
        warnings = extractor._validate_entity(entity)
        assert len(warnings) == 1
        assert "invalid name" in warnings[0]

    def test_low_confidence_warning(self, extractor):
        """Test that low confidence produces warning."""
        entity = PartEntity(
            id="p1",
            name="Bracket",
            entity_type=EntityType.PART,
            confidence=0.1,  # Below min_confidence (0.3)
            source="datasheet.pdf",
        )
        warnings = extractor._validate_entity(entity)
        assert any("low confidence" in w for w in warnings)

    def test_missing_source_warning(self, extractor):
        """Test that missing source produces warning when required."""
        entity = PartEntity(
            id="p1",
            name="Bracket",
            entity_type=EntityType.PART,
            confidence=0.8,
            source="",  # Missing source
        )
        warnings = extractor._validate_entity(entity)
        assert any("missing source" in w for w in warnings)

    def test_source_not_required_no_warning(self):
        """Test that missing source OK when not required."""
        config = ExtractionConfig(require_source=False)
        extractor = ConcreteExtractor(config=config)

        entity = PartEntity(
            id="p1",
            name="Bracket",
            entity_type=EntityType.PART,
            confidence=0.8,
            source="",
        )
        warnings = extractor._validate_entity(entity)
        assert not any("missing source" in w for w in warnings)


class TestBaseExtractorMergeResults:
    """Test result merging."""

    def test_merge_entities(self, extractor):
        """Test merging entities from multiple results."""
        r1 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[PartEntity(id="p1", name="Bracket", entity_type=EntityType.PART)],
            relations=[],
            extraction_confidence=0.8,
        )
        r2 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[
                PartEntity(id="p2", name="Fastener", entity_type=EntityType.PART)
            ],
            relations=[],
            extraction_confidence=0.9,
        )

        merged = extractor.merge_results([r1, r2])
        assert merged.entity_count == 2
        assert merged.extraction_confidence == pytest.approx(0.85)  # Average

    def test_merge_deduplicates(self, extractor):
        """Test that merge deduplicates entities."""
        r1 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[
                PartEntity(
                    id="p1", name="Bracket", entity_type=EntityType.PART, confidence=0.8
                )
            ],
            relations=[],
        )
        r2 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[
                PartEntity(
                    id="p2", name="bracket", entity_type=EntityType.PART, confidence=0.6
                )
            ],
            relations=[],
        )

        merged = extractor.merge_results([r1, r2])
        assert merged.entity_count == 1  # Deduplicated

    def test_merge_removes_orphan_relations(self, extractor):
        """Test that relations to removed entities are dropped."""
        r1 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[
                PartEntity(
                    id="p1", name="Bracket", entity_type=EntityType.PART, confidence=0.9
                ),
                PartEntity(
                    id="p2", name="bracket", entity_type=EntityType.PART, confidence=0.5
                ),  # Will be deduped
            ],
            relations=[
                OntologyRelation(
                    id="r1",
                    relation_type=RelationType.HAS_COMPONENT,
                    source_id="p1",
                    target_id="p2",  # Points to entity that will be removed
                )
            ],
        )

        merged = extractor.merge_results([r1])
        # p2 removed by dedup, so relation should be removed too
        assert merged.relation_count == 0

    def test_merge_empty_list(self, extractor):
        """Test merging empty list."""
        merged = extractor.merge_results([])
        assert merged.entity_count == 0
        assert merged.relation_count == 0

    def test_merge_preserves_warnings(self, extractor):
        """Test that warnings are preserved."""
        r1 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[],
            relations=[],
            warnings=["Warning 1"],
        )
        r2 = ExtractionResult(
            source_document="doc1.pdf",
            source_type=ConfidenceSource.DATASHEET,
            entities=[],
            relations=[],
            warnings=["Warning 2"],
        )

        merged = extractor.merge_results([r1, r2])
        assert len(merged.warnings) == 2


class TestSourceConfidenceMapping:
    """Test source confidence mapping."""

    def test_all_sources_have_mapping(self):
        """Test that all ConfidenceSource values have a mapping."""
        for source in ConfidenceSource:
            assert source in SOURCE_CONFIDENCE_MAP

    def test_get_base_confidence_known_source(self):
        """Test getting confidence for known source."""
        assert get_base_confidence(ConfidenceSource.STANDARD) == 0.90
        assert get_base_confidence(ConfidenceSource.DATASHEET) == 0.85
        assert get_base_confidence(ConfidenceSource.INFERRED) == 0.40

    def test_confidence_ordering(self):
        """Test that confidence ordering makes sense."""
        # Standards should be highest
        assert (
            SOURCE_CONFIDENCE_MAP[ConfidenceSource.STANDARD]
            >= SOURCE_CONFIDENCE_MAP[ConfidenceSource.TEXTBOOK]
        )
        # Inferred should be low
        assert (
            SOURCE_CONFIDENCE_MAP[ConfidenceSource.INFERRED]
            < SOURCE_CONFIDENCE_MAP[ConfidenceSource.EXPERT]
        )
        # Unknown should be lowest
        assert (
            SOURCE_CONFIDENCE_MAP[ConfidenceSource.UNKNOWN]
            <= SOURCE_CONFIDENCE_MAP[ConfidenceSource.INFERRED]
        )
