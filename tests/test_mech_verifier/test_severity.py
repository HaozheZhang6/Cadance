"""Tests for Severity enum handling and serialization."""

import pytest

from verifier_core.models import Finding, Severity


class TestSeverityEnum:
    """Tests for the Severity enum."""

    def test_severity_values(self):
        """Verify canonical Severity enum values."""
        assert Severity.BLOCKER.value == "BLOCKER"
        assert Severity.ERROR.value == "ERROR"
        assert Severity.WARN.value == "WARN"
        assert Severity.INFO.value == "INFO"
        assert Severity.UNKNOWN.value == "UNKNOWN"

    def test_severity_str_equality(self):
        """Severity enum should compare equal to its string value (str, Enum)."""
        assert Severity.BLOCKER == "BLOCKER"
        assert Severity.ERROR == "ERROR"
        assert Severity.WARN == "WARN"
        assert Severity.INFO == "INFO"
        assert Severity.UNKNOWN == "UNKNOWN"

    def test_severity_from_string(self):
        """Severity can be constructed from string."""
        assert Severity("BLOCKER") == Severity.BLOCKER
        assert Severity("ERROR") == Severity.ERROR
        assert Severity("WARN") == Severity.WARN
        assert Severity("INFO") == Severity.INFO
        assert Severity("UNKNOWN") == Severity.UNKNOWN

    def test_severity_invalid_string(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError):
            Severity("INVALID")

        with pytest.raises(ValueError):
            Severity("blocker")  # Case-sensitive for uppercase variants


class TestSeveritySerialization:
    """Tests for Severity serialization in Finding."""

    def test_finding_enum_to_dict(self):
        """Finding.to_dict() should serialize Severity enum to string."""
        finding = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Test message",
        )
        d = finding.to_dict()
        assert d["severity"] == "ERROR"
        assert isinstance(d["severity"], str)

    def test_finding_string_auto_converted(self):
        """Finding with string severity should auto-convert to enum."""
        finding = Finding(
            rule_id="test.rule",
            severity="ERROR",  # String input
            message="Test message",
        )
        # After __post_init__, severity should be enum
        assert finding.severity == Severity.ERROR
        assert isinstance(finding.severity, Severity)

    def test_finding_all_severity_levels(self):
        """Test all severity levels serialize correctly."""
        for sev in [
            Severity.BLOCKER,
            Severity.ERROR,
            Severity.WARN,
            Severity.INFO,
            Severity.UNKNOWN,
        ]:
            finding = Finding(
                rule_id="test.rule",
                severity=sev,
                message="Test message",
            )
            d = finding.to_dict()
            assert d["severity"] == sev.value

    def test_finding_lowercase_severity_variants(self):
        """Test lowercase severity variants (for compatibility)."""
        # These are legacy variants defined in Severity enum
        for sev_str in ["error", "warning", "note", "info"]:
            finding = Finding(
                rule_id="test.rule",
                severity=sev_str,
                message="Test message",
            )
            # Should convert to corresponding Severity enum member
            assert isinstance(finding.severity, Severity)


class TestSeverityComparisons:
    """Tests for Severity comparisons."""

    def test_enum_comparison(self):
        """Comparing two enum values."""
        assert Severity.ERROR == Severity.ERROR
        assert Severity.ERROR != Severity.WARN

    def test_finding_severity_comparison(self):
        """Comparing Finding severity to enum."""
        finding = Finding(
            rule_id="test.rule",
            severity=Severity.BLOCKER,
            message="Test message",
        )
        assert finding.severity == Severity.BLOCKER
        assert finding.severity != Severity.ERROR

    def test_finding_severity_in_collection(self):
        """Test severity checks using 'in' operator."""
        findings = [
            Finding(rule_id="r1", severity=Severity.BLOCKER, message="m1"),
            Finding(rule_id="r2", severity=Severity.ERROR, message="m2"),
            Finding(rule_id="r3", severity=Severity.WARN, message="m3"),
        ]

        blockers = [f for f in findings if f.severity == Severity.BLOCKER]
        assert len(blockers) == 1

        errors_or_blockers = [
            f for f in findings if f.severity in (Severity.BLOCKER, Severity.ERROR)
        ]
        assert len(errors_or_blockers) == 2

    def test_any_has_severity(self):
        """Test using any() to check for severity levels."""
        findings = [
            Finding(rule_id="r1", severity=Severity.ERROR, message="m1"),
            Finding(rule_id="r2", severity=Severity.WARN, message="m2"),
        ]

        assert any(f.severity == Severity.ERROR for f in findings)
        assert not any(f.severity == Severity.BLOCKER for f in findings)
