"""Tests for post-canonicalizer module."""

import pytest

from src.agents.canonicalizer import (
    CanonicalMapping,
    UnmappedParam,
    canonicalize_spec_params,
)
from src.agents.schemas import (
    AssumptionOutput,
    GoalOutput,
    GRSTreeOutput,
    RequirementOutput,
    SpecOutput,
    SpecParameterOutput,
)
from src.verification.semantic.symbol_table import SymbolTable


@pytest.fixture
def symbol_table():
    """Default symbol table with canonical params."""
    return SymbolTable()


@pytest.fixture
def simple_tree():
    """Simple GRS tree with one spec and params."""
    return GRSTreeOutput(
        goals=[
            GoalOutput(
                id="G1",
                description="Support 5kg payload",
                goal_type="ACHIEVE",
                requirements=[
                    RequirementOutput(
                        id="R1.1",
                        statement="System SHALL support payload mass",
                        specifications=[
                            SpecOutput(
                                id="S1.1.1",
                                description="Payload mass spec",
                                parameters=[
                                    SpecParameterOutput(
                                        name="mass",
                                        value="5.0",
                                        unit="kg",
                                    ),
                                    SpecParameterOutput(
                                        name="thickness",
                                        value="2.0",
                                        unit="mm",
                                    ),
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
        assumptions=[
            AssumptionOutput(
                id="A1",
                text="Standard gravity",
                confidence="Confident",
                reasoning="Earth",
                affects="S1.1.1",
            )
        ],
    )


class TestCanonicalizeSpecParams:
    def test_maps_known_alias_to_canonical(self, symbol_table, simple_tree):
        """mass -> payload_mass, thickness -> plate_thickness."""
        new_tree, mappings, unmapped = canonicalize_spec_params(
            simple_tree, symbol_table
        )

        # Check mappings
        assert len(mappings) == 2
        mapping_dict = {m.original: m.canonical for m in mappings}
        assert mapping_dict["mass"] == "payload_mass"
        assert mapping_dict["thickness"] == "plate_thickness"

        # Check tree was updated
        params = new_tree.goals[0].requirements[0].specifications[0].parameters
        assert params[0].name == "payload_mass"
        assert params[1].name == "plate_thickness"

        # Check no unmapped
        assert len(unmapped) == 0

    def test_original_tree_not_mutated(self, symbol_table, simple_tree):
        """Deep copy preserves original."""
        original_name = (
            simple_tree.goals[0].requirements[0].specifications[0].parameters[0].name
        )
        assert original_name == "mass"

        new_tree, _, _ = canonicalize_spec_params(simple_tree, symbol_table)

        # Original unchanged
        assert (
            simple_tree.goals[0].requirements[0].specifications[0].parameters[0].name
            == "mass"
        )
        # New tree updated
        assert (
            new_tree.goals[0].requirements[0].specifications[0].parameters[0].name
            == "payload_mass"
        )

    def test_unmapped_param_returns_suggestions(self, symbol_table):
        """Unknown param gets fuzzy suggestions."""
        tree = GRSTreeOutput(
            goals=[
                GoalOutput(
                    id="G1",
                    description="Test",
                    goal_type="ACHIEVE",
                    requirements=[
                        RequirementOutput(
                            id="R1.1",
                            statement="SHALL do something",
                            specifications=[
                                SpecOutput(
                                    id="S1.1.1",
                                    description="Test spec",
                                    parameters=[
                                        SpecParameterOutput(
                                            name="weird_param_xyz",
                                            value="10",
                                            unit="kg",
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
            assumptions=[],
        )

        _, mappings, unmapped = canonicalize_spec_params(tree, symbol_table)

        assert len(mappings) == 0
        assert len(unmapped) == 1
        assert unmapped[0].name == "weird_param_xyz"
        assert unmapped[0].spec_id == "S1.1.1"

    def test_unmapped_warning_format(self):
        """UnmappedParam.to_warning() formatting."""
        u = UnmappedParam(
            name="weird_param",
            unit="kg",
            spec_id="S1.1.1",
            suggestions=["payload_mass"],
        )
        assert "UNMAPPED_REQUIRED" in u.to_warning()
        assert "suggested: payload_mass" in u.to_warning()

        u_no_suggest = UnmappedParam(
            name="weird_param",
            unit="kg",
            spec_id="S1.1.1",
            suggestions=[],
        )
        assert "no match" in u_no_suggest.to_warning()

    def test_empty_tree_handled_gracefully(self, symbol_table):
        """Empty goals/specs don't crash."""
        tree = GRSTreeOutput(goals=[], assumptions=[])
        new_tree, mappings, unmapped = canonicalize_spec_params(tree, symbol_table)

        assert new_tree.goals == []
        assert mappings == []
        assert unmapped == []

    def test_canonical_name_already_used_no_mapping(self, symbol_table):
        """If param is already canonical, no mapping recorded."""
        tree = GRSTreeOutput(
            goals=[
                GoalOutput(
                    id="G1",
                    description="Test",
                    goal_type="ACHIEVE",
                    requirements=[
                        RequirementOutput(
                            id="R1.1",
                            statement="SHALL do something",
                            specifications=[
                                SpecOutput(
                                    id="S1.1.1",
                                    description="Test spec",
                                    parameters=[
                                        SpecParameterOutput(
                                            name="payload_mass",
                                            value="5.0",
                                            unit="kg",
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
            assumptions=[],
        )

        _, mappings, unmapped = canonicalize_spec_params(tree, symbol_table)

        # Already canonical, so no mapping
        assert len(mappings) == 0
        assert len(unmapped) == 0

    def test_multiple_specs_processed(self, symbol_table):
        """All specs across all goals processed."""
        tree = GRSTreeOutput(
            goals=[
                GoalOutput(
                    id="G1",
                    description="Goal 1",
                    goal_type="ACHIEVE",
                    requirements=[
                        RequirementOutput(
                            id="R1.1",
                            statement="SHALL support",
                            specifications=[
                                SpecOutput(
                                    id="S1.1.1",
                                    description="Spec 1",
                                    parameters=[
                                        SpecParameterOutput(
                                            name="mass", value="5", unit="kg"
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                ),
                GoalOutput(
                    id="G2",
                    description="Goal 2",
                    goal_type="MAINTAIN",
                    requirements=[
                        RequirementOutput(
                            id="R2.1",
                            statement="SHALL maintain",
                            specifications=[
                                SpecOutput(
                                    id="S2.1.1",
                                    description="Spec 2",
                                    parameters=[
                                        SpecParameterOutput(
                                            name="diameter", value="10", unit="mm"
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                ),
            ],
            assumptions=[],
        )

        _, mappings, _ = canonicalize_spec_params(tree, symbol_table)

        # Both aliases mapped
        assert len(mappings) == 2
        mapping_dict = {m.original: m.canonical for m in mappings}
        assert mapping_dict["mass"] == "payload_mass"
        assert mapping_dict["diameter"] == "hole_diameter"

    def test_preset_quantity_id_not_overwritten(self, symbol_table):
        """Pre-set quantity_id preserved during canonicalization."""
        tree = GRSTreeOutput(
            goals=[
                GoalOutput(
                    id="G1",
                    description="Test",
                    goal_type="ACHIEVE",
                    requirements=[
                        RequirementOutput(
                            id="R1.1",
                            statement="SHALL support",
                            specifications=[
                                SpecOutput(
                                    id="S1.1.1",
                                    description="Spec",
                                    parameters=[
                                        SpecParameterOutput(
                                            name="mass",
                                            value="5.0",
                                            unit="kg",
                                            quantity_id="custom_mass_id",
                                        ),
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
            assumptions=[],
        )

        new_tree, mappings, _ = canonicalize_spec_params(tree, symbol_table)
        param = new_tree.goals[0].requirements[0].specifications[0].parameters[0]
        # Name updated to canonical
        assert param.name == "payload_mass"
        # quantity_id preserved (not overwritten with canonical name)
        assert param.quantity_id == "custom_mass_id"


class TestCanonicalMapping:
    def test_dataclass_fields(self):
        """CanonicalMapping has expected fields."""
        m = CanonicalMapping(original="mass", canonical="payload_mass", spec_id="S1.1")
        assert m.original == "mass"
        assert m.canonical == "payload_mass"
        assert m.spec_id == "S1.1"
