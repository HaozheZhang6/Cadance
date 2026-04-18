"""Tests for mech adapter - ops program parsing and object ref generation."""

from verifier_core.adapters.mech import (
    MechOperation,
    OpParameter,
    OpsProgram,
    build_feature_ref,
    build_op_ref,
    build_part_ref,
    create_finding_from_op,
    create_unknown_from_op,
)
from verifier_core.models import Severity


class TestOpParameter:
    """Tests for OpParameter."""

    def test_from_dict(self):
        d = {"name": "diameter", "value": 5.0, "unit": "mm", "inferred": False}
        param = OpParameter.from_dict(d)
        assert param.name == "diameter"
        assert param.value == 5.0
        assert param.unit == "mm"
        assert param.inferred is False

    def test_from_dict_minimal(self):
        d = {"name": "depth", "value": 10}
        param = OpParameter.from_dict(d)
        assert param.name == "depth"
        assert param.value == 10
        assert param.unit is None
        assert param.inferred is False

    def test_to_dict(self):
        param = OpParameter(name="radius", value=2.0, unit="mm", inferred=True)
        d = param.to_dict()
        assert d["name"] == "radius"
        assert d["value"] == 2.0
        assert d["unit"] == "mm"
        assert d["inferred"] is True


class TestMechOperation:
    """Tests for MechOperation."""

    def test_from_dict(self):
        d = {
            "primitive": "hole",
            "description": "Mounting hole",
            "confidence": 0.9,
            "dependencies": [0],
            "parameters": [
                {"name": "diameter", "value": 5.0, "unit": "mm"},
                {"name": "depth", "value": 10, "unit": "mm"},
            ],
        }
        op = MechOperation.from_dict(d)
        assert op.primitive == "hole"
        assert op.description == "Mounting hole"
        assert op.confidence == 0.9
        assert op.dependencies == [0]
        assert len(op.parameters) == 2

    def test_get_param(self):
        op = MechOperation(
            primitive="hole",
            parameters=[
                OpParameter(name="diameter", value=5.0, unit="mm"),
                OpParameter(name="depth", value=10, unit="mm"),
            ],
        )
        assert op.get_param("diameter") == 5.0
        assert op.get_param("depth") == 10
        assert op.get_param("missing") is None
        assert op.get_param("missing", 99) == 99

    def test_get_param_with_unit(self):
        op = MechOperation(
            primitive="hole",
            parameters=[OpParameter(name="diameter", value=5.0, unit="mm")],
        )
        val, unit = op.get_param_with_unit("diameter")
        assert val == 5.0
        assert unit == "mm"

    def test_is_hole(self):
        assert MechOperation(primitive="hole").is_hole()
        assert MechOperation(primitive="hole_counterbore").is_hole()
        assert MechOperation(primitive="hole_countersink").is_hole()
        assert MechOperation(primitive="hole_tapped").is_hole()
        assert not MechOperation(primitive="box").is_hole()
        assert not MechOperation(primitive="fillet").is_hole()


class TestMechOperationSourceSpecIds:
    """Tests for MechOperation.source_spec_ids traceability."""

    def test_default_empty(self):
        op = MechOperation(primitive="hole")
        assert op.source_spec_ids == []

    def test_from_dict_parses(self):
        d = {
            "primitive": "hole",
            "parameters": [],
            "source_spec_ids": ["S1.1.1", "S2.1"],
        }
        op = MechOperation.from_dict(d)
        assert op.source_spec_ids == ["S1.1.1", "S2.1"]

    def test_from_dict_default_empty(self):
        d = {"primitive": "hole", "parameters": []}
        op = MechOperation.from_dict(d)
        assert op.source_spec_ids == []

    def test_to_dict_omits_when_empty(self):
        op = MechOperation(primitive="hole")
        d = op.to_dict()
        assert "source_spec_ids" not in d

    def test_to_dict_includes_when_set(self):
        op = MechOperation(primitive="hole", source_spec_ids=["S1.1.1"])
        d = op.to_dict()
        assert d["source_spec_ids"] == ["S1.1.1"]


class TestOpsProgram:
    """Tests for OpsProgram parsing."""

    def test_from_dict(self):
        d = {
            "original_intent": "Create a bracket",
            "overall_confidence": 0.95,
            "ambiguities": ["unclear dimension"],
            "assumptions": ["aluminum material"],
            "operations": [
                {"primitive": "box", "parameters": []},
                {"primitive": "hole", "parameters": []},
            ],
        }
        prog = OpsProgram.from_dict(d, part_id="bracket")
        assert prog.original_intent == "Create a bracket"
        assert prog.overall_confidence == 0.95
        assert len(prog.ambiguities) == 1
        assert len(prog.assumptions) == 1
        assert len(prog.operations) == 2
        assert prog.part_id == "bracket"

    def test_from_json(self):
        json_str = '{"operations": [{"primitive": "cylinder"}]}'
        prog = OpsProgram.from_json(json_str, part_id="test")
        assert len(prog.operations) == 1
        assert prog.operations[0].primitive == "cylinder"

    def test_get_holes(self):
        prog = OpsProgram(
            operations=[
                MechOperation(primitive="box"),
                MechOperation(primitive="hole"),
                MechOperation(primitive="fillet"),
                MechOperation(primitive="hole_counterbore"),
            ]
        )
        holes = prog.get_holes()
        assert len(holes) == 2
        assert holes[0][0] == 1  # index
        assert holes[1][0] == 3  # index

    def test_get_fillets(self):
        prog = OpsProgram(
            operations=[
                MechOperation(primitive="box"),
                MechOperation(primitive="fillet"),
                MechOperation(primitive="hole"),
                MechOperation(primitive="fillet"),
            ]
        )
        fillets = prog.get_fillets()
        assert len(fillets) == 2
        assert fillets[0][0] == 1
        assert fillets[1][0] == 3


class TestObjectRefBuilding:
    """Tests for object reference building."""

    def test_build_op_ref(self):
        ref = build_op_ref("bracket", 0)
        assert ref == "mech://part/bracket/op/0"

    def test_build_feature_ref(self):
        ref = build_feature_ref("bracket", "hole", 1)
        assert ref == "mech://part/bracket/feature/hole/1"

    def test_build_part_ref(self):
        ref = build_part_ref("bracket")
        assert ref == "mech://part/bracket"

    def test_op_ref_stability(self):
        """Object refs should be deterministic."""
        ref1 = build_op_ref("mypart", 5)
        ref2 = build_op_ref("mypart", 5)
        assert ref1 == ref2


class TestFindingCreation:
    """Tests for creating findings from operations."""

    def test_create_finding_from_op(self):
        prog = OpsProgram(
            part_id="bracket",
            operations=[
                MechOperation(primitive="box"),
                MechOperation(primitive="hole", description="Small hole"),
            ],
        )
        finding = create_finding_from_op(
            prog,
            op_index=1,
            rule_id="mech.hole_min_diameter",
            severity=Severity.ERROR,
            message="Hole too small",
            measured_value={"value": 0.3, "unit": "mm"},
            limit={"value": 0.5, "unit": "mm"},
        )
        assert finding.rule_id == "mech.hole_min_diameter"
        assert finding.severity == Severity.ERROR
        assert finding.object_ref == "mech://part/bracket/op/1"
        assert finding.measured_value == {"value": 0.3, "unit": "mm"}
        assert finding.raw["primitive"] == "hole"

    def test_create_finding_with_feature_type(self):
        prog = OpsProgram(
            part_id="test",
            operations=[MechOperation(primitive="hole")],
        )
        finding = create_finding_from_op(
            prog,
            op_index=0,
            rule_id="test.rule",
            severity=Severity.WARN,
            message="Test",
            feature_type="hole",
        )
        assert finding.object_ref == "mech://part/test/feature/hole/0"


class TestUnknownCreation:
    """Tests for creating unknowns from operations."""

    def test_create_unknown_from_op(self):
        prog = OpsProgram(
            part_id="part1",
            operations=[MechOperation(primitive="hole")],
        )
        unknown = create_unknown_from_op(
            prog,
            op_index=0,
            summary="Missing diameter",
            impact="Cannot verify hole",
            resolution_plan="Add diameter param",
            rule_id="mech.hole_min_diameter",
        )
        assert unknown.summary == "Missing diameter"
        assert unknown.object_ref == "mech://part/part1/op/0"
        assert unknown.created_by_rule_id == "mech.hole_min_diameter"

    def test_create_finding_threads_source_spec_ids(self):
        """create_finding_from_op should pass op.source_spec_ids to Finding."""
        prog = OpsProgram(
            part_id="bracket",
            operations=[
                MechOperation(
                    primitive="hole",
                    description="M6 hole",
                    source_spec_ids=["S3.1.1"],
                ),
            ],
        )
        finding = create_finding_from_op(
            prog,
            op_index=0,
            rule_id="mech.hole_min_diameter",
            severity=Severity.INFO,
            message="OK",
        )
        assert finding.source_spec_ids == ["S3.1.1"]

    def test_create_finding_empty_source_spec_ids(self):
        """Finding gets empty list when op has no source_spec_ids."""
        prog = OpsProgram(
            part_id="bracket",
            operations=[MechOperation(primitive="hole")],
        )
        finding = create_finding_from_op(
            prog,
            op_index=0,
            rule_id="mech.test",
            severity=Severity.INFO,
            message="OK",
        )
        assert finding.source_spec_ids == []

    def test_create_unknown_threads_source_spec_ids(self):
        """create_unknown_from_op should pass op.source_spec_ids to Unknown."""
        prog = OpsProgram(
            part_id="bracket",
            operations=[
                MechOperation(
                    primitive="rib",
                    source_spec_ids=["S1.1.1", "S2.1.1"],
                ),
            ],
        )
        unknown = create_unknown_from_op(
            prog,
            op_index=0,
            summary="Missing param",
            impact="Cannot verify",
            resolution_plan="Add param",
        )
        assert unknown.source_spec_ids == ["S1.1.1", "S2.1.1"]

    def test_create_unknown_empty_source_spec_ids(self):
        """Unknown gets empty list when op has no source_spec_ids."""
        prog = OpsProgram(
            part_id="bracket",
            operations=[MechOperation(primitive="hole")],
        )
        unknown = create_unknown_from_op(
            prog,
            op_index=0,
            summary="Missing",
            impact="Impact",
            resolution_plan="Plan",
        )
        assert unknown.source_spec_ids == []
