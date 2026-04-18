"""Tests for physics domain types."""

from src.physics.domains import (
    DomainRelevance,
    PhysicsDomain,
    PhysicsScreeningResult,
)


class TestPhysicsDomain:
    """Tests for PhysicsDomain enum."""

    def test_all_eleven_domains_exist(self):
        """PhysicsDomain should have exactly 11 domains."""
        assert len(PhysicsDomain) == 11

    def test_domain_values(self):
        """PhysicsDomain should have correct string values."""
        expected_domains = [
            "mechanical",
            "thermal",
            "electrical_power",
            "signals_timing",
            "electromagnetic",
            "fluids",
            "chemical_materials",
            "optical_radiative",
            "acoustic",
            "manufacturing",
            "safety",
        ]
        actual_values = [d.value for d in PhysicsDomain]
        assert set(actual_values) == set(expected_domains)

    def test_domain_is_string_enum(self):
        """PhysicsDomain should be a string enum."""
        assert isinstance(PhysicsDomain.MECHANICAL.value, str)
        assert PhysicsDomain.MECHANICAL == "mechanical"


class TestDomainRelevance:
    """Tests for DomainRelevance dataclass."""

    def test_create_domain_relevance(self):
        """DomainRelevance should be creatable with all fields."""
        relevance = DomainRelevance(
            domain=PhysicsDomain.MECHANICAL,
            is_relevant=True,
            confidence=0.85,
            reason="Load-bearing structure",
            keywords_matched=["stress", "load", "force"],
            suggested_checks=["FEA analysis", "fatigue testing"],
            priority="high",
        )

        assert relevance.domain == PhysicsDomain.MECHANICAL
        assert relevance.is_relevant is True
        assert relevance.confidence == 0.85
        assert relevance.reason == "Load-bearing structure"
        assert len(relevance.keywords_matched) == 3
        assert "stress" in relevance.keywords_matched
        assert len(relevance.suggested_checks) == 2
        assert relevance.priority == "high"

    def test_domain_relevance_confidence_bounds(self):
        """DomainRelevance confidence should be between 0 and 1."""
        # Valid confidence
        relevance = DomainRelevance(
            domain=PhysicsDomain.THERMAL,
            is_relevant=False,
            confidence=0.0,
            reason="Not applicable",
            keywords_matched=[],
            suggested_checks=[],
            priority="low",
        )
        assert relevance.confidence == 0.0

        relevance_high = DomainRelevance(
            domain=PhysicsDomain.THERMAL,
            is_relevant=True,
            confidence=1.0,
            reason="Direct thermal constraints",
            keywords_matched=["temperature"],
            suggested_checks=["thermal analysis"],
            priority="critical",
        )
        assert relevance_high.confidence == 1.0

    def test_domain_relevance_priority_values(self):
        """DomainRelevance should support critical, high, normal, low priorities."""
        priorities = ["critical", "high", "normal", "low"]
        for priority in priorities:
            relevance = DomainRelevance(
                domain=PhysicsDomain.SAFETY,
                is_relevant=True,
                confidence=0.9,
                reason="Test",
                keywords_matched=[],
                suggested_checks=[],
                priority=priority,
            )
            assert relevance.priority == priority


class TestPhysicsScreeningResult:
    """Tests for PhysicsScreeningResult dataclass."""

    def test_create_screening_result(self):
        """PhysicsScreeningResult should be creatable with all fields."""
        relevant = DomainRelevance(
            domain=PhysicsDomain.MECHANICAL,
            is_relevant=True,
            confidence=0.9,
            reason="Structural component",
            keywords_matched=["bracket", "load"],
            suggested_checks=["stress analysis"],
            priority="high",
        )
        irrelevant = DomainRelevance(
            domain=PhysicsDomain.ACOUSTIC,
            is_relevant=False,
            confidence=0.1,
            reason="No acoustic requirements",
            keywords_matched=[],
            suggested_checks=[],
            priority="low",
        )

        result = PhysicsScreeningResult(
            contract_id="contract_001",
            relevant_domains=[relevant],
            irrelevant_domains=[irrelevant],
            screening_confidence=0.85,
            needs_human_review=False,
        )

        assert result.contract_id == "contract_001"
        assert len(result.relevant_domains) == 1
        assert len(result.irrelevant_domains) == 1
        assert result.screening_confidence == 0.85
        assert result.needs_human_review is False

    def test_screening_result_with_multiple_relevant_domains(self):
        """PhysicsScreeningResult should support multiple relevant domains."""
        domains = [
            DomainRelevance(
                domain=PhysicsDomain.MECHANICAL,
                is_relevant=True,
                confidence=0.9,
                reason="Load bearing",
                keywords_matched=["load"],
                suggested_checks=["FEA"],
                priority="high",
            ),
            DomainRelevance(
                domain=PhysicsDomain.THERMAL,
                is_relevant=True,
                confidence=0.7,
                reason="Heat generation",
                keywords_matched=["temperature"],
                suggested_checks=["thermal sim"],
                priority="normal",
            ),
            DomainRelevance(
                domain=PhysicsDomain.MANUFACTURING,
                is_relevant=True,
                confidence=0.8,
                reason="Machining constraints",
                keywords_matched=["tolerance"],
                suggested_checks=["DFM review"],
                priority="high",
            ),
        ]

        result = PhysicsScreeningResult(
            contract_id="contract_002",
            relevant_domains=domains,
            irrelevant_domains=[],
            screening_confidence=0.75,
            needs_human_review=True,
        )

        assert len(result.relevant_domains) == 3
        assert result.needs_human_review is True

    def test_screening_result_needs_human_review_flag(self):
        """PhysicsScreeningResult should flag for human review when confidence is low."""
        result = PhysicsScreeningResult(
            contract_id="contract_003",
            relevant_domains=[],
            irrelevant_domains=[],
            screening_confidence=0.3,
            needs_human_review=True,
        )
        assert result.needs_human_review is True
