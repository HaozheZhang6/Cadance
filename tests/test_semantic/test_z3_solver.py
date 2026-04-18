"""Tests for z3_solver — derived constraint multiplication."""

from src.verification.semantic.constraint_extractor import Constraint
from src.verification.semantic.scoped_ontology.models import Ontology, OntologyQuantity
from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable
from src.verification.semantic.z3_solver import solve_constraints_scoped


def _make_ontology(*qty_ids: str) -> Ontology:
    """Build minimal ontology with given quantity IDs."""
    quantities = {}
    for qid in qty_ids:
        quantities[qid] = OntologyQuantity(
            dimensionality="",
            canonical_unit="",
            aliases=[],
            domain_class="",
        )
    return Ontology(
        version="test",
        quantities=quantities,
        regimes=[],
        entity_kinds=[],
    )


class TestDerivedConstraints:
    """Derived (multiplication) constraints must emit Z3 assertions."""

    def test_derived_multiplication_sat(self):
        """F = m * g with compatible bounds -> SAT."""
        ontology = _make_ontology("applied_force", "payload_mass", "gravity")
        table = ScopedSymbolTable(ontology=ontology)

        # F = m * g (derived)
        key_f, _ = table.resolve("system", "normal", "applied_force")
        c_derived = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            scoped_key=key_f,
            term_class="structured",
            source_spec_id="c1",
        )
        c_derived.derived = True
        c_derived.factors = ["payload_mass", "gravity"]

        # m in [4.5, 5.5]
        key_m, _ = table.resolve("system", "normal", "payload_mass")
        c_mass = Constraint(
            name="CONTRACT_c1_A_2",
            min_name="CONTRACT_c1_A_2_min",
            max_name="CONTRACT_c1_A_2_max",
            min_value=4.5,
            max_value=5.5,
            scoped_key=key_m,
            term_class="structured",
            source_spec_id="c1",
        )

        # g in [9.7, 9.9]
        key_g, _ = table.resolve("system", "normal", "gravity")
        c_grav = Constraint(
            name="CONTRACT_c1_A_3",
            min_name="CONTRACT_c1_A_3_min",
            max_name="CONTRACT_c1_A_3_max",
            min_value=9.7,
            max_value=9.9,
            scoped_key=key_g,
            term_class="structured",
            source_spec_id="c1",
        )

        # F in [40, 60] (compatible with 4.5*9.7=43.65 .. 5.5*9.9=54.45)
        c_force = Constraint(
            name="SPEC_force",
            min_name="SPEC_force_min",
            max_name="SPEC_force_max",
            min_value=40.0,
            max_value=60.0,
            scoped_key=key_f,
            term_class="structured",
            source_spec_id="SPEC-001",
        )

        result = solve_constraints_scoped([c_derived, c_mass, c_grav, c_force], table)
        assert result.status == "SAT"

    def test_derived_multiplication_unsat(self):
        """F = m * g with incompatible force bounds -> UNSAT."""
        ontology = _make_ontology("applied_force", "payload_mass", "gravity")
        table = ScopedSymbolTable(ontology=ontology)

        key_f, _ = table.resolve("system", "normal", "applied_force")
        c_derived = Constraint(
            name="CONTRACT_c1_A_1",
            min_name="CONTRACT_c1_A_1_min",
            max_name="CONTRACT_c1_A_1_max",
            scoped_key=key_f,
            term_class="structured",
            source_spec_id="c1",
        )
        c_derived.derived = True
        c_derived.factors = ["payload_mass", "gravity"]

        # m = 5
        key_m, _ = table.resolve("system", "normal", "payload_mass")
        c_mass = Constraint(
            name="CONTRACT_c1_A_2",
            min_name="CONTRACT_c1_A_2_min",
            max_name="CONTRACT_c1_A_2_max",
            min_value=5.0,
            max_value=5.0,
            scoped_key=key_m,
            term_class="structured",
            source_spec_id="c1",
        )

        # g = 9.81
        key_g, _ = table.resolve("system", "normal", "gravity")
        c_grav = Constraint(
            name="CONTRACT_c1_A_3",
            min_name="CONTRACT_c1_A_3_min",
            max_name="CONTRACT_c1_A_3_max",
            min_value=9.81,
            max_value=9.81,
            scoped_key=key_g,
            term_class="structured",
            source_spec_id="c1",
        )

        # F in [100, 200] (incompatible with 5*9.81=49.05)
        c_force = Constraint(
            name="SPEC_force",
            min_name="SPEC_force_min",
            max_name="SPEC_force_max",
            min_value=100.0,
            max_value=200.0,
            scoped_key=key_f,
            term_class="structured",
            source_spec_id="SPEC-001",
        )

        result = solve_constraints_scoped([c_derived, c_mass, c_grav, c_force], table)
        assert result.status == "UNSAT"

    def test_derived_no_factors_ignored(self):
        """Non-derived constraint unchanged (no multiplication assertion)."""
        ontology = _make_ontology("plate_thickness")
        table = ScopedSymbolTable(ontology=ontology)

        key, _ = table.resolve("system", "normal", "plate_thickness")
        c = Constraint(
            name="SPEC_thickness",
            min_name="SPEC_thickness_min",
            max_name="SPEC_thickness_max",
            min_value=0.004,
            max_value=0.006,
            scoped_key=key,
            term_class="structured",
            source_spec_id="SPEC-001",
        )
        # No derived attribute at all
        result = solve_constraints_scoped([c], table)
        assert result.status == "SAT"
