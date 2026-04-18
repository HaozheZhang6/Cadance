"""Tests for IEEE 830 quality checks."""

from unittest.mock import Mock

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    EdgeType,
    Intent,
    Requirement,
    RequirementStatus,
    SpecificationNode,
)
from src.hypergraph.store import HypergraphStore
from src.verification.base import VerificationStatus
from src.verification.syntactic.ieee830 import (
    check_ambiguity,
    check_traceability,
    check_verifiability,
)


@pytest.fixture
def engine(tmp_path):
    """Create HypergraphEngine with temp store."""
    store = HypergraphStore(str(tmp_path / "test.json"))
    return HypergraphEngine(store)


@pytest.fixture
def requirement_no_method():
    """Requirement with empty verification_method."""
    return Requirement(
        id="req-001",
        description="Test requirement",
        statement="The system SHALL do something",
        verification_method="",
        status=RequirementStatus.DRAFT,
    )


@pytest.fixture
def requirement_invalid_method():
    """Requirement with invalid verification_method."""
    return Requirement(
        id="req-002",
        description="Test requirement",
        statement="The system SHALL do something",
        verification_method="GUESS",
        status=RequirementStatus.DRAFT,
    )


@pytest.fixture
def requirement_valid_method():
    """Requirement with valid verification_method."""
    return Requirement(
        id="req-003",
        description="Test requirement",
        statement="The system SHALL do something",
        verification_method="TEST",
        status=RequirementStatus.DRAFT,
    )


class TestCheckVerifiability:
    """Tests for check_verifiability function."""

    def test_check_verifiability_missing(self, requirement_no_method):
        """Missing verification_method returns WARNING."""
        result = check_verifiability(requirement_no_method)

        assert result is not None
        assert result.status == VerificationStatus.WARNING
        assert result.tier == "SYN-02"
        assert "Missing verification_method" in result.message
        assert result.node_id == "req-001"

    def test_check_verifiability_invalid(self, requirement_invalid_method):
        """Invalid verification_method returns WARNING."""
        result = check_verifiability(requirement_invalid_method)

        assert result is not None
        assert result.status == VerificationStatus.WARNING
        assert result.tier == "SYN-02"
        assert "Invalid verification_method" in result.message
        assert "GUESS" in result.message
        assert result.node_id == "req-002"

    def test_check_verifiability_valid(self, requirement_valid_method):
        """Valid verification_method returns None (passed)."""
        result = check_verifiability(requirement_valid_method)

        assert result is None

    def test_check_verifiability_all_valid_methods(self):
        """All valid methods pass verification."""
        valid_methods = ["TEST", "ANALYSIS", "INSPECTION", "DEMONSTRATION"]

        for method in valid_methods:
            req = Requirement(
                id=f"req-{method}",
                description="Test",
                statement="The system SHALL work",
                verification_method=method,
            )
            result = check_verifiability(req)
            assert result is None, f"Method {method} should pass"

    def test_check_verifiability_case_insensitive(self):
        """Verification method check is case insensitive."""
        req = Requirement(
            id="req-case",
            description="Test",
            statement="The system SHALL work",
            verification_method="test",  # lowercase
        )
        result = check_verifiability(req)
        assert result is None


class TestCheckTraceability:
    """Tests for check_traceability function."""

    def test_check_traceability_missing_requirement(self, engine):
        """Requirement without DERIVES_FROM edge returns WARNING."""
        req = Requirement(
            id="req-orphan",
            description="Orphan requirement",
            statement="The system SHALL be orphan",
        )
        engine.add_node(req)

        result = check_traceability(req, engine)

        assert result is not None
        assert result.status == VerificationStatus.WARNING
        assert result.tier == "SYN-03"
        assert "Missing traceability" in result.message
        assert result.node_id == "req-orphan"

    def test_check_traceability_has_edge(self, engine):
        """Requirement with DERIVES_FROM edge returns None (passed)."""
        intent = Intent(
            id="intent-001",
            description="Root intent",
            goal="Design a bracket",
        )
        req = Requirement(
            id="req-traced",
            description="Traced requirement",
            statement="The system SHALL trace",
        )

        engine.add_node(intent)
        engine.add_node(req)
        engine.add_edge("req-traced", "intent-001", EdgeType.DERIVES_FROM)

        result = check_traceability(req, engine)

        assert result is None

    def test_check_traceability_has_parent_id_metadata(self, engine):
        """Requirement with parent_id in metadata returns None."""
        req = Requirement(
            id="req-meta",
            description="Requirement with metadata parent",
            statement="The system SHALL have parent",
            metadata={"parent_id": "intent-001"},
        )
        engine.add_node(req)

        result = check_traceability(req, engine)

        assert result is None

    def test_check_traceability_spec_has_derives_from(self, engine):
        """SpecificationNode with non-empty derives_from returns None."""
        spec = SpecificationNode(
            id="spec-001",
            description="Specification with derives_from",
            derives_from=["req-001"],
        )
        engine.add_node(spec)

        result = check_traceability(spec, engine)

        assert result is None

    def test_check_traceability_spec_has_satisfies_edge(self, engine):
        """SpecificationNode with SATISFIES edge returns None."""
        req = Requirement(
            id="req-001",
            description="Parent requirement",
            statement="The system SHALL work",
        )
        spec = SpecificationNode(
            id="spec-002",
            description="Specification with SATISFIES edge",
            derives_from=[],
        )

        engine.add_node(req)
        engine.add_node(spec)
        engine.add_edge("spec-002", "req-001", EdgeType.SATISFIES)

        result = check_traceability(spec, engine)

        assert result is None

    def test_check_traceability_spec_no_links(self, engine):
        """SpecificationNode without any links returns WARNING."""
        spec = SpecificationNode(
            id="spec-orphan",
            description="Orphan specification",
            derives_from=[],
        )
        engine.add_node(spec)

        result = check_traceability(spec, engine)

        assert result is not None
        assert result.status == VerificationStatus.WARNING
        assert result.tier == "SYN-03"
        assert "Missing traceability" in result.message

    def test_check_traceability_non_traceable_type(self, engine):
        """Non-traceable node types return None."""
        intent = Intent(
            id="intent-skip",
            description="Intent is not traceable",
            goal="Some goal",
        )
        engine.add_node(intent)

        result = check_traceability(intent, engine)

        assert result is None


class TestCheckAmbiguity:
    """Tests for check_ambiguity function."""

    def test_check_ambiguity_returns_warning(self):
        """LLM detecting ambiguity returns WARNING result."""
        mock_llm = Mock()
        mock_llm.complete_json.return_value = {
            "node_id": "req-ambig",
            "issues": [
                {
                    "issue_type": "AMBIGUITY",
                    "severity": "WARNING",
                    "location": "lightweight",
                    "explanation": "Vague term without quantification",
                }
            ],
        }

        req = Requirement(
            id="req-ambig",
            description="Ambiguous requirement",
            statement="The bracket shall be lightweight",
        )

        results = check_ambiguity(req, mock_llm)

        assert len(results) == 1
        assert results[0].status == VerificationStatus.WARNING
        assert results[0].tier == "SYN-01"
        assert "Ambiguity detected" in results[0].message
        assert results[0].node_id == "req-ambig"

    def test_check_ambiguity_no_issues(self):
        """LLM finding no issues returns empty list."""
        mock_llm = Mock()
        mock_llm.complete_json.return_value = {
            "node_id": "req-clear",
            "issues": [],
        }

        req = Requirement(
            id="req-clear",
            description="Clear requirement",
            statement="The bracket shall withstand 50N load with 2.5x safety factor",
        )

        results = check_ambiguity(req, mock_llm)

        assert len(results) == 0

    def test_check_ambiguity_multiple_issues(self):
        """LLM finding multiple issues returns multiple results."""
        mock_llm = Mock()
        mock_llm.complete_json.return_value = {
            "node_id": "req-multi",
            "issues": [
                {
                    "issue_type": "AMBIGUITY",
                    "severity": "WARNING",
                    "location": "fast",
                    "explanation": "Vague term - what is fast?",
                },
                {
                    "issue_type": "AMBIGUITY",
                    "severity": "INFO",
                    "location": "reliable",
                    "explanation": "Undefined reliability metric",
                },
            ],
        }

        req = Requirement(
            id="req-multi",
            description="Multiple issues",
            statement="The system shall be fast and reliable",
        )

        results = check_ambiguity(req, mock_llm)

        assert len(results) == 2

    def test_check_ambiguity_non_text_node(self):
        """Node without text field returns empty list."""
        mock_llm = Mock()

        # Intent has goal, not statement - _get_node_text returns None
        intent = Intent(
            id="intent-001",
            description="Test intent",
            goal="Design something",
        )

        results = check_ambiguity(intent, mock_llm)

        assert len(results) == 0
        mock_llm.complete_json.assert_not_called()

    def test_check_ambiguity_spec_node(self):
        """SpecificationNode description is checked for ambiguity."""
        mock_llm = Mock()
        mock_llm.complete_json.return_value = {
            "node_id": "spec-001",
            "issues": [
                {
                    "issue_type": "AMBIGUITY",
                    "severity": "WARNING",
                    "location": "adequate",
                    "explanation": "Undefined adequacy criteria",
                }
            ],
        }

        spec = SpecificationNode(
            id="spec-001",
            description="Shall have adequate strength",
        )

        results = check_ambiguity(spec, mock_llm)

        assert len(results) == 1
        assert "Ambiguity detected" in results[0].message

    def test_check_ambiguity_filters_non_ambiguity_issues(self):
        """Only AMBIGUITY issue_type generates results."""
        mock_llm = Mock()
        mock_llm.complete_json.return_value = {
            "node_id": "req-001",
            "issues": [
                {
                    "issue_type": "UNVERIFIABLE",
                    "severity": "WARNING",
                    "location": "somewhere",
                    "explanation": "Not ambiguity",
                }
            ],
        }

        req = Requirement(
            id="req-001",
            description="Test",
            statement="The system shall work",
        )

        results = check_ambiguity(req, mock_llm)

        assert len(results) == 0
