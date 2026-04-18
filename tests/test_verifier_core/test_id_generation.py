"""Tests for deterministic ID generation.

Verifies that finding_id, unknown_id, and report_id are content-based
and reproducible across runs.
"""

from verifier_core.id_generation import (
    generate_finding_id,
    generate_report_id,
    generate_unknown_id,
)
from verifier_core.models import Finding, Severity, Unknown


class TestFindingIdDeterminism:
    """Tests for deterministic finding IDs."""

    def test_finding_id_deterministic(self):
        """Same inputs produce same finding ID."""
        id1 = generate_finding_id("rule1", "obj1", "message1")
        id2 = generate_finding_id("rule1", "obj1", "message1")
        assert id1 == id2

    def test_finding_id_unique_per_content(self):
        """Different inputs produce different IDs."""
        id1 = generate_finding_id("rule1", "obj1", "message1")
        id2 = generate_finding_id("rule2", "obj1", "message1")
        id3 = generate_finding_id("rule1", "obj2", "message1")
        id4 = generate_finding_id("rule1", "obj1", "message2")

        assert id1 != id2
        assert id1 != id3
        assert id1 != id4

    def test_finding_id_length(self):
        """Finding IDs are 16 characters."""
        fid = generate_finding_id("rule", "obj", "msg")
        assert len(fid) == 16

    def test_finding_id_with_measured_value(self):
        """Measured values contribute to uniqueness."""
        id1 = generate_finding_id("rule", "obj", "msg", 1.5)
        id2 = generate_finding_id("rule", "obj", "msg", 2.5)
        assert id1 != id2

    def test_finding_id_none_object_ref(self):
        """None object_ref handled gracefully."""
        id1 = generate_finding_id("rule", None, "msg")
        id2 = generate_finding_id("rule", None, "msg")
        assert id1 == id2


class TestUnknownIdDeterminism:
    """Tests for deterministic unknown IDs."""

    def test_unknown_id_deterministic(self):
        """Same inputs produce same unknown ID."""
        id1 = generate_unknown_id("summary", "rule1", "obj1")
        id2 = generate_unknown_id("summary", "rule1", "obj1")
        assert id1 == id2

    def test_unknown_id_unique_per_content(self):
        """Different inputs produce different IDs."""
        id1 = generate_unknown_id("summary1", "rule1", "obj1")
        id2 = generate_unknown_id("summary2", "rule1", "obj1")
        id3 = generate_unknown_id("summary1", "rule2", "obj1")
        id4 = generate_unknown_id("summary1", "rule1", "obj2")

        assert id1 != id2
        assert id1 != id3
        assert id1 != id4

    def test_unknown_id_none_fields(self):
        """None fields handled gracefully."""
        id1 = generate_unknown_id("summary", None, None)
        id2 = generate_unknown_id("summary", None, None)
        assert id1 == id2


class TestReportIdDeterminism:
    """Tests for deterministic report IDs."""

    def test_report_id_deterministic(self):
        """Same inputs produce same report ID."""
        id1 = generate_report_id(["/path/to/file1.json", "/path/to/file2.json"])
        id2 = generate_report_id(["/path/to/file1.json", "/path/to/file2.json"])
        assert id1 == id2

    def test_report_id_order_independent(self):
        """Report ID is order-independent (sorted internally)."""
        id1 = generate_report_id(["/a.json", "/b.json"])
        id2 = generate_report_id(["/b.json", "/a.json"])
        assert id1 == id2

    def test_report_id_without_timestamp(self):
        """Default report ID excludes timestamp for determinism."""
        id1 = generate_report_id(["/file.json"])
        id2 = generate_report_id(["/file.json"])
        assert id1 == id2

    def test_report_id_with_timestamp_differs(self):
        """Including timestamp makes IDs different across runs."""
        id1 = generate_report_id(
            ["/file.json"], include_timestamp=True, timestamp="2024-01-01"
        )
        id2 = generate_report_id(
            ["/file.json"], include_timestamp=True, timestamp="2024-01-02"
        )
        assert id1 != id2

    def test_report_id_without_timestamp_same_as_before(self):
        """IDs without timestamp remain stable."""
        id1 = generate_report_id(["/file.json"], include_timestamp=False)
        id2 = generate_report_id(
            ["/file.json"], include_timestamp=False, timestamp="ignored"
        )
        assert id1 == id2


class TestModelsUseDeterministicIds:
    """Tests that models automatically use deterministic IDs."""

    def test_finding_auto_generates_deterministic_id(self):
        """Finding without finding_id gets deterministic ID."""
        f1 = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Test message",
            object_ref="obj1",
        )
        f2 = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Test message",
            object_ref="obj1",
        )

        # Should have same finding_id (deterministic)
        assert f1.finding_id == f2.finding_id
        assert f1.finding_id is not None
        assert len(f1.finding_id) == 16

    def test_finding_with_explicit_id_preserved(self):
        """Explicitly set finding_id is preserved."""
        f = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Test",
            finding_id="custom_id_1234",
        )
        assert f.finding_id == "custom_id_1234"

    def test_unknown_auto_generates_deterministic_id(self):
        """Unknown without unknown_id gets deterministic ID."""
        u1 = Unknown(
            summary="Test unknown",
            impact="Test impact",
            resolution_plan="Test plan",
            created_by_rule_id="test.rule",
            object_ref="obj1",
        )
        u2 = Unknown(
            summary="Test unknown",
            impact="Test impact",
            resolution_plan="Test plan",
            created_by_rule_id="test.rule",
            object_ref="obj1",
        )

        # Should have same unknown_id (deterministic)
        assert u1.unknown_id == u2.unknown_id
        assert u1.unknown_id is not None
        assert len(u1.unknown_id) == 16

    def test_unknown_with_explicit_id_preserved(self):
        """Explicitly set unknown_id is preserved."""
        u = Unknown(
            summary="Test",
            impact="Impact",
            resolution_plan="Plan",
            unknown_id="custom_unknown",
        )
        assert u.unknown_id == "custom_unknown"

    def test_finding_different_content_different_id(self):
        """Findings with different content get different IDs."""
        f1 = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Message 1",
        )
        f2 = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Message 2",
        )

        assert f1.finding_id != f2.finding_id

    def test_finding_measured_value_affects_id(self):
        """Measured value contributes to finding ID."""
        f1 = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Same message",
            measured_value={"value": 1.0},
        )
        f2 = Finding(
            rule_id="test.rule",
            severity=Severity.ERROR,
            message="Same message",
            measured_value={"value": 2.0},
        )

        # Different measured values should produce different IDs
        assert f1.finding_id != f2.finding_id
