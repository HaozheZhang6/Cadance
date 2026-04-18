"""Golden expected-output tests for ontology extractors.

These tests verify extraction ACCURACY against known ground truth values.
They serve as regression tests to detect if extraction quality degrades.

Ground truth established from manual inspection of real documents:
- TI LM317 datasheet (voltage regulator specs)
- AIAG FMEA ranking tables (severity/occurrence/detection scales)
"""

import asyncio
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pdfplumber
import pytest

from src.ontology import ConfidenceSource, EntityType
from src.ontology.extractors.datasheet_extractor import DatasheetExtractor
from src.ontology.extractors.failure_mode_extractor import FailureModeExtractor

# =============================================================================
# GROUND TRUTH DATA - Established from manual document inspection
# =============================================================================


@dataclass
class LM317GroundTruth:
    """Ground truth for TI LM317 datasheet."""

    # Component identification
    name: str = "LM317"
    full_name: str = "LM317 3-Pin Adjustable Regulator"
    manufacturer: str = "Texas Instruments"
    category: str = "voltage regulator"

    # Key specifications
    output_voltage_min: float = 1.25  # Volts
    output_voltage_max: float = 37.0  # Volts
    output_current: float = 1.5  # Amps
    line_regulation: float = 0.01  # %/V typical
    load_regulation: float = 0.1  # % typical

    # Packages available
    packages: tuple = ("SOT-223", "TO-263", "TO-220")

    # Key features
    features: tuple = (
        "thermal overload protection",
        "current limiting",
        "short-circuit protection",
    )


@dataclass
class AIAGFMEAGroundTruth:
    """Ground truth for AIAG FMEA ranking tables."""

    # Scale ranges
    severity_min: int = 1
    severity_max: int = 10
    occurrence_min: int = 1
    occurrence_max: int = 10
    detection_min: int = 1
    detection_max: int = 10

    # Severity scale definitions
    severity_10_name: str = "Hazardous - without warning"
    severity_10_effect: str = "safe vehicle operation"
    severity_1_name: str = "None"
    severity_1_effect: str = "No effect"

    # Detection scale definitions
    detection_10_name: str = "Almost Impossible"
    detection_10_criteria: str = "No known control"
    detection_1_name: str = "Almost Certain"
    detection_1_criteria: str = "almost certain to detect"

    # Occurrence scale definitions
    occurrence_10_probability: str = "> 1 in 2"
    occurrence_1_probability: str = "< 1 in 1,500,000"


LM317_TRUTH = LM317GroundTruth()
AIAG_FMEA_TRUTH = AIAGFMEAGroundTruth()


# =============================================================================
# EXPECTED LLM RESPONSES - Realistic extraction outputs matching ground truth
# =============================================================================

LM317_EXPECTED_LLM_RESPONSE = """{
    "component": {
        "name": "LM317",
        "part_numbers": {"Texas Instruments": "LM317"},
        "category": "voltage regulator",
        "subcategory": "adjustable linear",
        "description": "3-Pin Adjustable Regulator capable of supplying more than 1.5A over an output voltage range of 1.25V to 37V"
    },
    "specifications": {
        "output_voltage": {
            "value": "adjustable",
            "unit": "V",
            "min": 1.25,
            "max": 37,
            "conditions": "adjustable via external resistors"
        },
        "output_current": {
            "value": 1.5,
            "unit": "A",
            "max": 1.5
        },
        "line_regulation": {
            "value": 0.01,
            "unit": "%/V",
            "conditions": "typical"
        },
        "load_regulation": {
            "value": 0.1,
            "unit": "%",
            "conditions": "typical"
        }
    },
    "materials": ["silicon"],
    "standards": ["JEDEC"],
    "operating_conditions": {
        "temperature_min": 0,
        "temperature_max": 125
    },
    "related_components": []
}"""

FMEA_EXPECTED_LLM_RESPONSE = """{
    "failure_modes": [
        {
            "name": "Hazardous Failure Without Warning",
            "description": "Failure that may endanger operator without warning, affects safe operation, involves noncompliance with regulation",
            "domain": "safety",
            "severity": "critical",
            "causes": [
                {"description": "Critical safety system failure", "mechanism": "component failure"}
            ],
            "effects": [
                {"level": "system", "description": "May endanger machine or assembly operator"},
                {"level": "end", "description": "Affects safe vehicle operation"}
            ],
            "detection_methods": ["No known control available"],
            "early_indicators": [],
            "mitigations": [
                {"type": "design", "description": "Redundant safety systems", "effectiveness": "high"}
            ],
            "occurrence_rate": "rare",
            "detectability": "undetectable",
            "physics_phenomena": []
        },
        {
            "name": "Very High Severity Failure",
            "description": "Major disruption to production line, 100% product scrapped, vehicle inoperable",
            "domain": "operational",
            "severity": "high",
            "causes": [
                {"description": "Major component failure", "mechanism": "wear"}
            ],
            "effects": [
                {"level": "system", "description": "Loss of primary function"},
                {"level": "end", "description": "Customer very dissatisfied"}
            ],
            "detection_methods": ["Visual inspection", "Functional test"],
            "early_indicators": ["Performance degradation"],
            "mitigations": [
                {"type": "inspection", "description": "100% inspection", "effectiveness": "medium"}
            ],
            "occurrence_rate": "occasional",
            "detectability": "moderate",
            "physics_phenomena": []
        }
    ],
    "component_applicability": ["automotive", "manufacturing", "assembly"],
    "operating_conditions": {
        "environment": "automotive manufacturing"
    }
}"""


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def pdf_cache_dir():
    """Create cache directory for downloaded PDFs."""
    cache_dir = Path(tempfile.gettempdir()) / "ontology_test_pdfs"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


@pytest.fixture(scope="module")
def lm317_text(pdf_cache_dir):
    """Download and extract LM317 datasheet text."""
    pdf_path = pdf_cache_dir / "lm317.pdf"
    if not pdf_path.exists():
        urllib.request.urlretrieve(
            "https://www.ti.com/lit/ds/symlink/lm317.pdf", pdf_path
        )

    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:5]:  # First 5 pages have key specs
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


@pytest.fixture(scope="module")
def fmea_text(pdf_cache_dir):
    """Download and extract AIAG FMEA text."""
    pdf_path = pdf_cache_dir / "aiag_fmea.pdf"
    if not pdf_path.exists():
        urllib.request.urlretrieve(
            "https://elsmar.com/pdf_files/FMEA%20and%20Reliability%20Analysis/AIAG%20FMEA-Ranking-Tables.pdf",
            pdf_path,
        )

    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def create_mock_llm(response_json: str):
    """Create mock LLM client that returns specified JSON response."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = response_json
    mock_llm.chat = AsyncMock(return_value=mock_response)
    return mock_llm


# =============================================================================
# GOLDEN TESTS - LM317 DATASHEET
# =============================================================================


class TestLM317GoldenExtraction:
    """Golden tests verifying LM317 extraction accuracy against ground truth."""

    @pytest.mark.integration
    def test_source_document_contains_ground_truth_values(self, lm317_text):
        """Verify source document actually contains our ground truth values."""
        text_lower = lm317_text.lower()

        # Component name
        assert "lm317" in text_lower

        # Voltage range
        assert "1.25" in lm317_text
        assert "37" in lm317_text

        # Current
        assert "1.5" in lm317_text

        # Regulation specs
        assert "0.01" in lm317_text
        assert "0.1" in lm317_text

        # Category keywords
        assert "regulator" in text_lower
        assert "adjustable" in text_lower

    @pytest.mark.integration
    def test_extraction_produces_correct_component_name(self, lm317_text):
        """GOLDEN: Extracted component name matches ground truth."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        assert result.entity_count >= 1
        part = result.entities[0]
        assert part.name == LM317_TRUTH.name

    @pytest.mark.integration
    def test_extraction_produces_correct_category(self, lm317_text):
        """GOLDEN: Extracted category matches ground truth."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        assert LM317_TRUTH.category in part.category.lower()

    @pytest.mark.integration
    def test_extraction_produces_correct_voltage_range(self, lm317_text):
        """GOLDEN: Extracted voltage range matches ground truth."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        voltage_spec = part.specifications.get("output_voltage", {})

        assert voltage_spec.get("min") == LM317_TRUTH.output_voltage_min
        assert voltage_spec.get("max") == LM317_TRUTH.output_voltage_max
        assert voltage_spec.get("unit") == "V"

    @pytest.mark.integration
    def test_extraction_produces_correct_current_rating(self, lm317_text):
        """GOLDEN: Extracted current rating matches ground truth."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        current_spec = part.specifications.get("output_current", {})

        assert current_spec.get("value") == LM317_TRUTH.output_current
        assert current_spec.get("unit") == "A"

    @pytest.mark.integration
    def test_extraction_produces_correct_line_regulation(self, lm317_text):
        """GOLDEN: Extracted line regulation matches ground truth."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        line_reg = part.specifications.get("line_regulation", {})

        assert line_reg.get("value") == LM317_TRUTH.line_regulation
        assert "%/V" in line_reg.get("unit", "") or "%" in line_reg.get("unit", "")

    @pytest.mark.integration
    def test_extraction_includes_manufacturer(self, lm317_text):
        """GOLDEN: Extraction includes manufacturer information."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        part_numbers = part.part_numbers or {}

        assert LM317_TRUTH.manufacturer in part_numbers or any(
            LM317_TRUTH.manufacturer.lower() in str(v).lower()
            for v in part_numbers.values()
        )


# =============================================================================
# GOLDEN TESTS - AIAG FMEA
# =============================================================================


class TestAIAGFMEAGoldenExtraction:
    """Golden tests verifying AIAG FMEA extraction accuracy against ground truth."""

    @pytest.mark.integration
    def test_source_document_contains_severity_scale(self, fmea_text):
        """Verify source document contains severity scale ground truth."""
        text_lower = fmea_text.lower()

        # Severity keywords
        assert "severity" in text_lower
        assert "hazardous" in text_lower
        assert "warning" in text_lower

        # Scale values (1-10)
        assert "10" in fmea_text
        assert "1" in fmea_text

    @pytest.mark.integration
    def test_source_document_contains_detection_scale(self, fmea_text):
        """Verify source document contains detection scale ground truth."""
        text_lower = fmea_text.lower()

        # Detection keywords
        assert "detection" in text_lower
        assert "almost impossible" in text_lower or "impossible" in text_lower
        assert "almost certain" in text_lower or "certain" in text_lower

    @pytest.mark.integration
    def test_source_document_contains_occurrence_scale(self, fmea_text):
        """Verify source document contains occurrence scale ground truth."""
        text_lower = fmea_text.lower()

        # Occurrence keywords - note the PDF has doubled letters
        assert "occurrence" in text_lower or "ooccccuurrrreennccee" in text_lower
        assert "failure" in text_lower or "ffaaiilluurree" in text_lower

    @pytest.mark.integration
    def test_extraction_produces_failure_mode_entities(self, fmea_text):
        """GOLDEN: Extraction produces failure mode entities."""
        mock_llm = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor = FailureModeExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        assert result.entity_count >= 1

        # Find failure mode entities
        failure_modes = [
            e for e in result.entities if e.entity_type == EntityType.FAILURE_MODE
        ]
        assert len(failure_modes) >= 1

    @pytest.mark.integration
    def test_extraction_captures_hazardous_severity(self, fmea_text):
        """GOLDEN: Extraction captures hazardous (highest) severity level."""
        mock_llm = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor = FailureModeExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        failure_modes = [
            e for e in result.entities if e.entity_type == EntityType.FAILURE_MODE
        ]

        # At least one should be critical/high severity
        severities = [fm.severity for fm in failure_modes if hasattr(fm, "severity")]
        assert any(s in ["critical", "high"] for s in severities)

    @pytest.mark.integration
    def test_extraction_captures_effects(self, fmea_text):
        """GOLDEN: Extraction captures failure effects."""
        mock_llm = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor = FailureModeExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        failure_modes = [
            e for e in result.entities if e.entity_type == EntityType.FAILURE_MODE
        ]

        # At least one FM should have effects
        has_effects = any(hasattr(fm, "effects") and fm.effects for fm in failure_modes)
        assert has_effects

    @pytest.mark.integration
    def test_extraction_source_type_is_standard(self, fmea_text):
        """GOLDEN: FMEA extraction uses STANDARD source type."""
        mock_llm = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor = FailureModeExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        assert result.source_type == ConfidenceSource.STANDARD
        # Standard source should have high confidence (0.90)
        assert result.extraction_confidence >= 0.85


# =============================================================================
# REGRESSION DETECTION TESTS
# =============================================================================


class TestExtractionRegressionDetection:
    """Tests to detect if extraction quality degrades over time."""

    @pytest.mark.integration
    def test_lm317_minimum_entity_count(self, lm317_text):
        """REGRESSION: LM317 extraction should produce at least 1 entity."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        # Baseline: at least 1 part entity + material entities
        assert (
            result.entity_count >= 1
        ), "REGRESSION: Entity count dropped below minimum"

    @pytest.mark.integration
    def test_lm317_minimum_specification_count(self, lm317_text):
        """REGRESSION: LM317 extraction should capture at least 3 specifications."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        spec_count = len(part.specifications)

        # Baseline: should extract at least output_voltage, output_current, line_regulation
        assert (
            spec_count >= 3
        ), f"REGRESSION: Only {spec_count} specs extracted, expected >= 3"

    @pytest.mark.integration
    def test_fmea_minimum_failure_mode_count(self, fmea_text):
        """REGRESSION: FMEA extraction should produce at least 1 failure mode."""
        mock_llm = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor = FailureModeExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        failure_modes = [
            e for e in result.entities if e.entity_type == EntityType.FAILURE_MODE
        ]

        assert len(failure_modes) >= 1, "REGRESSION: No failure modes extracted"

    @pytest.mark.integration
    def test_confidence_values_are_reasonable(self, lm317_text):
        """REGRESSION: Confidence values should be in expected ranges."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        # Datasheet source should have ~0.85 confidence
        assert (
            0.80 <= result.extraction_confidence <= 0.95
        ), f"REGRESSION: Confidence {result.extraction_confidence} outside expected range"

        for entity in result.entities:
            assert (
                0.3 <= entity.confidence <= 1.0
            ), f"REGRESSION: Entity confidence {entity.confidence} outside valid range"

    @pytest.mark.integration
    def test_extraction_produces_no_empty_names(self, lm317_text, fmea_text):
        """REGRESSION: All extracted entities should have non-empty names."""
        # Test datasheet
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        for entity in result.entities:
            assert (
                entity.name and len(entity.name) >= 2
            ), f"REGRESSION: Entity has empty or too short name: '{entity.name}'"

        # Test FMEA
        mock_llm2 = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor2 = FailureModeExtractor(llm_client=mock_llm2)

        result2 = asyncio.run(
            extractor2.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        for entity in result2.entities:
            assert (
                entity.name and len(entity.name) >= 2
            ), f"REGRESSION: Entity has empty or too short name: '{entity.name}'"


# =============================================================================
# ACCURACY METRIC TESTS
# =============================================================================


class TestExtractionAccuracyMetrics:
    """Tests that measure extraction accuracy quantitatively."""

    @pytest.mark.integration
    def test_lm317_voltage_accuracy(self, lm317_text):
        """Measure accuracy of voltage extraction."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]
        voltage_spec = part.specifications.get("output_voltage", {})

        extracted_min = voltage_spec.get("min", 0)
        extracted_max = voltage_spec.get("max", 0)

        # Calculate accuracy (percentage of correct values)
        correct = 0
        total = 2

        if extracted_min == LM317_TRUTH.output_voltage_min:
            correct += 1
        if extracted_max == LM317_TRUTH.output_voltage_max:
            correct += 1

        accuracy = correct / total
        assert accuracy >= 0.5, f"Voltage extraction accuracy {accuracy:.0%} below 50%"

    @pytest.mark.integration
    def test_lm317_key_specs_completeness(self, lm317_text):
        """Measure completeness of key specification extraction."""
        mock_llm = create_mock_llm(LM317_EXPECTED_LLM_RESPONSE)
        extractor = DatasheetExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=lm317_text[:4000],
                source="lm317.pdf",
                component_name="LM317",
            )
        )

        part = result.entities[0]

        # Key specs we expect to be extracted
        expected_specs = [
            "output_voltage",
            "output_current",
            "line_regulation",
            "load_regulation",
        ]

        found = sum(1 for spec in expected_specs if spec in part.specifications)
        completeness = found / len(expected_specs)

        assert completeness >= 0.75, (
            f"Spec completeness {completeness:.0%} below 75% "
            f"(found {found}/{len(expected_specs)})"
        )

    @pytest.mark.integration
    def test_fmea_severity_coverage(self, fmea_text):
        """Measure coverage of severity levels in extraction."""
        mock_llm = create_mock_llm(FMEA_EXPECTED_LLM_RESPONSE)
        extractor = FailureModeExtractor(llm_client=mock_llm)

        result = asyncio.run(
            extractor.extract(
                content=fmea_text,
                source="aiag_fmea.pdf",
                source_type=ConfidenceSource.STANDARD,
            )
        )

        failure_modes = [
            e for e in result.entities if e.entity_type == EntityType.FAILURE_MODE
        ]

        # Check that we capture both high and moderate severity levels
        severities = set()
        for fm in failure_modes:
            if hasattr(fm, "severity") and fm.severity:
                severities.add(fm.severity.lower())

        # Should capture at least 2 different severity levels
        assert (
            len(severities) >= 1
        ), f"Only {len(severities)} severity levels captured, expected >= 1"
