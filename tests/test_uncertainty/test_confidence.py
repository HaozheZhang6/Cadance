"""Tests for confidence classification."""

import pytest

from src.uncertainty.confidence import ConfidenceClassifier, EvidenceType


class TestEvidenceType:
    """Tests for EvidenceType enum."""

    def test_evidence_types_exist(self):
        """All evidence types should be defined."""
        assert EvidenceType.FIRST_PRINCIPLES is not None
        assert EvidenceType.TESTED_INTERNALLY is not None
        assert EvidenceType.DATASHEET is not None
        assert EvidenceType.PUBLISHED_LITERATURE is not None
        assert EvidenceType.INFERRED_BY_ANALOGY is not None
        assert EvidenceType.UNKNOWN is not None


class TestConfidenceClassifier:
    """Tests for ConfidenceClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ConfidenceClassifier()

    def test_classifier_creation(self, classifier):
        """Classifier should be creatable."""
        assert classifier is not None

    def test_first_principles_confidence(self, classifier):
        """First-principles physics should have highest confidence."""
        confidence = classifier.classify(EvidenceType.FIRST_PRINCIPLES)
        assert confidence == 0.95

    def test_tested_internally_confidence(self, classifier):
        """Tested internally should have high confidence."""
        confidence = classifier.classify(EvidenceType.TESTED_INTERNALLY)
        assert confidence == 0.90

    def test_datasheet_confidence(self, classifier):
        """Datasheet bounds should have good confidence."""
        confidence = classifier.classify(EvidenceType.DATASHEET)
        assert confidence == 0.80

    def test_published_literature_confidence(self, classifier):
        """Published literature should have moderate confidence."""
        confidence = classifier.classify(EvidenceType.PUBLISHED_LITERATURE)
        assert confidence == 0.55

    def test_inferred_by_analogy_confidence(self, classifier):
        """Inferred by analogy should have lower confidence."""
        confidence = classifier.classify(EvidenceType.INFERRED_BY_ANALOGY)
        assert confidence == 0.40

    def test_unknown_confidence(self, classifier):
        """Unknown should have lowest confidence."""
        confidence = classifier.classify(EvidenceType.UNKNOWN)
        assert confidence == 0.20

    def test_get_confidence_matrix(self, classifier):
        """Classifier should return full confidence matrix."""
        matrix = classifier.get_matrix()
        assert len(matrix) == 6
        assert matrix[EvidenceType.FIRST_PRINCIPLES] == 0.95
        assert matrix[EvidenceType.UNKNOWN] == 0.20

    def test_classify_from_string(self, classifier):
        """Classifier should accept string evidence types."""
        confidence = classifier.classify_from_string("first_principles")
        assert confidence == 0.95

        confidence = classifier.classify_from_string("datasheet")
        assert confidence == 0.80

    def test_classify_from_string_invalid(self, classifier):
        """Classifier should handle invalid strings gracefully."""
        confidence = classifier.classify_from_string("invalid_type")
        assert confidence == 0.20  # Default to unknown

    def test_describe_confidence_level(self, classifier):
        """Classifier should describe confidence levels."""
        description = classifier.describe(0.95)
        assert "high" in description.lower() or "first" in description.lower()

        description = classifier.describe(0.20)
        assert "low" in description.lower() or "unknown" in description.lower()

    def test_confidence_bounds(self, classifier):
        """All confidences should be between 0 and 1."""
        matrix = classifier.get_matrix()
        for confidence in matrix.values():
            assert 0.0 <= confidence <= 1.0
