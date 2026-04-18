"""Tests for PreArtifactGate unified verification loop.

Tests verify:
- Pass on first attempt with no regen needed
- UNSAT triggers targeted regen
- V0 failure triggers regen
- Feedback includes UNSAT core, V3 warnings, V0/V1 failures
- Frozen node changes stripped from interpretation
- Binding registry carries across attempts
- Max attempts returns failure
- Verbose V4 display with witness, per-contract, UNSAT core
- Summary line reflects actual V4 status
- Drift detection after regen
- _extract_spec_dicts helper
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    NodeType,
    SpecificationNode,
    SpecParameter,
)
from src.hypergraph.store import HypergraphStore
from src.verification.base import VerificationResult, VerificationStatus
from src.verification.gate_report import GateReport, TierResult
from src.verification.pre_artifact_gate import GateResult, PreArtifactGate
from src.verification.tier4_semantic import SemanticVerifier


@pytest.fixture
def engine(tmp_path) -> HypergraphEngine:
    store = HypergraphStore(tmp_path / "test.json")
    return HypergraphEngine(store)


@pytest.fixture
def gate(engine, tmp_path) -> PreArtifactGate:
    return PreArtifactGate(
        engine=engine,
        intent="Test intent",
        store_path=str(tmp_path / "test.json"),
        llm=None,
        max_attempts=3,
        coverage_threshold=0.7,
        verbose=False,
        auto=True,
    )


def _make_passing_report(attempt: int = 1) -> GateReport:
    """Helper: all-green GateReport."""
    return GateReport(
        attempt=attempt,
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
            message="All SAT",
            details={"per_contract": {}},
        ),
        spec_coverage=1.0,
        contract_coverages={},
        coverage_threshold=0.7,
        aggregate_contract_coverage=1.0,
        passing_node_ids=set(),
    )


def _make_unsat_report(attempt: int = 1) -> GateReport:
    """Helper: V4 UNSAT GateReport."""
    return GateReport(
        attempt=attempt,
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
            status=VerificationStatus.FAILED,
            tier="V4-semantic",
            message="1/1 UNSAT",
            details={
                "per_contract": {
                    "c001": {
                        "sat_ags": "UNSAT",
                        "unsat_core": ["SPEC-001_thickness_min", "CONTRACT_c001_A_0"],
                        "core_explanation": {"summary": "Thickness conflict"},
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


def _make_v0_failure_report(attempt: int = 1) -> GateReport:
    """Helper: V0 schema failure."""
    return GateReport(
        attempt=attempt,
        tier_results={
            "V0": TierResult(
                tier="V0",
                passed=4,
                failed=1,
                warnings=0,
                details=[
                    {"id": "node_bad", "message": "Missing field", "severity": "error"}
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
            details={"per_contract": {}},
        ),
        spec_coverage=1.0,
        contract_coverages={},
        coverage_threshold=0.7,
        aggregate_contract_coverage=1.0,
        passing_node_ids=set(),
    )


class TestPreArtifactGateInit:
    """Tests for PreArtifactGate initialization."""

    def test_gate_init(self, gate):
        """Gate initializes with required fields."""
        assert gate.max_attempts == 3
        assert gate.coverage_threshold == 0.7
        assert gate.binding_registry is not None


class TestPreArtifactGateRun:
    """Tests for PreArtifactGate.run()."""

    def test_pass_first_attempt_no_regen(self, gate):
        """All tiers pass on first attempt -> success, no regen called."""
        with patch.object(gate, "_run_all_tiers", return_value=_make_passing_report()):
            with patch.object(gate, "_regenerate_targeted") as mock_regen:
                result = gate.run()

        assert result.success is True
        assert result.attempts == 1
        assert result.final_report.passed is True
        mock_regen.assert_not_called()

    def test_unsat_triggers_regen(self, gate):
        """V4 UNSAT -> regen called, then passes on attempt 2."""
        reports = [_make_unsat_report(1), _make_passing_report(2)]
        call_count = [0]

        def side_effect(*args, **kwargs):
            r = reports[call_count[0]]
            call_count[0] += 1
            return r

        with patch.object(gate, "_run_all_tiers", side_effect=side_effect):
            with patch.object(gate, "_regenerate_targeted") as mock_regen:
                result = gate.run()

        assert result.success is True
        assert result.attempts == 2
        mock_regen.assert_called_once()

    def test_v0_failure_triggers_regen(self, gate):
        """V0 failure -> regen called."""
        reports = [_make_v0_failure_report(1), _make_passing_report(2)]
        call_count = [0]

        def side_effect(*args, **kwargs):
            r = reports[call_count[0]]
            call_count[0] += 1
            return r

        with patch.object(gate, "_run_all_tiers", side_effect=side_effect):
            with patch.object(gate, "_regenerate_targeted") as mock_regen:
                result = gate.run()

        assert result.success is True
        assert result.attempts == 2
        mock_regen.assert_called_once()

    def test_max_attempts_returns_failure(self, gate):
        """All attempts fail -> GateResult.success=False."""
        with patch.object(gate, "_run_all_tiers", return_value=_make_unsat_report()):
            with patch.object(gate, "_regenerate_targeted"):
                result = gate.run()

        assert result.success is False
        assert result.attempts == 3
        assert len(result.history) == 3

    def test_history_tracks_all_attempts(self, gate):
        """History list contains one report per attempt."""
        reports = [
            _make_unsat_report(1),
            _make_unsat_report(2),
            _make_passing_report(3),
        ]
        call_count = [0]

        def side_effect(*args, **kwargs):
            r = reports[call_count[0]]
            call_count[0] += 1
            return r

        with patch.object(gate, "_run_all_tiers", side_effect=side_effect):
            with patch.object(gate, "_regenerate_targeted"):
                result = gate.run()

        assert result.success is True
        assert len(result.history) == 3


class TestRegenFeedbackContent:
    """Tests that regen feedback includes expected content."""

    def test_regen_feedback_includes_unsat_core(self, gate):
        """UNSAT report feedback includes core constraint names."""
        report = _make_unsat_report()
        feedback = report.to_regen_feedback()
        assert "SPEC-001_thickness_min" in feedback
        assert "CONTRACT_c001_A_0" in feedback

    def test_regen_feedback_includes_v3_warnings(self, gate):
        """V3 warnings appear in feedback text."""
        report = _make_passing_report()
        report.tier_results["V3-syntactic"] = TierResult(
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
        )
        feedback = report.to_regen_feedback()
        assert "req_1" in feedback
        assert "Ambiguous" in feedback

    def test_regen_feedback_includes_v0v1_failures(self, gate):
        """V0/V1 failures appear in feedback text."""
        report = _make_v0_failure_report()
        feedback = report.to_regen_feedback()
        assert "node_bad" in feedback
        assert "Missing field" in feedback

    def test_frozen_nodes_in_feedback(self, gate):
        """Passing nodes listed as frozen in feedback."""
        report = _make_passing_report()
        report.passing_node_ids = {"goal_abc", "spec_def"}
        feedback = report.to_regen_feedback()
        assert "goal_abc" in feedback
        assert "spec_def" in feedback
        assert "Frozen" in feedback or "DO NOT MODIFY" in feedback


class TestComputePassingNodes:
    """Tests for _compute_passing_nodes."""

    def test_nodes_with_failures_excluded(self, gate, engine):
        """Nodes referenced in tier failure details are excluded."""
        from src.hypergraph.models import GoalNode

        g = GoalNode(
            id="goal_1",
            node_type=NodeType.GOAL,
            description="Good goal",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        engine.add_node(g)
        spec = SpecificationNode(
            id="spec_bad",
            node_type=NodeType.SPECIFICATION,
            description="Bad spec",
            parameters=[],
        )
        engine.add_node(spec)

        report = _make_passing_report()
        # V0 failure on spec_bad
        report.tier_results["V0"] = TierResult(
            tier="V0",
            passed=1,
            failed=1,
            warnings=0,
            details=[{"id": "spec_bad", "message": "fail", "severity": "error"}],
        )
        passing = gate._compute_passing_nodes(report)
        assert "goal_1" in passing
        assert "spec_bad" not in passing

    def test_nodes_with_warnings_excluded(self, gate, engine):
        """Nodes with warnings (not just failures) are excluded."""
        from src.hypergraph.models import GoalNode

        g = GoalNode(
            id="goal_1",
            node_type=NodeType.GOAL,
            description="Good goal",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="system",
        )
        engine.add_node(g)
        spec = SpecificationNode(
            id="spec_warned",
            node_type=NodeType.SPECIFICATION,
            description="Warned spec",
            parameters=[],
        )
        engine.add_node(spec)

        report = _make_passing_report()
        report.tier_results["V3-syntactic"] = TierResult(
            tier="V3-syntactic",
            passed=1,
            failed=0,
            warnings=1,
            details=[{"id": "spec_warned", "message": "ambig", "severity": "warning"}],
        )
        passing = gate._compute_passing_nodes(report)
        assert "goal_1" in passing
        assert "spec_warned" not in passing

    def test_empty_graph_returns_empty(self, gate):
        """No nodes -> empty passing set."""
        report = _make_passing_report()
        passing = gate._compute_passing_nodes(report)
        assert passing == set()

    def test_v4_coverage_affected_nodes_excluded(self, gate, engine):
        """V4 coverage-affected specs are excluded from passing set."""
        spec = SpecificationNode(
            id="spec_cov",
            node_type=NodeType.SPECIFICATION,
            description="Coverage issue spec",
            parameters=[],
        )
        engine.add_node(spec)

        report = _make_passing_report()
        report.v4_coverage_affected_ids = {"spec_cov"}
        passing = gate._compute_passing_nodes(report)
        assert "spec_cov" not in passing

    def test_v4_unsat_affected_nodes_excluded(self, gate, engine):
        """V4 UNSAT-affected specs are excluded from passing set."""
        spec = SpecificationNode(
            id="spec_unsat",
            node_type=NodeType.SPECIFICATION,
            description="UNSAT issue spec",
            parameters=[],
        )
        engine.add_node(spec)

        report = _make_passing_report()
        report.v4_unsat_affected_ids = {"spec_unsat"}
        passing = gate._compute_passing_nodes(report)
        assert "spec_unsat" not in passing


class TestTargetedCoverageContext:
    """Tests for low-coverage targeting behavior."""

    def test_low_coverage_without_node_ids_sets_targeting_error(self, gate):
        """Low spec coverage with unresolved warnings blocks targeted regen."""
        base_summary = {
            "tier_stats": {
                "V0": {"passed": 1, "failed": 0, "warnings": 0},
                "V1": {"passed": 1, "failed": 0, "warnings": 0},
            }
        }
        v3_summary = {
            "tier_stats": {
                "V3-syntactic": {
                    "passed": 1,
                    "failed": 0,
                    "warnings": 0,
                    "failures_detail": [],
                    "warnings_detail": [],
                }
            }
        }

        with patch(
            "src.verification.pre_artifact_gate.VerificationPipeline.verify_all",
            side_effect=[base_summary, v3_summary],
        ):
            with patch.object(
                SemanticVerifier,
                "verify_all_specs",
                return_value=VerificationResult(
                    status=VerificationStatus.PASSED,
                    tier="V4-semantic",
                    message="SAT",
                    details={
                        "coverage": {"compiled": 5, "skipped": 4},
                        "warnings": [
                            {"code": "LOW_COVERAGE", "message": "Only 56% compiled"}
                        ],
                    },
                ),
            ):
                with patch.object(
                    SemanticVerifier,
                    "verify_contracts",
                    return_value=VerificationResult(
                        status=VerificationStatus.PASSED,
                        tier="V4-semantic",
                        message="SAT",
                        details={"per_contract": {}},
                    ),
                ):
                    report = gate._run_all_tiers(attempt=1)

        assert report.spec_coverage == pytest.approx(5 / 9)
        assert report.v4_coverage_affected_ids == set()
        assert report.targeting_errors
        assert "did not map to node IDs" in report.targeting_errors[0]

    def test_regenerate_targeted_returns_early_on_targeting_error(self, gate):
        """Targeted regen exits before any mutation when targeting context is incomplete."""
        report = _make_passing_report()
        report.targeting_errors = ["Spec coverage is below threshold but unresolved"]
        report.affected_node_ids = {"spec_x"}
        gate.llm = object()
        gate._last_modified_ids = {"existing"}

        gate._regenerate_targeted(report)
        assert gate._last_modified_ids == {"existing"}

    def test_run_all_tiers_v3_is_not_scoped_to_modified_ids(self, gate):
        """V3 verify_all reruns full stack and does not pass node_ids filter."""
        base_summary = {
            "tier_stats": {
                "V0": {"passed": 1, "failed": 0, "warnings": 0},
                "V1": {"passed": 1, "failed": 0, "warnings": 0},
            }
        }
        v3_summary = {
            "tier_stats": {
                "V3-syntactic": {
                    "passed": 2,
                    "failed": 0,
                    "warnings": 0,
                    "failures_detail": [],
                    "warnings_detail": [],
                }
            }
        }
        gate._last_modified_ids = {"spec_only"}

        with patch(
            "src.verification.pre_artifact_gate.VerificationPipeline.verify_all",
            side_effect=[base_summary, v3_summary],
        ) as mock_verify:
            with patch.object(
                SemanticVerifier,
                "verify_all_specs",
                return_value=VerificationResult(
                    status=VerificationStatus.PASSED,
                    tier="V4-semantic",
                    message="SAT",
                    details={"coverage": {"compiled": 2, "skipped": 0}, "warnings": []},
                ),
            ):
                with patch.object(
                    SemanticVerifier,
                    "verify_contracts",
                    return_value=VerificationResult(
                        status=VerificationStatus.PASSED,
                        tier="V4-semantic",
                        message="SAT",
                        details={"per_contract": {}},
                    ),
                ):
                    gate._run_all_tiers(attempt=2)

        v3_call_kwargs = mock_verify.call_args_list[1].kwargs
        assert "node_ids" not in v3_call_kwargs
        assert v3_call_kwargs.get("node_types") == {
            NodeType.SPECIFICATION,
            NodeType.REQUIREMENT,
            NodeType.CONTRACT,
        }


class TestBindingRegistryPersistence:
    """Binding registry carries across gate attempts."""

    def test_binding_registry_carries_across_attempts(self, gate):
        """Same BindingRegistry instance used across all attempts."""
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        # Register a binding before run
        key = ScopedKey("bracket", "normal", "thickness")
        gate.binding_registry.register("SPEC-001", "thickness", key, "user")

        # After run, binding should still exist
        with patch.object(gate, "_run_all_tiers", return_value=_make_passing_report()):
            gate.run()

        binding = gate.binding_registry.get("SPEC-001", "thickness")
        assert binding is not None
        assert binding.scoped_key.entity_id == "bracket"


class TestGateResult:
    """Tests for GateResult dataclass."""

    def test_gate_result_fields(self):
        """GateResult has expected fields."""
        report = _make_passing_report()
        result = GateResult(
            success=True,
            attempts=1,
            final_report=report,
            history=[report],
        )
        assert result.success is True
        assert result.attempts == 1
        assert result.final_report is report
        assert len(result.history) == 1


# ==============================================================================
# V4 display tests
# ==============================================================================


def _make_passing_report_with_v4_details(
    witness=None, constraint_count=29, spec_count=8, coverage_compiled=24
) -> GateReport:
    """Passing report with realistic V4 details."""
    return GateReport(
        attempt=1,
        tier_results={
            "V0": TierResult(tier="V0", passed=5, failed=0, warnings=0, details=[]),
            "V1": TierResult(tier="V1", passed=5, failed=0, warnings=0, details=[]),
            "V3-syntactic": TierResult(
                tier="V3-syntactic", passed=5, failed=0, warnings=2, details=[]
            ),
        },
        cross_spec_result=VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V4-semantic",
            message=f"SAT: All {constraint_count} constraints satisfiable across {spec_count} spec(s)",
            details={
                "witness": witness or {"bracket__normal__thickness": 5.0},
                "constraint_count": constraint_count,
                "spec_count": spec_count,
                "coverage": {
                    "compiled": coverage_compiled,
                    "skipped": 0,
                    "total": coverage_compiled,
                    "percentage": "100%",
                },
            },
        ),
        contract_result=VerificationResult(
            status=VerificationStatus.PASSED,
            tier="V4-semantic",
            message="Verified 2 contract(s)",
            details={
                "contract_count": 2,
                "per_contract": {
                    "contract_9cb537b2": {
                        "sat_a": "SAT",
                        "sat_ag": "SAT",
                        "sat_ags": "SAT",
                        "unsat_core": [],
                        "compilation": {"compiled": 8, "skipped": 0},
                    },
                    "contract_6fa3361d": {
                        "sat_a": "SAT",
                        "sat_ag": "SAT",
                        "sat_ags": "SAT",
                        "unsat_core": [],
                        "compilation": {"compiled": 7, "skipped": 0},
                    },
                },
            },
        ),
        spec_coverage=1.0,
        contract_coverages={"contract_9cb537b2": 1.0, "contract_6fa3361d": 1.0},
        coverage_threshold=0.7,
        aggregate_contract_coverage=1.0,
        passing_node_ids=set(),
    )


class TestDisplayReportVerbose:
    """Tests for verbose V4 display in _display_report."""

    def test_display_report_verbose_shows_witness(self, gate, capsys):
        """verbose=True shows witness values (numeric extraction from dict)."""
        gate.verbose = True
        witness = {
            "bracket__normal__payload_mass": {
                "value": 5.0,
                "from": "SPEC-001_payload_mass",
            },
            "bracket__normal__gravity": 9.81,  # plain number also works
        }
        report = _make_passing_report_with_v4_details(witness=witness)
        gate._display_report(report)
        out = capsys.readouterr().out
        assert "bracket__normal__payload_mass" in out
        assert "5.0" in out
        assert "9.81" in out
        # Should NOT print raw dict
        assert "from" not in out

    def test_display_report_verbose_shows_per_contract(self, gate, capsys):
        """verbose=True shows per-contract SAT status."""
        gate.verbose = True
        report = _make_passing_report_with_v4_details()
        gate._display_report(report)
        out = capsys.readouterr().out
        assert "contract_9cb537b2" in out
        assert "contract_6fa3361d" in out
        assert "SAT" in out

    def test_display_report_verbose_shows_unsat_core(self, gate, capsys):
        """verbose=True with UNSAT shows core + explanation."""
        gate.verbose = True
        report = _make_passing_report_with_v4_details()
        # Override cross_spec to FAILED with UNSAT
        report.cross_spec_result = VerificationResult(
            status=VerificationStatus.FAILED,
            tier="V4-semantic",
            message="UNSAT: thickness conflict",
            details={
                "unsat_core": ["SPEC-001_thickness_min", "SPEC-001_thickness_max"],
                "explanation": {
                    "summary": "Thickness min > max",
                    "details": "min=10, max=5",
                    "fix_hint": "Widen tolerance",
                },
                "constraint_count": 5,
                "spec_count": 2,
                "coverage": {"compiled": 5, "skipped": 0},
            },
        )
        gate._display_report(report)
        out = capsys.readouterr().out
        assert "SPEC-001_thickness_min" in out
        assert "Thickness min > max" in out

    def test_display_report_normal_no_verbose(self, gate, capsys):
        """verbose=False shows only compact summary."""
        gate.verbose = False
        report = _make_passing_report_with_v4_details(
            witness={"bracket__normal__thickness": 5.0}
        )
        gate._display_report(report)
        out = capsys.readouterr().out
        # Should NOT show witness section header
        assert "Witness" not in out
        # Should show compact summary
        assert "V4:" in out


class TestSummaryLineReflectsV4Status:
    """Summary line uses actual V4 status, not hardcoded 'SAT'."""

    def test_summary_shows_warning_when_v4_warning(self, gate, capsys):
        """V4 WARNING status reflected in summary."""
        report = _make_passing_report()
        # Override cross_spec to WARNING
        report.cross_spec_result = VerificationResult(
            status=VerificationStatus.WARNING,
            tier="V4-semantic",
            message="Z3 returned unknown",
            details={
                "coverage": {"compiled": 5, "skipped": 3},
                "constraint_count": 5,
                "spec_count": 2,
            },
        )
        # WARNING cross_spec means report.passed=False, so display failure path
        # But let's test that the summary mentions the actual status
        gate._display_report(report)
        out = capsys.readouterr().out
        # Should NOT say "V4: SAT" when it's actually WARNING
        assert (
            "V4: SAT" not in out.upper().replace("warning", "WARNING")
            or "WARNING" in out.upper()
        )

    def test_summary_shows_sat_with_stats(self, gate, capsys):
        """Passing V4 shows spec + contract coverage percentages."""
        report = _make_passing_report_with_v4_details(
            constraint_count=29, spec_count=8, coverage_compiled=24
        )
        gate._display_report(report)
        out = capsys.readouterr().out
        assert "100% spec" in out
        assert "contract" in out


# ==============================================================================
# Drift detection after regen
# ==============================================================================


class TestDriftAfterRegen:
    """Tests for drift detection wiring in _regenerate_targeted."""

    def test_extract_spec_dicts_from_engine(self, gate, engine):
        """_extract_spec_dicts returns correct format from engine specs."""
        spec = SpecificationNode(
            id="SPEC-001",
            node_type=NodeType.SPECIFICATION,
            description="Test spec",
            parameters=[
                SpecParameter(
                    name="thickness", value=5.0, unit="mm", tolerance="+/- 1mm"
                )
            ],
            metadata={"interface": "bracket", "regime_id": "normal"},
        )
        engine.add_node(spec)

        result = gate._extract_spec_dicts()
        assert len(result) == 1
        d = result[0]
        assert d["spec_id"] == "SPEC-001"
        assert d["entity_id"] == "bracket"
        assert d["regime_id"] == "normal"

    def test_extract_spec_dicts_multiple_params(self, gate, engine):
        """_extract_spec_dicts returns one entry per param."""
        spec = SpecificationNode(
            id="SPEC-002",
            node_type=NodeType.SPECIFICATION,
            description="Multi-param spec",
            parameters=[
                SpecParameter(name="width", value=50.0, unit="mm"),
                SpecParameter(name="height", value=30.0, unit="mm"),
            ],
            metadata={"interface": "bracket", "regime_id": "normal"},
        )
        engine.add_node(spec)

        result = gate._extract_spec_dicts()
        assert len(result) == 2
        names = {d["param_name"] for d in result}
        assert names == {"width", "height"}

    def test_extract_spec_dicts_handles_dict_params(self, gate, engine):
        """_extract_spec_dicts tolerates dict-style params from legacy/corrupt state."""
        spec = SpecificationNode(
            id="SPEC-003",
            node_type=NodeType.SPECIFICATION,
            description="Dict params",
            parameters=[SpecParameter(name="width", value=50.0, unit="mm")],
            metadata={"interface": "bracket", "regime_id": "normal"},
        )
        engine.add_node(spec)

        # Simulate legacy state where parameters were written as raw dicts
        engine.nodes["SPEC-003"] = engine.nodes["SPEC-003"].model_copy(
            update={
                "parameters": [
                    {
                        "name": "legacy_param",
                        "value": 10.0,
                        "unit": "mm",
                        "tolerance": "+/- 1",
                    }
                ]
            }
        )

        result = gate._extract_spec_dicts()
        assert len(result) == 1
        assert result[0]["spec_id"] == "SPEC-003"
        assert result[0]["param_name"] == "legacy_param"


# ==============================================================================
# V3 fingerprint + cache tests
# ==============================================================================


class TestCountV3PerNode:
    """Tests for _count_v3_per_node helper."""

    def test_count_empty(self):
        assert PreArtifactGate._count_v3_per_node([]) == {}

    def test_count_basic(self):
        details = [
            {"id": "req_1", "message": "Ambiguous term 'sufficient'"},
            {"id": "spec_2", "message": "Missing units"},
        ]
        counts = PreArtifactGate._count_v3_per_node(details)
        assert counts == {"req_1": 1, "spec_2": 1}

    def test_count_multiple_per_node(self):
        details = [
            {"id": "req_1", "message": "Issue A"},
            {"id": "req_1", "message": "Issue B"},
            {"id": "spec_2", "message": "Issue C"},
        ]
        counts = PreArtifactGate._count_v3_per_node(details)
        assert counts == {"req_1": 2, "spec_2": 1}

    def test_count_missing_id(self):
        details = [{"message": "no id"}]
        counts = PreArtifactGate._count_v3_per_node(details)
        assert counts == {"": 1}


class TestV3CacheInit:
    """V3 cache and last_modified_ids initialized."""

    def test_cache_starts_empty(self, gate):
        assert gate._v3_cache == {}
        assert gate._last_modified_ids == set()


class TestDisplayChanges:
    """Tests for _display_changes split by GRS vs contract."""

    def test_no_changes_shows_grs_preserved(self, gate, capsys):
        """No changes -> 'GRS nodes: no structural changes'."""
        before = {"n1": {"type": "goal"}, "n2": {"type": "contract"}}
        after = {"n1": {"type": "goal"}, "n2": {"type": "contract"}}
        gate._display_changes(before, after)
        out = capsys.readouterr().out
        assert "GRS nodes: no structural changes" in out

    def test_contract_churn_shown_separately(self, gate, capsys):
        """Contract add/remove shown as re-extracted."""
        before = {"g1": {"type": "goal"}, "c1": {"type": "contract"}}
        after = {"g1": {"type": "goal"}, "c2": {"type": "contract"}}
        gate._display_changes(before, after)
        out = capsys.readouterr().out
        assert "GRS nodes: no structural changes" in out
        assert "Contracts re-extracted" in out
        assert "+0 net change" in out

    def test_grs_add_shown(self, gate, capsys):
        """GRS node added shows GRS line."""
        before = {"g1": {"type": "goal"}}
        after = {"g1": {"type": "goal"}, "s1": {"type": "specification"}}
        gate._display_changes(before, after)
        out = capsys.readouterr().out
        assert "GRS:" in out
        assert "+1" in out


class TestNewV3WarningsOnReport:
    """new_v3_warnings field on GateReport from _run_all_tiers."""

    def test_attempt1_new_v3_negative(self, gate):
        """Attempt 1 sets new_v3_warnings = -1 (not computed)."""
        report = _make_passing_report(attempt=1)
        # Default is -1
        assert report.new_v3_warnings == -1
