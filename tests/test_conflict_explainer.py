"""Tests for UNSAT conflict explanation."""

from src.verification.semantic.conflict_explainer import (
    explain_conflict,
)


class TestExplainConflict:
    """Test conflict explanation generation."""

    def test_empty_core_no_conflict(self):
        result = explain_conflict([], {})
        assert result.summary == "No conflicts detected"
        assert result.conflicting_constraints == []

    def test_single_spec_conflict(self):
        unsat_core = ["SPEC-001_width_min", "SPEC-001_width_max"]
        constraints_by_name = {
            "SPEC-001_width_min": {"min_value": 10.0, "max_value": 5.0},
            "SPEC-001_width_max": {"min_value": 10.0, "max_value": 5.0},
        }
        result = explain_conflict(unsat_core, constraints_by_name)

        assert "UNSAT" in result.summary
        assert "2 conflicting" in result.summary
        assert "1 specification" in result.summary
        assert "SPEC-001_width_min" in result.conflicting_constraints
        assert len(result.details) == 2
        assert "SPEC-001" in result.fix_hint

    def test_multi_spec_conflict(self):
        unsat_core = ["SPEC-001_x_min", "SPEC-002_y_max"]
        constraints_by_name = {
            "SPEC-001_x_min": {"min_value": 5.0, "max_value": 10.0},
            "SPEC-002_y_max": {"min_value": 3.0, "max_value": 8.0},
        }
        result = explain_conflict(unsat_core, constraints_by_name)

        assert "2 specification" in result.summary
        assert "SPEC-001" in result.fix_hint
        assert "SPEC-002" in result.fix_hint

    def test_explanation_with_exact_value(self):
        unsat_core = ["SPEC-001_exact"]
        constraints_by_name = {
            "SPEC-001_exact": {"exact_value": 5.0},
        }
        result = explain_conflict(unsat_core, constraints_by_name)
        assert "== 5" in result.details[0]

    def test_unknown_constraint_handled(self):
        unsat_core = ["UNKNOWN_constraint"]
        result = explain_conflict(unsat_core, {})
        assert "UNKNOWN_constraint" in result.conflicting_constraints
        assert "violated" in result.details[0]
