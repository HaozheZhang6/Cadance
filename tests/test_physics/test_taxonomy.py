"""Tests for physics taxonomy."""

from src.physics.domains import PhysicsDomain
from src.physics.taxonomy import PHYSICS_TAXONOMY, get_domain_keywords


class TestPhysicsTaxonomy:
    """Tests for PHYSICS_TAXONOMY constant."""

    def test_taxonomy_has_all_domains(self):
        """PHYSICS_TAXONOMY should have entries for all 11 domains."""
        assert len(PHYSICS_TAXONOMY) == 11
        for domain in PhysicsDomain:
            assert domain in PHYSICS_TAXONOMY

    def test_each_domain_has_required_fields(self):
        """Each domain entry should have keywords, failure_modes, key_parameters, typical_checks."""
        required_fields = [
            "keywords",
            "failure_modes",
            "key_parameters",
            "typical_checks",
        ]

        for domain, data in PHYSICS_TAXONOMY.items():
            for field in required_fields:
                assert field in data, f"{domain.value} missing {field}"
                assert isinstance(
                    data[field], list
                ), f"{domain.value}.{field} should be a list"
                assert (
                    len(data[field]) > 0
                ), f"{domain.value}.{field} should not be empty"

    def test_mechanical_domain_keywords(self):
        """Mechanical domain should have relevant keywords."""
        mechanical = PHYSICS_TAXONOMY[PhysicsDomain.MECHANICAL]
        assert "stress" in mechanical["keywords"]
        assert "load" in mechanical["keywords"]
        assert "force" in mechanical["keywords"]

    def test_thermal_domain_keywords(self):
        """Thermal domain should have relevant keywords."""
        thermal = PHYSICS_TAXONOMY[PhysicsDomain.THERMAL]
        assert "temperature" in thermal["keywords"]
        assert "heat" in thermal["keywords"]

    def test_electrical_power_domain_keywords(self):
        """Electrical power domain should have relevant keywords."""
        electrical = PHYSICS_TAXONOMY[PhysicsDomain.ELECTRICAL_POWER]
        assert "voltage" in electrical["keywords"]
        assert "current" in electrical["keywords"]
        assert "power" in electrical["keywords"]

    def test_safety_domain_keywords(self):
        """Safety domain should have relevant keywords."""
        safety = PHYSICS_TAXONOMY[PhysicsDomain.SAFETY]
        assert "hazard" in safety["keywords"] or "safety" in safety["keywords"]

    def test_mechanical_failure_modes(self):
        """Mechanical domain should have relevant failure modes."""
        mechanical = PHYSICS_TAXONOMY[PhysicsDomain.MECHANICAL]
        # Should include common mechanical failures
        failure_modes_lower = [fm.lower() for fm in mechanical["failure_modes"]]
        has_fatigue = any("fatigue" in fm for fm in failure_modes_lower)
        has_fracture = any(
            "fracture" in fm or "yield" in fm or "stress" in fm
            for fm in failure_modes_lower
        )
        assert (
            has_fatigue or has_fracture
        ), "Mechanical should have fatigue or fracture failure modes"


class TestGetDomainKeywords:
    """Tests for get_domain_keywords function."""

    def test_get_keywords_for_valid_domain(self):
        """get_domain_keywords should return keywords for valid domain."""
        keywords = get_domain_keywords(PhysicsDomain.MECHANICAL)
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "stress" in keywords

    def test_get_keywords_for_all_domains(self):
        """get_domain_keywords should work for all domains."""
        for domain in PhysicsDomain:
            keywords = get_domain_keywords(domain)
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_keywords_are_lowercase(self):
        """Keywords should be lowercase for consistent matching."""
        for domain in PhysicsDomain:
            keywords = get_domain_keywords(domain)
            for keyword in keywords:
                assert (
                    keyword == keyword.lower()
                ), f"Keyword '{keyword}' should be lowercase"
