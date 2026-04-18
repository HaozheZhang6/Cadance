"""Tests for vacuity audit — detect unconstrained Z3 vars."""

from src.verification.semantic.constraint_extractor import Constraint
from src.verification.semantic.scoped_symbol_table import ScopedKey
from src.verification.semantic.stability import BindingRegistry
from src.verification.semantic.vacuity_audit import audit_vacuity


class TestVacuityAudit:
    def test_no_warnings_multi_constraint_var(self):
        """Var in 2+ constraints -> no warning."""
        key = ScopedKey("bracket", "normal", "plate_thickness")
        c1 = Constraint(
            name="SPEC-001_thickness",
            min_name="SPEC-001_thickness_min",
            max_name="SPEC-001_thickness_max",
            min_value=0.004,
            max_value=0.006,
            scoped_key=key,
        )
        c2 = Constraint(
            name="CONTRACT_c001_A_1",
            min_name="CONTRACT_c001_A_1_min",
            max_name="CONTRACT_c001_A_1_max",
            min_value=0.009,
            max_value=0.011,
            scoped_key=key,
        )
        report = audit_vacuity([c1, c2])
        assert not report.has_warnings

    def test_single_constraint_var_flagged(self):
        """Var in only 1 constraint, no binding -> flagged."""
        key = ScopedKey("bracket", "normal", "deflection")
        c1 = Constraint(
            name="CONTRACT_c001_G_1",
            min_name="CONTRACT_c001_G_1_min",
            max_name="CONTRACT_c001_G_1_max",
            max_value=0.001,
            scoped_key=key,
        )
        report = audit_vacuity([c1])
        assert report.has_warnings
        assert len(report.unconstrained) == 1
        assert report.unconstrained[0].var_name == "bracket__normal__deflection"

    def test_single_constraint_with_binding_ok(self):
        """Var in 1 constraint but has binding -> no warning."""
        key = ScopedKey("bracket", "normal", "deflection")
        c1 = Constraint(
            name="CONTRACT_c001_G_1",
            min_name="CONTRACT_c001_G_1_min",
            max_name="CONTRACT_c001_G_1_max",
            max_value=0.001,
            scoped_key=key,
        )
        registry = BindingRegistry()
        registry.register("SPEC-002", "deflection", key, "spec")
        report = audit_vacuity([c1], registry)
        assert not report.has_warnings

    def test_no_scoped_key_ignored(self):
        """Constraint without scoped_key is ignored."""
        c1 = Constraint(
            name="SPEC_old",
            min_name="SPEC_old_min",
            max_name="SPEC_old_max",
            min_value=1.0,
            max_value=2.0,
        )
        report = audit_vacuity([c1])
        assert not report.has_warnings

    def test_summary_message(self):
        key = ScopedKey("bracket", "normal", "stress")
        c1 = Constraint(
            name="CONTRACT_c001_G_1",
            min_name="CONTRACT_c001_G_1_min",
            max_name="CONTRACT_c001_G_1_max",
            max_value=250e6,
            scoped_key=key,
        )
        report = audit_vacuity([c1])
        assert "1 unconstrained" in report.summary()
        assert "stress" in report.summary()

    def test_exogenous_feeding_derived_not_flagged(self):
        """Var in derived_sources with 1 constraint -> no warning."""
        key = ScopedKey("system", "normal", "gravity")
        c1 = Constraint(
            name="CONTRACT_c001_A_3",
            min_name="CONTRACT_c001_A_3_min",
            max_name="CONTRACT_c001_A_3_max",
            min_value=9.7,
            max_value=9.9,
            scoped_key=key,
        )
        derived_sources = {"system__normal__gravity"}
        report = audit_vacuity([c1], derived_sources=derived_sources)
        assert not report.has_warnings
