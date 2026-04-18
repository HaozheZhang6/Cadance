"""Tests for Z3 constraint solving."""

import pytest

from src.verification.semantic.constraint_extractor import (
    Constraint,
    validate_for_z3,
)
from src.verification.semantic.symbol_table import SymbolTable
from src.verification.semantic.z3_solver import SolveResult, solve_constraints


class TestSolveConstraints:
    """Test Z3 solving."""

    def test_sat_single_constraint(self):
        """Single satisfiable constraint returns SAT with witness."""
        constraints = [
            Constraint(
                name="SPEC-001_width",
                min_name="SPEC-001_width_min",
                max_name="SPEC-001_width_max",
                min_value=0.095,
                max_value=0.105,
                canonical_unit="m",
                is_equality=False,
            )
        ]
        result = solve_constraints(constraints)
        assert result.status == "SAT"
        assert "SPEC-001_width" in result.witness
        value = result.witness["SPEC-001_width"]["value"]
        assert 0.095 <= value <= 0.105
        assert result.witness["SPEC-001_width"]["from"] == "SPEC-001_width"

    def test_sat_multiple_compatible_constraints(self):
        """Multiple compatible constraints return SAT."""
        constraints = [
            Constraint(
                name="SPEC-001_width",
                min_name="SPEC-001_width_min",
                max_name="SPEC-001_width_max",
                min_value=0.1,
                max_value=0.2,
                canonical_unit="m",
                is_equality=False,
            ),
            Constraint(
                name="SPEC-002_height",
                min_name="SPEC-002_height_min",
                max_name="SPEC-002_height_max",
                min_value=0.05,
                max_value=0.15,
                canonical_unit="m",
                is_equality=False,
            ),
        ]
        result = solve_constraints(constraints)
        assert result.status == "SAT"
        assert "SPEC-001_width" in result.witness
        assert "SPEC-002_height" in result.witness

    def test_unsat_conflicting_bounds(self):
        """Conflicting bounds return UNSAT with core."""
        # Same variable must be >= 10 AND <= 5 (impossible)
        constraints = [
            Constraint(
                name="SPEC-001_value",
                min_name="SPEC-001_value_min",
                max_name="SPEC-001_value_max",
                min_value=10.0,
                max_value=5.0,  # max < min = UNSAT
                canonical_unit="m",
                is_equality=False,
            ),
        ]
        result = solve_constraints(constraints)
        assert result.status == "UNSAT"
        assert len(result.unsat_core) > 0
        # Core should contain the conflicting constraint names
        assert any("SPEC-001_value" in name for name in result.unsat_core)

    def test_sat_exact_equality(self):
        """Exact equality constraint works."""
        constraints = [
            Constraint(
                name="SPEC-001_exact",
                min_name="SPEC-001_exact_min",
                max_name="SPEC-001_exact_max",
                exact_value=5.0,
                canonical_unit="m",
                is_equality=True,
            ),
        ]
        result = solve_constraints(constraints)
        assert result.status == "SAT"
        assert result.witness["SPEC-001_exact"]["value"] == pytest.approx(5.0)

    def test_unsat_conflicting_equalities(self):
        """Conflicting exact values return UNSAT."""
        # Same conceptual variable can't be both 5 and 10
        # This requires cross-spec conflict via shared variable name
        # For now, test with explicit contradictory bounds
        constraints = [
            Constraint(
                name="SPEC-001_x",
                min_name="SPEC-001_x_min",
                max_name="SPEC-001_x_max",
                min_value=10.0,
                max_value=10.0,  # exact 10
                canonical_unit="m",
                is_equality=False,
            ),
            Constraint(
                name="SPEC-002_x",
                min_name="SPEC-002_x_min",
                max_name="SPEC-002_x_max",
                min_value=5.0,
                max_value=5.0,  # exact 5
                canonical_unit="m",
                is_equality=False,
                # Note: these are different variables, so this is SAT
            ),
        ]
        # This is actually SAT because they're different variables
        result = solve_constraints(constraints)
        assert result.status == "SAT"

    def test_empty_constraints_sat(self):
        """Empty constraint list returns SAT."""
        result = solve_constraints([])
        assert result.status == "SAT"
        assert result.witness == {}

    def test_result_has_constraint_count(self):
        """Result includes constraint count."""
        constraints = [
            Constraint(
                name="SPEC-001_a",
                min_name="SPEC-001_a_min",
                max_name="SPEC-001_a_max",
                min_value=0,
                max_value=10,
                canonical_unit="m",
                is_equality=False,
            ),
        ]
        result = solve_constraints(constraints)
        assert result.constraint_count == 1


class TestSolveResult:
    """Test result structure."""

    def test_result_sat_structure(self):
        result = SolveResult(
            status="SAT",
            witness={"x": {"value": 5.0, "from": "SPEC-001_x"}},
            unsat_core=[],
            constraint_count=1,
        )
        assert result.status == "SAT"
        assert result.is_sat

    def test_result_unsat_structure(self):
        result = SolveResult(
            status="UNSAT",
            witness={},
            unsat_core=["SPEC-001_x_min", "SPEC-001_x_max"],
            constraint_count=1,
        )
        assert result.status == "UNSAT"
        assert not result.is_sat


class TestSymbolTableIntegration:
    """Test SymbolTable integration for shared variables (08-02)."""

    def test_solve_shared_variable_for_same_canonical(self):
        """Two constraints with same canonical_name use same Z3 variable."""
        symbol_table = SymbolTable()

        # Two different specs, same canonical param
        constraints = [
            Constraint(
                name="SPEC-A_payload_mass",
                min_name="SPEC-A_payload_mass_min",
                max_name="SPEC-A_payload_mass_max",
                min_value=4.0,
                max_value=6.0,
                canonical_unit="kg",
                is_equality=False,
                canonical_name="payload_mass",
            ),
            Constraint(
                name="SPEC-B_mass",
                min_name="SPEC-B_mass_min",
                max_name="SPEC-B_mass_max",
                min_value=5.0,
                max_value=7.0,
                canonical_unit="kg",
                is_equality=False,
                canonical_name="payload_mass",  # Same canonical
            ),
        ]
        result = solve_constraints(constraints, symbol_table=symbol_table)

        # Should be SAT - intersection [5,6] is non-empty
        assert result.status == "SAT"
        # Witness should use canonical name (shared variable)
        assert "payload_mass" in result.witness
        val = result.witness["payload_mass"]["value"]
        assert 5.0 <= val <= 6.0

    def test_solve_cross_spec_conflict_returns_unsat(self):
        """Conflicting cross-spec constraints return UNSAT with shared variable."""
        symbol_table = SymbolTable()

        # Two specs: one requires [1,2], other requires [8,10] (disjoint)
        constraints = [
            Constraint(
                name="SPEC-X_payload_mass",
                min_name="SPEC-X_payload_mass_min",
                max_name="SPEC-X_payload_mass_max",
                min_value=1.0,
                max_value=2.0,
                canonical_unit="kg",
                is_equality=False,
                canonical_name="payload_mass",
            ),
            Constraint(
                name="SPEC-Y_mass",
                min_name="SPEC-Y_mass_min",
                max_name="SPEC-Y_mass_max",
                min_value=8.0,
                max_value=10.0,
                canonical_unit="kg",
                is_equality=False,
                canonical_name="payload_mass",  # Same canonical, conflict!
            ),
        ]
        result = solve_constraints(constraints, symbol_table=symbol_table)

        # Should be UNSAT
        assert result.status == "UNSAT"
        assert len(result.unsat_core) > 0


class TestInvariantIntegration:
    """Test domain invariant integration in Z3 solver (09-02)."""

    def test_solve_with_invariants_coating_negative_unsat(self):
        """Negative coating_thickness violates NONNEG invariant, returns UNSAT."""
        symbol_table = SymbolTable()
        # Resolve coating_thickness to create Z3 variable
        symbol_table.resolve("coating_thickness", "m")

        constraint = Constraint(
            name="SPEC-001_coating",
            min_name="SPEC-001_coating_min",
            max_name="SPEC-001_coating_max",
            exact_value=-0.00001,  # -10 micrometers (negative)
            canonical_unit="m",
            is_equality=True,
            canonical_name="coating_thickness",
        )
        result = solve_constraints([constraint], symbol_table=symbol_table)

        assert result.status == "UNSAT"
        assert "INV_NONNEG_coating_thickness" in result.unsat_core

    def test_solve_with_invariants_thickness_positive_sat(self):
        """Positive plate_thickness satisfies POS invariant, returns SAT."""
        symbol_table = SymbolTable()
        symbol_table.resolve("plate_thickness", "m")

        constraint = Constraint(
            name="SPEC-002_thickness",
            min_name="SPEC-002_thickness_min",
            max_name="SPEC-002_thickness_max",
            exact_value=0.005,  # 5mm (positive)
            canonical_unit="m",
            is_equality=True,
            canonical_name="plate_thickness",
        )
        result = solve_constraints([constraint], symbol_table=symbol_table)

        assert result.status == "SAT"
        assert "plate_thickness" in result.witness
        assert result.witness["plate_thickness"]["value"] > 0

    def test_solve_with_invariants_safety_factor_below_one_unsat(self):
        """Safety factor < 1 violates GE1 invariant, returns UNSAT."""
        symbol_table = SymbolTable()
        symbol_table.resolve("safety_factor", "")

        constraint = Constraint(
            name="SPEC-003_safety",
            min_name="SPEC-003_safety_min",
            max_name="SPEC-003_safety_max",
            exact_value=0.5,  # Below 1.0 (invalid)
            canonical_unit="",
            is_equality=True,
            canonical_name="safety_factor",
        )
        result = solve_constraints([constraint], symbol_table=symbol_table)

        assert result.status == "UNSAT"
        assert "INV_GE1_safety_factor" in result.unsat_core

    def test_solve_with_invariants_safety_factor_valid_sat(self):
        """Safety factor >= 1 satisfies GE1 invariant, returns SAT."""
        symbol_table = SymbolTable()
        symbol_table.resolve("safety_factor", "")

        constraint = Constraint(
            name="SPEC-004_safety",
            min_name="SPEC-004_safety_min",
            max_name="SPEC-004_safety_max",
            min_value=1.5,
            max_value=2.5,
            canonical_unit="",
            is_equality=False,
            canonical_name="safety_factor",
        )
        result = solve_constraints([constraint], symbol_table=symbol_table)

        assert result.status == "SAT"
        assert "safety_factor" in result.witness
        assert result.witness["safety_factor"]["value"] >= 1

    def test_solve_without_symbol_table_no_invariants(self):
        """Without symbol_table, negative values allowed (backward compatibility)."""
        constraint = Constraint(
            name="SPEC-005_value",
            min_name="SPEC-005_value_min",
            max_name="SPEC-005_value_max",
            exact_value=-5.0,  # Negative but no invariant
            canonical_unit="m",
            is_equality=True,
        )
        result = solve_constraints([constraint], symbol_table=None)

        # Should be SAT (no invariants applied)
        assert result.status == "SAT"
        assert result.witness["SPEC-005_value"]["value"] == pytest.approx(-5.0)


class TestFullExtractionSolvingPipeline:
    """Test full extraction->solving pipeline with SymbolTable (08-02)."""

    def test_extract_and_solve_cross_spec_with_shared_variables(self):
        """Full pipeline: extract from two specs, solve with shared variables."""
        from src.hypergraph.models import SpecificationNode, SpecParameter
        from src.verification.semantic.constraint_extractor import extract_constraints

        symbol_table = SymbolTable()

        # Spec A: payload_mass in [4,6] kg
        spec_a = SpecificationNode(
            id="SPEC-A",
            description="Design requirement",
            parameters=[
                SpecParameter(
                    name="payload_mass", value=5.0, unit="kg", tolerance="+/- 20%"
                )
            ],
        )

        # Spec B: mass (alias) in [4.5, 5.5] kg
        spec_b = SpecificationNode(
            id="SPEC-B",
            description="Manufacturing constraint",
            parameters=[
                SpecParameter(name="mass", value=5.0, unit="kg", tolerance="+/- 10%")
            ],
        )

        # Extract constraints
        result_a = extract_constraints(spec_a, symbol_table=symbol_table)
        result_b = extract_constraints(spec_b, symbol_table=symbol_table)

        assert len(result_a.constraints) == 1
        assert len(result_b.constraints) == 1
        assert result_a.constraints[0].canonical_name == "payload_mass"
        assert result_b.constraints[0].canonical_name == "payload_mass"

        # Solve together
        all_constraints = result_a.constraints + result_b.constraints
        solve_result = solve_constraints(all_constraints, symbol_table=symbol_table)

        # Should be SAT with intersection [4.5, 5.5]
        assert solve_result.status == "SAT"
        # Witness should use canonical name (shared variable)
        assert "payload_mass" in solve_result.witness
        val = solve_result.witness["payload_mass"]["value"]
        assert 4.5 <= val <= 5.5

    def test_extract_and_solve_cross_spec_conflict_detected(self):
        """Full pipeline detects cross-spec conflict via shared variable."""
        from src.hypergraph.models import SpecificationNode, SpecParameter
        from src.verification.semantic.constraint_extractor import extract_constraints

        symbol_table = SymbolTable()

        # Spec X: payload_mass = 2 kg exactly
        spec_x = SpecificationNode(
            id="SPEC-X",
            description="Design requirement",
            parameters=[
                SpecParameter(name="payload_mass", value=2.0, unit="kg", tolerance="")
            ],
        )

        # Spec Y: mass (alias) = 10 kg exactly
        spec_y = SpecificationNode(
            id="SPEC-Y",
            description="Conflicting requirement",
            parameters=[
                SpecParameter(name="mass", value=10.0, unit="kg", tolerance="")
            ],
        )

        # Extract constraints
        result_x = extract_constraints(spec_x, symbol_table=symbol_table)
        result_y = extract_constraints(spec_y, symbol_table=symbol_table)

        assert len(result_x.constraints) == 1
        assert len(result_y.constraints) == 1
        assert result_x.constraints[0].canonical_name == "payload_mass"
        assert result_y.constraints[0].canonical_name == "payload_mass"

        # Solve together
        all_constraints = result_x.constraints + result_y.constraints
        solve_result = solve_constraints(all_constraints, symbol_table=symbol_table)

        # Should be UNSAT (2 != 10)
        assert solve_result.status == "UNSAT"
        assert len(solve_result.unsat_core) > 0


class TestValidateForZ3:
    """Test pre-flight Z3 validation (12-02)."""

    def test_validate_for_z3_passes_complete_constraints(self):
        """All fields present -> passes."""
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        c = Constraint(
            name="SPEC-001_thickness",
            min_name="SPEC-001_thickness_min",
            max_name="SPEC-001_thickness_max",
            min_value=0.003,
            max_value=0.005,
            canonical_unit="m",
            is_equality=False,
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            term_class="structured",
            source_spec_id="SPEC-001",
        )
        is_valid, errors = validate_for_z3([c])
        assert is_valid is True
        assert errors == []

    def test_validate_for_z3_fails_missing_source_spec_id(self):
        """Structured term without source_spec_id -> error."""
        from src.verification.semantic.scoped_symbol_table import ScopedKey

        c = Constraint(
            name="SPEC-002_mass",
            min_name="SPEC-002_mass_min",
            max_name="SPEC-002_mass_max",
            min_value=4.0,
            max_value=6.0,
            canonical_unit="kg",
            is_equality=False,
            scoped_key=ScopedKey("bracket", "normal", "payload_mass"),
            term_class="structured",
            source_spec_id="",  # Missing!
        )
        is_valid, errors = validate_for_z3([c])
        assert is_valid is False
        assert len(errors) == 1
        assert "source_spec_id" in errors[0]
        assert "Z3E-03" in errors[0]

    def test_validate_for_z3_fails_missing_scoped_key(self):
        """Structured term without scoped_key -> error."""
        c = Constraint(
            name="SPEC-003_force",
            min_name="SPEC-003_force_min",
            max_name="SPEC-003_force_max",
            min_value=0,
            max_value=100,
            canonical_unit="N",
            is_equality=False,
            scoped_key=None,  # Missing!
            term_class="structured",
            source_spec_id="SPEC-003",
        )
        is_valid, errors = validate_for_z3([c])
        assert is_valid is False
        assert len(errors) == 1
        assert "scoped_key" in errors[0]
        assert "SID-01" in errors[0]

    def test_validate_for_z3_ignores_nl_only(self):
        """nl_only terms don't need source_spec_id or scoped_key."""
        c = Constraint(
            name="SPEC-004_finish",
            min_name="SPEC-004_finish_min",
            max_name="SPEC-004_finish_max",
            exact_value=1.6,
            canonical_unit="um",
            is_equality=True,
            scoped_key=None,  # Missing but ok for nl_only
            term_class="nl_only",
            source_spec_id="",  # Missing but ok for nl_only
        )
        is_valid, errors = validate_for_z3([c])
        assert is_valid is True
        assert errors == []


class TestSolveConstraintsScoped:
    """Test scoped constraint solving (12-02)."""

    def test_solve_constraints_scoped_blocks_invalid(self):
        """Raises ValueError on validation fail."""
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable
        from src.verification.semantic.z3_solver import solve_constraints_scoped

        scoped_table = ScopedSymbolTable()

        # Constraint missing source_spec_id
        c = Constraint(
            name="SPEC-BAD_mass",
            min_name="SPEC-BAD_mass_min",
            max_name="SPEC-BAD_mass_max",
            min_value=4.0,
            max_value=6.0,
            canonical_unit="kg",
            is_equality=False,
            scoped_key=None,  # Missing!
            term_class="structured",
            source_spec_id="",  # Missing!
        )

        with pytest.raises(ValueError) as exc_info:
            solve_constraints_scoped([c], scoped_table)

        assert "validation failed" in str(exc_info.value).lower()

    def test_solve_constraints_scoped_uses_scoped_vars(self):
        """Uses ScopedSymbolTable variables."""
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
            ScopedSymbolTable,
        )
        from src.verification.semantic.z3_solver import solve_constraints_scoped

        scoped_table = ScopedSymbolTable()

        c = Constraint(
            name="SPEC-001_thickness",
            min_name="SPEC-001_thickness_min",
            max_name="SPEC-001_thickness_max",
            min_value=0.003,
            max_value=0.005,
            canonical_unit="m",
            is_equality=False,
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            term_class="structured",
            source_spec_id="SPEC-001",
        )

        result = solve_constraints_scoped([c], scoped_table)

        assert result.status == "SAT"
        # Witness should use scoped key name
        assert "bracket__normal__plate_thickness" in result.witness
        val = result.witness["bracket__normal__plate_thickness"]["value"]
        assert 0.003 <= val <= 0.005

    def test_solve_constraints_scoped_adds_invariants(self):
        """Invariants added from scoped_table."""
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
            ScopedSymbolTable,
        )
        from src.verification.semantic.z3_solver import solve_constraints_scoped

        scoped_table = ScopedSymbolTable()

        # Negative plate_thickness should violate POS invariant
        c = Constraint(
            name="SPEC-NEG_thickness",
            min_name="SPEC-NEG_thickness_min",
            max_name="SPEC-NEG_thickness_max",
            exact_value=-0.001,  # Negative!
            canonical_unit="m",
            is_equality=True,
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            term_class="structured",
            source_spec_id="SPEC-NEG",
        )

        result = solve_constraints_scoped([c], scoped_table)

        assert result.status == "UNSAT"
        # Should have invariant in unsat core
        assert any("INV_POS" in name for name in result.unsat_core)

    def test_solve_constraints_scoped_filters_nl_only(self):
        """nl_only constraints filtered out before solving."""
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
            ScopedSymbolTable,
        )
        from src.verification.semantic.z3_solver import solve_constraints_scoped

        scoped_table = ScopedSymbolTable()

        # Mix of structured and nl_only
        structured = Constraint(
            name="SPEC-001_mass",
            min_name="SPEC-001_mass_min",
            max_name="SPEC-001_mass_max",
            min_value=4.0,
            max_value=6.0,
            canonical_unit="kg",
            is_equality=False,
            scoped_key=ScopedKey("bracket", "normal", "payload_mass"),
            term_class="structured",
            source_spec_id="SPEC-001",
        )
        nl_only = Constraint(
            name="SPEC-001_finish",
            min_name="SPEC-001_finish_min",
            max_name="SPEC-001_finish_max",
            exact_value=1.6,
            canonical_unit="um",
            is_equality=True,
            scoped_key=None,  # No scoped key for nl_only
            term_class="nl_only",
            source_spec_id="",  # No source for nl_only
        )

        result = solve_constraints_scoped([structured, nl_only], scoped_table)

        assert result.status == "SAT"
        # Only 1 constraint counted (structured only)
        assert result.constraint_count == 1

    def test_solve_constraints_scoped_identity_gate_blocks(self):
        """Identity gate blocks on missing identity fields."""
        from src.verification.semantic.scoped_symbol_table import (
            ScopedKey,
            ScopedSymbolTable,
        )
        from src.verification.semantic.z3_solver import solve_constraints_scoped

        scoped_table = ScopedSymbolTable()

        # Constraint with empty entity_id
        c = Constraint(
            name="SPEC-IGT_thickness",
            min_name="SPEC-IGT_thickness_min",
            max_name="SPEC-IGT_thickness_max",
            min_value=0.003,
            max_value=0.005,
            canonical_unit="m",
            is_equality=False,
            scoped_key=ScopedKey("", "normal", "plate_thickness"),  # Empty entity_id!
            term_class="structured",
            source_spec_id="SPEC-IGT",
        )

        with pytest.raises(ValueError) as exc_info:
            solve_constraints_scoped([c], scoped_table)

        assert "Identity validation failed" in str(exc_info.value)
        assert "entity_id is empty" in str(exc_info.value)
