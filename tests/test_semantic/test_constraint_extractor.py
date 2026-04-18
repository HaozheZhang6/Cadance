"""Tests for constraint extractor with interface-prefixed namespacing."""

from src.hypergraph.models import SpecificationNode, SpecParameter
from src.verification.semantic.constraint_extractor import (
    ExtractionResult,
    extract_constraints_scoped,
    extract_constraints_with_interface,
)
from src.verification.semantic.scoped_symbol_table import ScopedSymbolTable


class TestInterfacePrefixedNamespacing:
    """Tests for cross-spec parameter namespacing via entity_id.

    Problem: host holes (0.0065-0.0067m) and payload holes (0.0054-0.0056m)
    both using `hole_diameter` get same Z3 var -> UNSAT conflict.

    Solution: Use interface (host/payload) as entity_id to produce
    distinct ScopedKeys and Z3 variables.
    """

    def test_host_and_payload_specs_produce_distinct_scoped_keys(self):
        """Same param name + different entity_id => distinct ScopedKeys."""
        table = ScopedSymbolTable()

        # Host interface spec with hole_diameter
        host_spec = SpecificationNode(
            id="SPEC-HOST",
            description="Host interface holes",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0066,
                    unit="m",
                    tolerance="0.0065-0.0067",
                )
            ],
            metadata={"interface": "host"},
        )

        # Payload interface spec with hole_diameter
        payload_spec = SpecificationNode(
            id="SPEC-PAYLOAD",
            description="Payload interface holes",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0055,
                    unit="m",
                    tolerance="0.0054-0.0056",
                )
            ],
            metadata={"interface": "payload"},
        )

        # Extract with interface-derived entity_id
        host_result = extract_constraints_scoped(
            host_spec, table, entity_id="host", regime_id="normal"
        )
        payload_result = extract_constraints_scoped(
            payload_spec, table, entity_id="payload", regime_id="normal"
        )

        assert host_result.compiled_count == 1
        assert payload_result.compiled_count == 1

        host_constraint = host_result.constraints[0]
        payload_constraint = payload_result.constraints[0]

        # Distinct ScopedKeys
        assert host_constraint.scoped_key != payload_constraint.scoped_key
        assert host_constraint.scoped_key.entity_id == "host"
        assert payload_constraint.scoped_key.entity_id == "payload"

    def test_distinct_z3_var_names_for_cross_interface_params(self):
        """Z3 var names differ for same param across interfaces."""
        table = ScopedSymbolTable()

        host_spec = SpecificationNode(
            id="SPEC-H",
            description="Host holes",
            parameters=[SpecParameter(name="hole_diameter", value=0.0066, unit="m")],
        )
        payload_spec = SpecificationNode(
            id="SPEC-P",
            description="Payload holes",
            parameters=[SpecParameter(name="hole_diameter", value=0.0055, unit="m")],
        )

        host_result = extract_constraints_scoped(
            host_spec, table, entity_id="host", regime_id="normal"
        )
        payload_result = extract_constraints_scoped(
            payload_spec, table, entity_id="payload", regime_id="normal"
        )

        # Get the Z3 variable names from scoped keys
        host_z3_name = host_result.constraints[0].scoped_key.to_z3_name()
        payload_z3_name = payload_result.constraints[0].scoped_key.to_z3_name()

        assert host_z3_name != payload_z3_name
        assert "host__" in host_z3_name
        assert "payload__" in payload_z3_name

    def test_z3_sat_with_previously_conflicting_specs(self):
        """Z3 solver returns SAT with properly namespaced constraints.

        Previously: host_hole_diameter [0.0065, 0.0067] and
                   payload_hole_diameter [0.0054, 0.0056] shared var -> UNSAT
        Now: distinct vars -> SAT
        """
        from z3 import Solver, sat

        table = ScopedSymbolTable()

        host_spec = SpecificationNode(
            id="SPEC-HOST",
            description="Host interface",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0066,
                    unit="m",
                    tolerance="0.0065-0.0067",
                )
            ],
        )
        payload_spec = SpecificationNode(
            id="SPEC-PAYLOAD",
            description="Payload interface",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0055,
                    unit="m",
                    tolerance="0.0054-0.0056",
                )
            ],
        )

        host_result = extract_constraints_scoped(
            host_spec, table, entity_id="host", regime_id="normal"
        )
        payload_result = extract_constraints_scoped(
            payload_spec, table, entity_id="payload", regime_id="normal"
        )

        # Build Z3 constraints
        solver = Solver()
        for c in host_result.constraints + payload_result.constraints:
            key = c.scoped_key
            z3_var = table._z3_vars[key]
            if c.min_value is not None:
                solver.add(z3_var >= c.min_value)
            if c.max_value is not None:
                solver.add(z3_var <= c.max_value)

        # Should be SAT (distinct vars, non-overlapping ranges OK)
        result = solver.check()
        assert result == sat

    def test_single_interface_spec_unchanged(self):
        """Existing single-interface extraction API unchanged."""
        table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-SINGLE",
            description="Single interface spec",
            parameters=[
                SpecParameter(
                    name="plate_thickness",
                    value=0.003,
                    unit="m",
                    tolerance="0.002-0.004",
                )
            ],
        )

        # Default entity_id="system" still works
        result = extract_constraints_scoped(spec, table)

        assert result.compiled_count == 1
        assert result.constraints[0].scoped_key.entity_id == "system"
        assert result.constraints[0].source_spec_id == "SPEC-SINGLE"

    def test_scoped_extractor_handles_dict_style_parameters(self):
        """Scoped extraction tolerates legacy dict parameters."""
        table = ScopedSymbolTable()
        spec = SpecificationNode(
            id="SPEC-DICT",
            description="Legacy dict params",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.006,
                    unit="m",
                    tolerance="0.005-0.007",
                )
            ],
        )
        spec = spec.model_copy(
            update={
                "parameters": [
                    {
                        "name": "hole_diameter",
                        "value": 0.006,
                        "unit": "m",
                        "tolerance": "0.005-0.007",
                    }
                ]
            }
        )

        result = extract_constraints_scoped(spec, table)
        assert result.compiled_count == 1

    def test_spec_metadata_interface_used_for_entity_id(self):
        """Spec metadata['interface'] can inform entity_id choice.

        This test documents the caller pattern - the caller reads
        spec.metadata['interface'] and passes it as entity_id.
        """
        table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-META",
            description="Spec with interface metadata",
            parameters=[SpecParameter(name="hole_diameter", value=0.006, unit="m")],
            metadata={"interface": "host"},
        )

        # Caller extracts interface from metadata and passes as entity_id
        interface = spec.metadata.get("interface", "system")
        result = extract_constraints_scoped(
            spec, table, entity_id=interface, regime_id="normal"
        )

        assert result.compiled_count == 1
        assert result.constraints[0].scoped_key.entity_id == "host"


class TestExtractConstraintsWithInterface:
    """Tests for extract_constraints_with_interface convenience function."""

    def test_auto_extracts_interface_from_metadata(self):
        """Function auto-extracts interface from spec.metadata['interface']."""
        table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-AUTO",
            description="Auto interface extraction",
            parameters=[SpecParameter(name="hole_diameter", value=0.006, unit="m")],
            metadata={"interface": "payload"},
        )

        result = extract_constraints_with_interface(spec, table)

        assert result.compiled_count == 1
        assert result.constraints[0].scoped_key.entity_id == "payload"

    def test_defaults_to_system_without_interface(self):
        """Falls back to 'system' entity_id when no interface in metadata."""
        table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-NO-IFACE",
            description="No interface metadata",
            parameters=[SpecParameter(name="plate_thickness", value=0.003, unit="m")],
        )

        result = extract_constraints_with_interface(spec, table)

        assert result.compiled_count == 1
        assert result.constraints[0].scoped_key.entity_id == "system"

    def test_host_payload_distinct_via_helper(self):
        """Distinct Z3 vars for host/payload via helper function."""
        table = ScopedSymbolTable()

        host_spec = SpecificationNode(
            id="SPEC-H",
            description="Host",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0066,
                    unit="m",
                    tolerance="0.0065-0.0067",
                )
            ],
            metadata={"interface": "host"},
        )
        payload_spec = SpecificationNode(
            id="SPEC-P",
            description="Payload",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0055,
                    unit="m",
                    tolerance="0.0054-0.0056",
                )
            ],
            metadata={"interface": "payload"},
        )

        host_result = extract_constraints_with_interface(host_spec, table)
        payload_result = extract_constraints_with_interface(payload_spec, table)

        assert host_result.constraints[0].scoped_key.entity_id == "host"
        assert payload_result.constraints[0].scoped_key.entity_id == "payload"
        # Distinct keys
        assert (
            host_result.constraints[0].scoped_key
            != payload_result.constraints[0].scoped_key
        )

    def test_z3_sat_with_helper_function(self):
        """Full Z3 solve SAT with helper function for cross-interface specs."""
        from z3 import Solver, sat

        table = ScopedSymbolTable()

        host_spec = SpecificationNode(
            id="SPEC-HOST-H",
            description="Host holes",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0066,
                    unit="m",
                    tolerance="0.0065-0.0067",
                )
            ],
            metadata={"interface": "host"},
        )
        payload_spec = SpecificationNode(
            id="SPEC-PAYLOAD-P",
            description="Payload holes",
            parameters=[
                SpecParameter(
                    name="hole_diameter",
                    value=0.0055,
                    unit="m",
                    tolerance="0.0054-0.0056",
                )
            ],
            metadata={"interface": "payload"},
        )

        host_result = extract_constraints_with_interface(host_spec, table)
        payload_result = extract_constraints_with_interface(payload_spec, table)

        solver = Solver()
        for c in host_result.constraints + payload_result.constraints:
            key = c.scoped_key
            z3_var = table._z3_vars[key]
            if c.min_value is not None:
                solver.add(z3_var >= c.min_value)
            if c.max_value is not None:
                solver.add(z3_var <= c.max_value)

        assert solver.check() == sat

    def test_respects_explicit_entity_id_override(self):
        """entity_id parameter overrides metadata['interface']."""
        table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-OVERRIDE",
            description="Override test",
            parameters=[SpecParameter(name="hole_diameter", value=0.006, unit="m")],
            metadata={"interface": "host"},
        )

        # Explicit entity_id overrides metadata
        result = extract_constraints_with_interface(
            spec, table, entity_id="custom_entity"
        )

        assert result.constraints[0].scoped_key.entity_id == "custom_entity"

    def test_respects_regime_parameter(self):
        """regime_id parameter is passed through."""
        table = ScopedSymbolTable()

        spec = SpecificationNode(
            id="SPEC-REGIME",
            description="Regime test",
            parameters=[SpecParameter(name="plate_thickness", value=0.003, unit="m")],
            metadata={"interface": "bracket"},
        )

        result = extract_constraints_with_interface(spec, table, regime_id="shock")

        assert result.constraints[0].scoped_key.regime_id == "shock"


class TestExtractionResultCoverage:
    """Tests for ExtractionResult coverage calculation."""

    def test_coverage_calculation(self):
        """coverage = compiled / (compiled + skipped)."""
        result = ExtractionResult()
        result.compiled_count = 3
        result.skipped_count = 1
        assert result.coverage == 0.75

    def test_coverage_all_compiled(self):
        """100% coverage when all params compile."""
        result = ExtractionResult()
        result.compiled_count = 5
        result.skipped_count = 0
        assert result.coverage == 1.0

    def test_coverage_empty(self):
        """Empty result has 100% coverage (vacuously true)."""
        result = ExtractionResult()
        assert result.coverage == 1.0
