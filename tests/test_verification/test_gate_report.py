"""Tests for GateReport and TierResult dataclasses.

Tests verify:
- Pass criteria: 0 V0/V1 failures, 0 V3 failures (warnings OK),
  cross-spec SAT, all contracts SAT, coverage >= threshold
- failure_summary lists all issues
- to_regen_feedback includes all tiers + frozen nodes
"""

from __future__ import annotations

import pytest

from src.verification.base import VerificationResult, VerificationStatus
from src.verification.gate_report import GateReport, TierResult


@pytest.fixture
def all_green_report() -> GateReport:
    """GateReport where everything passes."""
    return GateReport(
        attempt=1,
        tier_results={
            "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
            "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
            "V3-syntactic": TierResult(
                tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
            ),
        },
        cross_spec_result=VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V4-semantic",
            message="SAT",
            details={"coverage": {"compiled": 10, "skipped": 0}},
        ),
        contract_result=VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V4-semantic",
            message="All contracts SAT",
            details={"per_contract": {}},
        ),
        spec_coverage=1.0,
        contract_coverages={},
        coverage_threshold=0.7,
        aggregate_contract_coverage=1.0,
        passing_node_ids={"node_a", "node_b"},
    )


class TestGateReportPassCriteria:
    """Tests for GateReport.passed property."""

    def test_all_green_passes(self, all_green_report):
        """All tiers pass, SAT, coverage 100% -> passed."""
        assert all_green_report.passed is True

    def test_v0_failure_fails_gate(self, all_green_report):
        """V0 failure -> gate fails."""
        all_green_report.tier_results["V0"] = TierResult(
            tier="V0",
            passed=4,
            failed=1,
            warnings=0,
            details=[{"id": "node_x", "message": "Missing field", "severity": "error"}],
        )
        assert all_green_report.passed is False

    def test_v1_failure_fails_gate(self, all_green_report):
        """V1 failure -> gate fails."""
        all_green_report.tier_results["V1"] = TierResult(
            tier="V1",
            passed=4,
            failed=1,
            warnings=0,
            details=[
                {"id": "node_y", "message": "Rule violation", "severity": "error"}
            ],
        )
        assert all_green_report.passed is False

    def test_v3_warnings_still_pass(self, all_green_report):
        """V3 warnings (no failures) -> gate still passes."""
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic",
            passed=3,
            failed=0,
            warnings=2,
            details=[
                {"id": "req_1", "message": "Ambiguous term", "severity": "warning"},
                {
                    "id": "spec_1",
                    "message": "Subjective language",
                    "severity": "warning",
                },
            ],
        )
        assert all_green_report.passed is True

    def test_v3_failure_fails_gate(self, all_green_report):
        """V3 failure -> gate fails."""
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic",
            passed=3,
            failed=1,
            warnings=1,
            details=[
                {"id": "req_2", "message": "Not verifiable", "severity": "error"},
            ],
        )
        assert all_green_report.passed is False

    def test_unsat_cross_spec_fails_gate(self, all_green_report):
        """Cross-spec UNSAT -> gate fails."""
        all_green_report.cross_spec_result = VerificationResult(
            status=VerificationStatus.FAILED,
            tier="V4-semantic",
            message="UNSAT",
            details={"unsat_core": ["spec_a_min", "spec_b_max"]},
        )
        assert all_green_report.passed is False

    def test_unsat_contract_fails_gate(self, all_green_report):
        """Contract UNSAT -> gate fails."""
        all_green_report.contract_result = VerificationResult(
            status=VerificationStatus.FAILED,
            tier="V4-semantic",
            message="1/1 contracts UNSAT",
            details={
                "per_contract": {
                    "c001": {
                        "sat_ags": "UNSAT",
                        "unsat_core": ["SPEC-001_thickness_min"],
                    }
                }
            },
        )
        assert all_green_report.passed is False

    def test_low_spec_coverage_fails_gate(self, all_green_report):
        """Spec coverage below threshold -> gate fails."""
        all_green_report.spec_coverage = 0.5
        assert all_green_report.passed is False

    def test_low_contract_coverage_fails_gate(self, all_green_report):
        """Aggregate contract coverage below threshold -> gate fails."""
        all_green_report.contract_coverages = {"c001": 0.5}
        all_green_report.aggregate_contract_coverage = 0.5
        assert all_green_report.passed is False

    def test_coverage_at_threshold_passes(self, all_green_report):
        """Coverage exactly at threshold -> passes."""
        all_green_report.spec_coverage = 0.7
        all_green_report.contract_coverages = {"c001": 0.7}
        all_green_report.aggregate_contract_coverage = 0.7
        assert all_green_report.passed is True

    def test_single_contract_low_but_aggregate_passes(self, all_green_report):
        """One contract at 0% but aggregate >= 70% -> PASS."""
        all_green_report.contract_coverages = {"c001": 0.0, "c002": 1.0}
        # aggregate: (0 + 10) / (1 + 10) ~ 0.91
        all_green_report.aggregate_contract_coverage = 0.91
        assert all_green_report.passed is True
        assert all_green_report.hard_fail is False


class TestGateReportHardSoftFail:
    """Tests for hard_fail and soft_fail properties."""

    def test_all_green_no_hard_fail(self, all_green_report):
        assert all_green_report.hard_fail is False

    def test_all_green_no_soft_fail(self, all_green_report):
        assert all_green_report.soft_fail is False

    def test_v0_failure_is_hard_fail(self, all_green_report):
        all_green_report.tier_results["V0"] = TierResult(
            tier="V0", passed=4, failed=1, warnings=0, details=[]
        )
        assert all_green_report.hard_fail is True

    def test_unsat_is_hard_fail(self, all_green_report):
        all_green_report.cross_spec_result = VerificationResult(
            status=VerificationStatus.FAILED, tier="V4-semantic", message="UNSAT"
        )
        assert all_green_report.hard_fail is True

    def test_v3_warnings_above_max_is_soft_fail(self, all_green_report):
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic", passed=3, failed=0, warnings=4, details=[]
        )
        assert all_green_report.soft_fail is True
        assert all_green_report.passed is False

    def test_v3_warnings_at_max_no_soft_fail(self, all_green_report):
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic", passed=3, failed=0, warnings=3, details=[]
        )
        assert all_green_report.soft_fail is False
        assert all_green_report.passed is True

    def test_custom_max_warnings(self, all_green_report):
        all_green_report.max_warnings = 5
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic", passed=3, failed=0, warnings=5, details=[]
        )
        assert all_green_report.soft_fail is False

    def test_failure_summary_tags_soft(self, all_green_report):
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic", passed=3, failed=0, warnings=4, details=[]
        )
        reasons = all_green_report.failure_summary()
        assert any("[SOFT]" in r for r in reasons)

    def test_attempt2_zero_new_warnings_passes(self, all_green_report):
        """Attempt > 1 with 0 new V3 warnings -> no soft fail."""
        all_green_report.attempt = 2
        all_green_report.new_v3_warnings = 0
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic", passed=3, failed=0, warnings=5, details=[]
        )
        assert all_green_report.soft_fail is False
        assert all_green_report.passed is True

    def test_attempt2_positive_new_warnings_soft_fail(self, all_green_report):
        """Attempt > 1 with new V3 warnings -> soft fail."""
        all_green_report.attempt = 2
        all_green_report.new_v3_warnings = 1
        assert all_green_report.soft_fail is True
        assert all_green_report.passed is False

    def test_attempt1_uses_total_threshold(self, all_green_report):
        """Attempt 1 (new_v3_warnings=-1) uses total > max_warnings."""
        all_green_report.attempt = 1
        all_green_report.new_v3_warnings = -1
        all_green_report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic", passed=3, failed=0, warnings=4, details=[]
        )
        assert all_green_report.soft_fail is True


class TestGateReportFailureSummary:
    """Tests for GateReport.failure_summary."""

    def test_empty_summary_when_passing(self, all_green_report):
        """No failure reasons when gate passes."""
        assert all_green_report.failure_summary() == []

    def test_summary_lists_all_issues(self):
        """Summary includes all failure reasons with [HARD]/[SOFT] tags."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(
                    tier="V0",
                    passed=4,
                    failed=1,
                    warnings=0,
                    details=[{"id": "n1", "message": "bad", "severity": "error"}],
                ),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic",
                    passed=3,
                    failed=1,
                    warnings=1,
                    details=[
                        {"id": "n2", "message": "not verifiable", "severity": "error"}
                    ],
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.FAILED,
                tier="V4-semantic",
                message="UNSAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.FAILED,
                tier="V4-semantic",
                message="Contract UNSAT",
            ),
            spec_coverage=0.5,
            contract_coverages={"c001": 0.4},
            coverage_threshold=0.7,
            aggregate_contract_coverage=0.4,
            passing_node_ids=set(),
        )
        reasons = report.failure_summary()
        # Should have entries for V0 failure, V3 failure, cross-spec, contract, coverage
        assert len(reasons) >= 4
        assert any("[HARD]" in r and "V0" in r for r in reasons)
        assert any("[HARD]" in r and ("V3" in r or "Syntactic" in r) for r in reasons)
        assert any("[HARD]" in r and "Cross-spec" in r for r in reasons)
        assert any("[HARD]" in r and "coverage" in r.lower() for r in reasons)
        # Aggregate contract coverage message (not per-contract)
        assert any("[HARD]" in r and "Aggregate contract" in r for r in reasons)


class TestGateReportRegenFeedback:
    """Tests for GateReport.to_regen_feedback."""

    def test_feedback_includes_v0_failures(self):
        """Feedback text includes V0 schema failures."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(
                    tier="V0",
                    passed=4,
                    failed=1,
                    warnings=0,
                    details=[
                        {
                            "id": "node_x",
                            "message": "Missing confidence",
                            "severity": "error",
                        }
                    ],
                ),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            passing_node_ids={"node_a"},
        )
        feedback = report.to_regen_feedback()
        assert "node_x" in feedback
        assert "Missing confidence" in feedback

    def test_feedback_includes_v3_warnings(self):
        """Feedback text includes V3 warnings."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic",
                    passed=3,
                    failed=0,
                    warnings=2,
                    details=[
                        {
                            "id": "req_1",
                            "message": "Ambiguous: 'sufficient'",
                            "severity": "warning",
                        },
                    ],
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            passing_node_ids=set(),
        )
        feedback = report.to_regen_feedback()
        assert "req_1" in feedback
        assert "Ambiguous" in feedback

    def test_feedback_includes_unsat_core(self):
        """Feedback text includes V4 UNSAT core info."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.FAILED,
                tier="V4-semantic",
                message="UNSAT",
                details={
                    "unsat_core": ["spec_a_duration_min", "spec_b_duration_max"],
                    "explanation": {
                        "summary": "duration used with incompatible ranges",
                        "fix_hint": "Rename duration parameter",
                    },
                },
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            passing_node_ids=set(),
        )
        feedback = report.to_regen_feedback()
        assert "spec_a_duration_min" in feedback
        assert "spec_b_duration_max" in feedback

    def test_feedback_includes_contract_unsat(self):
        """Feedback includes per-contract UNSAT details."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.FAILED,
                tier="V4-semantic",
                message="1/1 UNSAT",
                details={
                    "per_contract": {
                        "c001": {
                            "sat_ags": "UNSAT",
                            "unsat_core": [
                                "SPEC-001_thickness_min",
                                "CONTRACT_c001_A_0",
                            ],
                            "core_explanation": {
                                "summary": "Thickness conflict",
                                "fix_hint": "Disambiguate duration",
                            },
                        }
                    }
                },
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            passing_node_ids=set(),
        )
        feedback = report.to_regen_feedback()
        assert "c001" in feedback
        assert "UNSAT" in feedback
        assert "SPEC-001_thickness_min" in feedback

    def test_feedback_includes_frozen_nodes(self):
        """Feedback includes frozen node list."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            passing_node_ids={"goal_abc123", "requirement_def456"},
        )
        feedback = report.to_regen_feedback()
        assert "goal_abc123" in feedback
        assert "requirement_def456" in feedback
        assert "Frozen" in feedback or "DO NOT MODIFY" in feedback

    def test_feedback_includes_new_v3_warnings_soft(self):
        """Feedback includes new V3 warnings tag on attempt > 1."""
        report = GateReport(
            attempt=2,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic",
                    passed=3,
                    failed=0,
                    warnings=2,
                    details=[
                        {
                            "id": "req_1",
                            "message": "Ambiguous",
                            "severity": "warning",
                        }
                    ],
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=1.0,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            new_v3_warnings=2,
            passing_node_ids=set(),
        )
        assert report.soft_fail is True
        reasons = report.failure_summary()
        assert any("net-new warnings" in r for r in reasons)

    def test_feedback_includes_coverage_gaps(self):
        """Feedback includes coverage gap information (aggregate)."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=0.6,
            contract_coverages={"c001": 0.5},
            coverage_threshold=0.7,
            aggregate_contract_coverage=0.5,
            passing_node_ids=set(),
        )
        feedback = report.to_regen_feedback()
        assert "Coverage" in feedback
        assert "Aggregate contract coverage" in feedback

    def test_feedback_includes_node_scoped_v4_coverage_issues(self):
        """Coverage feedback includes node IDs and editable scope."""
        report = GateReport(
            attempt=1,
            tier_results={
                "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
                "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
                "V3-syntactic": TierResult(
                    tier="V3-syntactic", passed=5, failed=0, warnings=0, details=[]
                ),
            },
            cross_spec_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            contract_result=VerificationResult(
                status=VerificationStatus.PASSED,
                tier="V4-semantic",
                message="SAT",
            ),
            spec_coverage=0.6,
            contract_coverages={},
            coverage_threshold=0.7,
            aggregate_contract_coverage=1.0,
            v4_coverage_issues=[
                {
                    "node_id": "spec_a",
                    "field": "thickness",
                    "code": "SKIPPED_NO_NUMERIC",
                    "message": "Could not parse range",
                }
            ],
            affected_node_ids={"spec_a"},
            passing_node_ids={"goal_1"},
        )
        feedback = report.to_regen_feedback()
        assert "V4 Coverage Issues" in feedback
        assert "spec_a" in feedback
        assert "Editable Nodes (ONLY)" in feedback
        assert "goal_1" in feedback

    def test_targeting_error_is_hard_fail(self, all_green_report):
        """Targeting errors are treated as hard failures."""
        all_green_report.targeting_errors = ["No resolvable node IDs for low coverage"]
        assert all_green_report.hard_fail is True
        assert all_green_report.passed is False
        reasons = all_green_report.failure_summary()
        assert any("No resolvable node IDs" in r for r in reasons)
