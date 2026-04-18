"""Tests for constraint extraction from SpecificationNode."""

import pytest

from src.hypergraph.models import SpecificationNode, SpecParameter
from src.verification.semantic.constraint_extractor import (
    Constraint,
    ExtractionWarning,
    SkipReason,
    extract_constraints,
)
from src.verification.semantic.symbol_table import SymbolTable


class TestExtractConstraints:
    """Test constraint extraction from specs."""

    def test_extract_single_param_with_tolerance(self):
        """Extract constraint from parameter with percentage tolerance."""
        spec = SpecificationNode(
            id="SPEC-001",
            description="Wall thickness spec",
            parameters=[
                SpecParameter(
                    name="wall_thickness", value=2.5, unit="mm", tolerance="+/- 5%"
                )
            ],
        )
        result = extract_constraints(spec)

        assert len(result.constraints) == 1
        constraint = result.constraints[0]
        assert constraint.name == "SPEC-001_wall_thickness"
        assert constraint.min_name == "SPEC-001_wall_thickness_min"
        assert constraint.max_name == "SPEC-001_wall_thickness_max"
        # 2.5mm = 0.0025m, +/- 5% = 0.002375 to 0.002625
        assert constraint.min_value == pytest.approx(0.002375)
        assert constraint.max_value == pytest.approx(0.002625)
        assert constraint.canonical_unit == "m"

    def test_extract_multiple_params(self):
        """Extract multiple constraints from one spec."""
        spec = SpecificationNode(
            id="SPEC-002",
            description="Multi-param spec",
            parameters=[
                SpecParameter(name="width", value=100, unit="mm", tolerance="+/- 1%"),
                SpecParameter(name="height", value=50, unit="mm", tolerance="+/- 2%"),
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 2
        names = {c.name for c in result.constraints}
        assert "SPEC-002_width" in names
        assert "SPEC-002_height" in names

    def test_extract_param_no_tolerance_exact_equality(self):
        """Parameter without tolerance becomes exact equality constraint."""
        spec = SpecificationNode(
            id="SPEC-003",
            description="Exact value spec",
            parameters=[
                SpecParameter(name="diameter", value=10, unit="mm", tolerance="")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        constraint = result.constraints[0]
        assert constraint.is_equality
        assert constraint.exact_value == pytest.approx(0.01)  # 10mm -> 0.01m

    def test_extract_param_range_tolerance(self):
        """Range tolerance (8-12) becomes direct bounds."""
        spec = SpecificationNode(
            id="SPEC-004",
            description="Range spec",
            parameters=[
                SpecParameter(name="load", value=0, unit="kg", tolerance="8-12")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        constraint = result.constraints[0]
        assert constraint.min_value == pytest.approx(8.0)  # kg is canonical
        assert constraint.max_value == pytest.approx(12.0)

    def test_extract_missing_value_warning(self):
        """Missing value generates warning, skips constraint."""
        # SpecParameter uses float | str, not Optional - can't test None directly
        # Instead test string value that can't be converted to float
        spec = SpecificationNode(
            id="SPEC-005",
            description="Incomplete spec",
            parameters=[
                SpecParameter(
                    name="undefined", value="TBD", unit="mm", tolerance="+/- 5%"
                )
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 0
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        # String "TBD" fails float conversion, caught by exception handler
        assert warning.code == "NON_NUMERIC_VALUE"
        assert warning.node_id == "SPEC-005"
        assert warning.field == "undefined"

    def test_extract_unparseable_tolerance_warning(self):
        """Unparseable tolerance generates warning, skips constraint."""
        spec = SpecificationNode(
            id="SPEC-006",
            description="Bad tolerance",
            parameters=[
                SpecParameter(
                    name="length", value=10, unit="mm", tolerance="approximately"
                )
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 0
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        # "approximately" is now classified as TOLERANCE_AMBIGUOUS (07-02)
        assert warning.code == "TOLERANCE_AMBIGUOUS"
        assert "approximately" in warning.raw_value

    def test_extract_unknown_unit_warning(self):
        """Unknown unit generates warning, skips constraint."""
        spec = SpecificationNode(
            id="SPEC-007",
            description="Unknown unit",
            parameters=[
                SpecParameter(
                    name="distance", value=10, unit="flargles", tolerance="+/- 5%"
                )
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 0
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "UNIT_CONVERSION_FAILED"

    def test_extract_empty_parameters_no_error(self):
        """Spec with no parameters returns empty results."""
        spec = SpecificationNode(
            id="SPEC-008",
            description="No params",
            parameters=[],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 0
        assert len(result.warnings) == 0

    def test_extract_dimensionless_param(self):
        """Dimensionless parameter (no unit) works."""
        spec = SpecificationNode(
            id="SPEC-009",
            description="Dimensionless",
            parameters=[
                SpecParameter(name="ratio", value=0.5, unit="", tolerance="+/- 10%")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        assert result.constraints[0].canonical_unit == ""

    def test_extract_handles_dict_style_parameters(self):
        """Legacy dict parameters are coerced and do not crash extraction."""
        spec = SpecificationNode(
            id="SPEC-009B",
            description="Legacy dict params",
            parameters=[
                SpecParameter(name="diameter", value=10, unit="mm", tolerance="")
            ],
        )
        # Simulate legacy/corrupt state where parameters were stored as dicts
        spec = spec.model_copy(
            update={
                "parameters": [
                    {"name": "diameter", "value": 10, "unit": "mm", "tolerance": ""}
                ]
            }
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        assert result.compiled_count == 1


class TestToleranceBeforeConversion:
    """Test BF-2 fix: tolerance parsed BEFORE unit conversion."""

    def test_absolute_tolerance_mm_to_m(self):
        """4.0mm +/- 0.2mm -> [3.8mm, 4.2mm] -> [0.0038m, 0.0042m]."""
        spec = SpecificationNode(
            id="SPEC-BF2-1",
            description="Absolute tolerance with unit conversion",
            parameters=[
                SpecParameter(
                    name="thickness", value=4.0, unit="mm", tolerance="+/- 0.2"
                )
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(0.0038)
        assert c.max_value == pytest.approx(0.0042)
        assert c.canonical_unit == "m"

    def test_percentage_tolerance_mm_to_m(self):
        """100mm +/- 5% -> [95mm, 105mm] -> [0.095m, 0.105m]."""
        spec = SpecificationNode(
            id="SPEC-BF2-2",
            description="Percentage tolerance with unit conversion",
            parameters=[
                SpecParameter(name="length", value=100, unit="mm", tolerance="+/- 5%")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(0.095)
        assert c.max_value == pytest.approx(0.105)
        assert c.canonical_unit == "m"

    def test_range_tolerance_um_to_m(self):
        """10um with range 7-13um -> [7um, 13um] -> [7e-6m, 13e-6m]."""
        spec = SpecificationNode(
            id="SPEC-BF2-3",
            description="Range tolerance with micrometer conversion",
            parameters=[
                SpecParameter(name="roughness", value=10, unit="um", tolerance="7-13")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(7e-6)
        assert c.max_value == pytest.approx(13e-6)
        assert c.canonical_unit == "m"

    def test_no_tolerance_exact_equality(self):
        """No tolerance -> exact equality after conversion."""
        spec = SpecificationNode(
            id="SPEC-BF2-4",
            description="Exact value no tolerance",
            parameters=[
                SpecParameter(name="diameter", value=10, unit="mm", tolerance="")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.is_equality
        assert c.exact_value == pytest.approx(0.01)
        assert c.canonical_unit == "m"


class TestOneSidedConstraints:
    """Test one-sided constraint handling (07-02)."""

    def test_one_sided_min(self):
        """min tolerance compiles to >= inequality."""
        spec = SpecificationNode(
            id="SPEC-MIN-1",
            description="Minimum load spec",
            parameters=[SpecParameter(name="load", value=5, unit="N", tolerance="min")],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(5.0)
        assert c.max_value is None
        assert c.canonical_unit == "N"

    def test_one_sided_max(self):
        """max tolerance compiles to <= inequality."""
        spec = SpecificationNode(
            id="SPEC-MAX-1",
            description="Maximum pressure spec",
            parameters=[
                SpecParameter(name="pressure", value=100, unit="Pa", tolerance="max")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value is None
        assert c.max_value == pytest.approx(100.0)
        assert c.canonical_unit == "Pa"

    def test_one_sided_gte_operator(self):
        """>= tolerance compiles correctly."""
        spec = SpecificationNode(
            id="SPEC-GTE-1",
            description="Greater than or equal spec",
            parameters=[
                SpecParameter(name="thickness", value=2, unit="mm", tolerance=">=")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(0.002)
        assert c.max_value is None

    def test_one_sided_lte_operator(self):
        """<= tolerance compiles correctly."""
        spec = SpecificationNode(
            id="SPEC-LTE-1",
            description="Less than or equal spec",
            parameters=[
                SpecParameter(name="weight", value=500, unit="g", tolerance="<=")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value is None
        assert c.max_value == pytest.approx(0.5)  # 500g = 0.5kg

    def test_ambiguous_tolerance_warning(self):
        """Ambiguous tolerances (approx, ~) generate warning and skip."""
        spec = SpecificationNode(
            id="SPEC-AMB-1",
            description="Ambiguous tolerance",
            parameters=[
                SpecParameter(name="length", value=10, unit="mm", tolerance="~5")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 0
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "TOLERANCE_AMBIGUOUS"


class TestDimensionlessUnits:
    """Test dimensionless unit handling (07-02)."""

    def test_ratio_unit(self):
        """ratio unit compiles as dimensionless."""
        spec = SpecificationNode(
            id="SPEC-DIM-1",
            description="Ratio spec",
            parameters=[
                SpecParameter(
                    name="safety_factor", value=3.0, unit="ratio", tolerance=""
                )
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.exact_value == pytest.approx(3.0)
        assert c.canonical_unit == ""

    def test_factor_unit(self):
        """factor unit compiles as dimensionless."""
        spec = SpecificationNode(
            id="SPEC-DIM-2",
            description="Factor spec",
            parameters=[
                SpecParameter(
                    name="scale_factor", value=1.5, unit="factor", tolerance="+/- 10%"
                )
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(1.35)
        assert c.max_value == pytest.approx(1.65)
        assert c.canonical_unit == ""

    def test_count_unit(self):
        """count unit compiles as dimensionless."""
        spec = SpecificationNode(
            id="SPEC-DIM-3",
            description="Count spec",
            parameters=[
                SpecParameter(name="num_holes", value=4, unit="count", tolerance="")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.exact_value == pytest.approx(4.0)
        assert c.canonical_unit == ""

    def test_pcs_unit(self):
        """pcs (pieces) unit compiles as dimensionless."""
        spec = SpecificationNode(
            id="SPEC-DIM-4",
            description="Pieces spec",
            parameters=[
                SpecParameter(name="quantity", value=10, unit="pcs", tolerance="8-12")
            ],
        )
        result = extract_constraints(spec)
        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.min_value == pytest.approx(8.0)
        assert c.max_value == pytest.approx(12.0)
        assert c.canonical_unit == ""


class TestExtractionWarning:
    """Test warning structure."""

    def test_warning_has_required_fields(self):
        warning = ExtractionWarning(
            code="TEST_CODE",
            severity="WARNING",
            node_id="NODE-1",
            field="test_field",
            raw_value="bad_value",
            message="Test message",
            suggested_action="Fix it",
        )
        assert warning.code == "TEST_CODE"
        assert warning.node_id == "NODE-1"


class TestSymbolTableIntegration:
    """Test SymbolTable integration (08-02)."""

    def test_canonical_unit_from_symbol_table_for_torque(self):
        """Mapped params should use symbol_table canonical_unit, not unit_converter."""
        st = SymbolTable()
        spec = SpecificationNode(
            id="SPEC-TORQUE",
            description="Torque spec",
            parameters=[
                SpecParameter(
                    name="installation_torque", value=10, unit="N*m", tolerance="+/- 1"
                )
            ],
        )
        result = extract_constraints(spec, symbol_table=st)

        assert len(result.constraints) == 1
        constraint = result.constraints[0]
        # Key assertion: torque should be N*m (from symbol_table), not J (from unit_converter)
        assert (
            constraint.canonical_unit == "N*m"
        ), f"Expected N*m, got {constraint.canonical_unit}"
        assert constraint.canonical_name == "installation_torque"

    def test_extract_unmapped_param_generates_warning_with_suggestions(self):
        """Unmapped param skips with UNMAPPED_SYMBOL warning and fuzzy suggestions."""
        symbol_table = SymbolTable()  # Use explicit symbol_table
        spec = SpecificationNode(
            id="SPEC-UNMAP-1",
            description="Unmapped param",
            parameters=[
                SpecParameter(
                    name="unknown_param", value=10, unit="mm", tolerance="+/- 5%"
                )
            ],
        )
        result = extract_constraints(spec, symbol_table=symbol_table)
        assert len(result.constraints) == 0
        assert result.skipped_count == 1
        assert result.skip_breakdown["UNMAPPED_SYMBOL"] == 1
        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert warning.code == "UNMAPPED_SYMBOL"
        assert "unknown_param" in warning.message

    def test_extract_mapped_param_uses_canonical_name(self):
        """Mapped param compiles with canonical_name set."""
        symbol_table = SymbolTable()  # Use explicit symbol_table
        spec = SpecificationNode(
            id="SPEC-MAP-1",
            description="Mapped param",
            parameters=[
                SpecParameter(
                    name="payload_mass", value=5, unit="kg", tolerance="+/- 5%"
                )
            ],
        )
        result = extract_constraints(spec, symbol_table=symbol_table)
        assert len(result.constraints) == 1
        assert result.compiled_count == 1
        assert result.skipped_count == 0
        constraint = result.constraints[0]
        assert constraint.canonical_name == "payload_mass"
        assert constraint.name == "SPEC-MAP-1_payload_mass"

    def test_extract_alias_resolves_to_canonical(self):
        """Alias name resolves to canonical_name."""
        symbol_table = SymbolTable()  # Use explicit symbol_table
        spec = SpecificationNode(
            id="SPEC-ALIAS-1",
            description="Alias param",
            parameters=[
                # "mass" is an alias for "payload_mass"
                SpecParameter(name="mass", value=10, unit="kg", tolerance="")
            ],
        )
        result = extract_constraints(spec, symbol_table=symbol_table)
        assert len(result.constraints) == 1
        constraint = result.constraints[0]
        assert constraint.canonical_name == "payload_mass"
        assert constraint.name == "SPEC-ALIAS-1_mass"


class TestSkipTracking:
    """Test skip tracking and coverage reporting (07-03)."""

    def test_coverage_calculation(self):
        """Coverage = compiled / (compiled + skipped)."""
        spec = SpecificationNode(
            id="SPEC-COV-1",
            description="Mixed spec",
            parameters=[
                SpecParameter(name="valid1", value=10, unit="mm", tolerance="+/- 5%"),
                SpecParameter(name="valid2", value=5, unit="kg", tolerance=""),
                SpecParameter(name="invalid", value=10, unit="flargles", tolerance=""),
            ],
        )
        result = extract_constraints(spec)
        assert result.compiled_count == 2
        assert result.skipped_count == 1
        assert result.coverage == pytest.approx(2 / 3)

    def test_skip_breakdown_by_reason(self):
        """Skip breakdown counts each reason."""
        spec = SpecificationNode(
            id="SPEC-SKIP-1",
            description="Multiple skip reasons",
            parameters=[
                SpecParameter(
                    name="bad_unit", value=10, unit="flargles", tolerance=""
                ),  # UNIT_CONVERSION_FAILED
                SpecParameter(
                    name="ambiguous", value=5, unit="mm", tolerance="~3"
                ),  # TOLERANCE_AMBIGUOUS
                SpecParameter(
                    name="non_numeric", value="TBD", unit="mm", tolerance=""
                ),  # NON_NUMERIC_VALUE
            ],
        )
        result = extract_constraints(spec)
        assert result.compiled_count == 0
        assert result.skipped_count == 3
        assert result.skip_breakdown["UNIT_CONVERSION_FAILED"] == 1
        assert result.skip_breakdown["TOLERANCE_AMBIGUOUS"] == 1
        assert result.skip_breakdown["NON_NUMERIC_VALUE"] == 1

    def test_coverage_zero_params(self):
        """Zero params -> 100% coverage (not div by zero)."""
        spec = SpecificationNode(
            id="SPEC-EMPTY-1", description="Empty spec", parameters=[]
        )
        result = extract_constraints(spec)
        assert result.compiled_count == 0
        assert result.skipped_count == 0
        assert result.coverage == 1.0

    def test_coverage_all_compiled(self):
        """All compiled -> 100% coverage."""
        spec = SpecificationNode(
            id="SPEC-ALL-1",
            description="All valid",
            parameters=[
                SpecParameter(name="p1", value=10, unit="mm", tolerance=""),
                SpecParameter(name="p2", value=5, unit="kg", tolerance="+/- 5%"),
            ],
        )
        result = extract_constraints(spec)
        assert result.compiled_count == 2
        assert result.skipped_count == 0
        assert result.coverage == 1.0

    def test_coverage_all_skipped(self):
        """All skipped -> 0% coverage."""
        spec = SpecificationNode(
            id="SPEC-NONE-1",
            description="All invalid",
            parameters=[
                SpecParameter(name="p1", value=10, unit="flargles", tolerance=""),
                SpecParameter(name="p2", value=5, unit="blargs", tolerance=""),
            ],
        )
        result = extract_constraints(spec)
        assert result.compiled_count == 0
        assert result.skipped_count == 2
        assert result.coverage == 0.0


class TestConstraintScopedFields:
    """Test Constraint scoped identity fields (12-02)."""

    def test_constraint_has_scoped_key_field(self):
        """Constraint has scoped_key field, default None."""
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
        )
        assert hasattr(c, "scoped_key")
        assert c.scoped_key is None

    def test_constraint_has_term_class_field(self):
        """Constraint has term_class field, default 'structured'."""
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
        )
        assert hasattr(c, "term_class")
        assert c.term_class == "structured"

    def test_constraint_has_source_spec_id_field(self):
        """Constraint has source_spec_id field, default ''."""
        c = Constraint(
            name="test",
            min_name="test_min",
            max_name="test_max",
        )
        assert hasattr(c, "source_spec_id")
        assert c.source_spec_id == ""

    def test_skip_reason_has_nl_only_term(self):
        """SkipReason has NL_ONLY_TERM value."""
        assert hasattr(SkipReason, "NL_ONLY_TERM")
        assert SkipReason.NL_ONLY_TERM.value == "NL_ONLY_TERM"


class TestExtractConstraintsScoped:
    """Test scoped constraint extraction (12-02)."""

    def test_extract_constraints_scoped_basic(self):
        """Basic extraction with scope context."""
        from src.verification.semantic.constraint_extractor import (
            extract_constraints_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        scoped_table = ScopedSymbolTable()

        # plate_thickness is in default ontology
        spec = SpecificationNode(
            id="SPEC-001",
            description="Bracket spec",
            parameters=[
                SpecParameter(
                    name="plate_thickness", value=4.0, unit="mm", tolerance="+/- 5%"
                )
            ],
        )
        result = extract_constraints_scoped(
            spec, scoped_table, entity_id="bracket", regime_id="normal"
        )

        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.source_spec_id == "SPEC-001"
        assert c.scoped_key is not None
        assert c.scoped_key.entity_id == "bracket"
        assert c.scoped_key.regime_id == "normal"
        assert c.scoped_key.quantity_id == "plate_thickness"
        assert c.term_class == "structured"

    def test_extract_constraints_scoped_skips_nl_only(self):
        """nl_only params skipped, counted in breakdown."""
        from dataclasses import dataclass

        from src.verification.semantic.constraint_extractor import (
            extract_constraints_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        scoped_table = ScopedSymbolTable()

        # Create duck-typed param with term_class="nl_only"
        @dataclass
        class NLParam:
            name: str = "surface_finish"
            value: float = 1.6
            unit: str = "um"
            tolerance: str = ""
            term_class: str = "nl_only"
            quantity_id: str = None

        nl_param = NLParam()

        spec = SpecificationNode(
            id="SPEC-002",
            description="NL spec",
            parameters=[],
        )
        # Use object.__setattr__ to bypass Pydantic validation
        object.__setattr__(spec, "parameters", [nl_param])

        result = extract_constraints_scoped(spec, scoped_table)

        assert len(result.constraints) == 0
        assert result.skipped_count == 1
        assert result.skip_breakdown["NL_ONLY_TERM"] == 1

    def test_extract_constraints_scoped_uses_entity_regime(self):
        """scoped_key has correct entity/regime."""
        from src.verification.semantic.constraint_extractor import (
            extract_constraints_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        scoped_table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-003",
            description="Housing spec",
            parameters=[
                SpecParameter(
                    name="payload_mass", value=5.0, unit="kg", tolerance="+/- 10%"
                )
            ],
        )
        result = extract_constraints_scoped(
            spec, scoped_table, entity_id="housing", regime_id="shock"
        )

        assert len(result.constraints) == 1
        c = result.constraints[0]
        assert c.scoped_key.entity_id == "housing"
        assert c.scoped_key.regime_id == "shock"

    def test_extract_constraints_scoped_sets_source_spec_id(self):
        """Every constraint has spec.id as source_spec_id."""
        from src.verification.semantic.constraint_extractor import (
            extract_constraints_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        scoped_table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-SOURCE-TEST",
            description="Source ID test",
            parameters=[
                SpecParameter(name="hole_diameter", value=6.0, unit="mm", tolerance=""),
                SpecParameter(
                    name="safety_factor", value=2.5, unit="ratio", tolerance="+/- 10%"
                ),
            ],
        )
        result = extract_constraints_scoped(spec, scoped_table)

        assert len(result.constraints) == 2
        for c in result.constraints:
            assert c.source_spec_id == "SPEC-SOURCE-TEST"

    def test_extract_constraints_scoped_unmapped_param(self):
        """Params without quantity_id skipped with UNMAPPED_SYMBOL."""
        from src.verification.semantic.constraint_extractor import (
            extract_constraints_scoped,
        )
        from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable

        scoped_table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-UNMAP",
            description="Unknown param",
            parameters=[
                SpecParameter(
                    name="fluxcapacitor_power", value=1.21, unit="GW", tolerance=""
                )
            ],
        )
        result = extract_constraints_scoped(spec, scoped_table)

        assert len(result.constraints) == 0
        assert result.skipped_count == 1
        assert result.skip_breakdown["UNMAPPED_SYMBOL"] == 1
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "UNMAPPED_SYMBOL"
