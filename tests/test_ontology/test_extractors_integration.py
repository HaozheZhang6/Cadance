"""Integration tests for ontology extractors with real documents.

These tests download real engineering documents and validate extraction.
Requires network access and may be slow.
"""

import asyncio
import tempfile
import urllib.request
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pdfplumber
import pytest

from src.ontology import ConfidenceSource, EntityType
from src.ontology.extractors.datasheet_extractor import DatasheetExtractor
from src.ontology.extractors.failure_mode_extractor import FailureModeExtractor

# Test document URLs (small, publicly accessible)
TEST_DOCS = {
    "aiag_fmea": {
        "url": "https://elsmar.com/pdf_files/FMEA%20and%20Reliability%20Analysis/AIAG%20FMEA-Ranking-Tables.pdf",
        "type": "fmea",
        "expected_keywords": ["severity", "detection", "ranking", "failure"],
    },
    "ti_lm317": {
        "url": "https://www.ti.com/lit/ds/symlink/lm317.pdf",
        "type": "datasheet",
        "expected_keywords": ["voltage", "regulator", "output", "input"],
    },
}


def download_pdf(url: str, cache_dir: Path) -> Path:
    """Download PDF to cache directory."""
    filename = url.split("/")[-1]
    cache_path = cache_dir / filename

    if not cache_path.exists():
        urllib.request.urlretrieve(url, cache_path)

    return cache_path


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:10]:  # Limit to first 10 pages
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


@pytest.fixture(scope="module")
def pdf_cache_dir():
    """Create a cache directory for downloaded PDFs."""
    cache_dir = Path(tempfile.gettempdir()) / "ontology_test_pdfs"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


class TestRealDocumentDownload:
    """Test that real documents can be downloaded and parsed."""

    @pytest.mark.integration
    def test_download_aiag_fmea(self, pdf_cache_dir):
        """Test downloading AIAG FMEA ranking tables."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 1000  # At least 1KB

    @pytest.mark.integration
    def test_extract_text_from_aiag_fmea(self, pdf_cache_dir):
        """Test extracting text from AIAG FMEA PDF."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        assert len(text) > 100
        # Check for expected FMEA keywords
        text_lower = text.lower()
        for keyword in TEST_DOCS["aiag_fmea"]["expected_keywords"]:
            assert keyword in text_lower, f"Expected '{keyword}' in FMEA document"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_download_ti_datasheet(self, pdf_cache_dir):
        """Test downloading TI LM317 datasheet."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 10000  # At least 10KB

    @pytest.mark.integration
    @pytest.mark.slow
    def test_extract_text_from_ti_datasheet(self, pdf_cache_dir):
        """Test extracting text from TI datasheet."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        assert len(text) > 500
        text_lower = text.lower()
        for keyword in TEST_DOCS["ti_lm317"]["expected_keywords"]:
            assert keyword in text_lower, f"Expected '{keyword}' in datasheet"


class TestDatasheetExtractorWithRealDocs:
    """Test DatasheetExtractor with real document content."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_prompt_generation_with_real_content(self, pdf_cache_dir):
        """Test that extraction prompt is generated correctly for real content."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        extractor = DatasheetExtractor()
        prompt = extractor.get_extraction_prompt(
            content=text[:4000],  # First 4000 chars
            component_name="LM317",
            source="lm317.pdf",
        )

        assert "LM317" in prompt
        assert "lm317.pdf" in prompt
        assert "specifications" in prompt.lower()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_mock_extraction_with_real_content(self, pdf_cache_dir):
        """Test mock extraction returns valid structure with real content."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        extractor = DatasheetExtractor()  # No LLM client = mock mode
        result = asyncio.run(
            extractor.extract(
                content=text,
                source="lm317.pdf",
                component_name="LM317 Voltage Regulator",
            )
        )

        assert result.entity_count >= 1
        assert result.source_document == "lm317.pdf"
        assert result.source_type == ConfidenceSource.DATASHEET

        # Check entity structure
        part = result.entities[0]
        assert part.entity_type == EntityType.PART
        assert part.name == "LM317 Voltage Regulator"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_llm_extraction_with_mocked_response(self, pdf_cache_dir):
        """Test extraction with mocked LLM response based on real content."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        # Create mock LLM client with realistic response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """{
            "component": {
                "name": "LM317",
                "part_numbers": {"Texas Instruments": "LM317"},
                "category": "voltage regulator",
                "subcategory": "linear",
                "description": "3-terminal adjustable voltage regulator"
            },
            "specifications": {
                "output_voltage": {
                    "value": 1.25,
                    "unit": "V",
                    "min": 1.2,
                    "max": 37,
                    "conditions": "adjustable"
                },
                "output_current": {
                    "value": 1.5,
                    "unit": "A",
                    "max": 2.2
                },
                "line_regulation": {
                    "value": 0.01,
                    "unit": "%/V"
                }
            },
            "materials": ["silicon"],
            "standards": ["JEDEC"],
            "operating_conditions": {
                "temperature_min": 0,
                "temperature_max": 125
            }
        }"""
        mock_llm.chat = AsyncMock(return_value=mock_response)

        extractor = DatasheetExtractor(llm_client=mock_llm)
        result = asyncio.run(
            extractor.extract(
                content=text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        assert result.entity_count >= 1
        part = result.entities[0]
        assert part.name == "LM317"
        assert part.category == "voltage regulator"
        assert "output_voltage" in part.specifications
        assert part.specifications["output_voltage"]["unit"] == "V"


class TestFailureModeExtractorWithRealDocs:
    """Test FailureModeExtractor with real FMEA documents."""

    @pytest.mark.integration
    def test_prompt_generation_with_fmea_content(self, pdf_cache_dir):
        """Test extraction prompt for real FMEA content."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        extractor = FailureModeExtractor()
        prompt = extractor.get_extraction_prompt(
            content=text,
            doc_type="FMEA",
            source="aiag_fmea.pdf",
        )

        assert "failure" in prompt.lower()
        assert len(prompt) > 100

    @pytest.mark.integration
    def test_fmea_content_contains_ranking_info(self, pdf_cache_dir):
        """Verify FMEA document contains expected ranking information."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)
        text_lower = text.lower()

        # AIAG FMEA should have severity ratings 1-10
        assert "severity" in text_lower
        # Should have ranking information
        assert "ranking" in text_lower
        # Should have detection ratings
        assert "detection" in text_lower
        # Should reference failure modes
        assert "failure" in text_lower

    @pytest.mark.integration
    def test_mock_fmea_extraction(self, pdf_cache_dir):
        """Test mock FMEA extraction with real content."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        extractor = FailureModeExtractor()  # No LLM = mock mode
        result = asyncio.run(
            extractor.extract(
                content=text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        assert result.source_document == "aiag_fmea.pdf"
        assert result.source_type == ConfidenceSource.STANDARD


class TestChunkingWithRealDocs:
    """Test document chunking with real long documents."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_chunking_preserves_content(self, pdf_cache_dir):
        """Test that chunking doesn't lose content from real docs."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        from src.ontology.extractors.base import ExtractionConfig

        config = ExtractionConfig(chunk_size=2000, chunk_overlap=200)
        extractor = DatasheetExtractor(config=config)
        chunks = extractor._chunk_text(text)

        # Should create multiple chunks for long doc
        if len(text) > 2000:
            assert len(chunks) > 1

        # Chunks should cover the document
        # (accounting for overlap, total chars should be >= original)
        total_chunk_chars = sum(len(c) for c in chunks)
        assert total_chunk_chars >= len(text) * 0.9  # Allow 10% loss from boundaries

    @pytest.mark.integration
    def test_chunking_respects_boundaries(self, pdf_cache_dir):
        """Test that chunking prefers sentence/paragraph boundaries."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        from src.ontology.extractors.base import ExtractionConfig

        config = ExtractionConfig(chunk_size=1000, chunk_overlap=100)
        extractor = DatasheetExtractor(config=config)
        chunks = extractor._chunk_text(text)

        # Most chunks should end at sentence boundaries (. or newline)
        sentence_endings = 0
        for chunk in chunks[:-1]:  # Exclude last chunk
            if chunk.rstrip().endswith((".", "!", "?", "\n")):
                sentence_endings += 1

        if len(chunks) > 2:
            # At least half should end at sentence boundaries
            assert sentence_endings >= len(chunks) // 2


class TestExtractionResultValidation:
    """Test that extraction results meet quality criteria."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_extracted_entities_have_required_fields(self, pdf_cache_dir):
        """Test that extracted entities have all required fields."""
        pdf_path = download_pdf(TEST_DOCS["ti_lm317"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        extractor = DatasheetExtractor()
        result = asyncio.run(
            extractor.extract(
                content=text,
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        for entity in result.entities:
            assert entity.id, "Entity must have ID"
            assert entity.name, "Entity must have name"
            assert entity.entity_type, "Entity must have type"
            assert entity.confidence > 0, "Entity must have positive confidence"

    @pytest.mark.integration
    def test_extraction_confidence_in_valid_range(self, pdf_cache_dir):
        """Test that confidence values are in valid range."""
        pdf_path = download_pdf(TEST_DOCS["aiag_fmea"]["url"], pdf_cache_dir)
        text = extract_text_from_pdf(pdf_path)

        extractor = FailureModeExtractor()
        result = asyncio.run(
            extractor.extract(
                content=text,
                source="fmea.pdf",
            )
        )

        assert 0 <= result.extraction_confidence <= 1
        for entity in result.entities:
            assert 0 <= entity.confidence <= 1
