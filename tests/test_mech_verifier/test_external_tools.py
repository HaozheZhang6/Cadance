"""
Tests for external tool adapters.

These tests verify:
1. Adapter protocol compliance
2. Availability detection (CI-safe)
3. Output parsing (always runs - uses saved sample outputs)
4. Registry behavior
"""

import json
from unittest.mock import patch

import pytest

from mech_verify.external_tools import (
    ExternalToolAdapter,
    FreeCADAdapter,
    SFAAdapter,
    ToolInvocationResult,
    ToolRegistry,
    create_tool_missing_unknown,
    default_registry,
    get_available_tools,
    get_unavailable_tools,
    parse_freecad_output,
    parse_sfa_csv,
    parse_sfa_stdout,
    run_external_tools,
)
from verifier_core.models import Severity


class TestToolInvocationResult:
    """Tests for ToolInvocationResult dataclass."""

    def test_basic_creation(self):
        result = ToolInvocationResult(
            tool_name="test-tool",
            command=["test", "-v"],
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100.5,
        )
        assert result.tool_name == "test-tool"
        assert result.command == ["test", "-v"]
        assert result.exit_code == 0
        assert result.duration_ms == 100.5
        assert result.invocation_id is not None

    def test_to_dict(self):
        result = ToolInvocationResult(
            tool_name="test",
            command=["cmd"],
            exit_code=1,
            stdout="out",
            stderr="err",
            duration_ms=50.0,
            invocation_id="test-123",
        )
        d = result.to_dict()
        assert d["tool_name"] == "test"
        assert d["exit_code"] == 1
        assert d["invocation_id"] == "test-123"


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get(self):
        registry = ToolRegistry()
        adapter = FreeCADAdapter()
        registry.register(adapter)
        assert registry.get("freecad") is adapter

    def test_list_registered(self):
        registry = ToolRegistry()
        registry.register(FreeCADAdapter())
        registry.register(SFAAdapter())
        names = registry.list_registered()
        assert "freecad" in names
        assert "sfa" in names

    def test_unregister(self):
        registry = ToolRegistry()
        registry.register(FreeCADAdapter())
        registry.unregister("freecad")
        assert registry.get("freecad") is None

    def test_get_available_empty_when_no_tools(self):
        """Test that get_available returns empty when tools not installed."""
        registry = ToolRegistry()
        registry.register(FreeCADAdapter())
        # FreeCAD likely not installed in CI
        # This should not raise, just return empty or filtered list
        available = registry.get_available()
        assert isinstance(available, list)

    def test_run_all_empty_when_disabled(self):
        """Test run_all doesn't crash even when no tools available."""
        registry = ToolRegistry()
        results = registry.run_all("/nonexistent/file.step")
        assert results == []


class TestFreeCADAdapter:
    """Tests for FreeCAD adapter."""

    def test_tool_name(self):
        adapter = FreeCADAdapter()
        assert adapter.tool_name == "freecad"

    def test_is_available_returns_bool(self):
        """is_available should return bool, not raise."""
        adapter = FreeCADAdapter()
        result = adapter.is_available()
        assert isinstance(result, bool)

    def test_run_raises_for_missing_file(self):
        """run should raise FileNotFoundError for missing artifact."""
        adapter = FreeCADAdapter()
        # Mock is_available to return True
        with patch.object(adapter, "is_available", return_value=True):
            with pytest.raises(FileNotFoundError):
                adapter.run("/nonexistent/file.step")


class TestFreeCADOutputParsing:
    """Tests for FreeCAD output parsing - always run (no FreeCAD required)."""

    def test_parse_valid_geometry(self):
        """Parse output indicating valid geometry."""
        output = json.dumps(
            {
                "input_file": "test.step",
                "valid": True,
                "errors": [],
                "warnings": [],
                "stats": {
                    "num_solids": 1,
                    "num_faces": 6,
                    "num_edges": 12,
                },
            }
        )
        findings = parse_freecad_output(output, "test.step")
        assert len(findings) == 1
        assert findings[0].rule_id == "freecad.check_geometry.valid"
        assert findings[0].severity == Severity.INFO
        assert "valid" in findings[0].message.lower()

    def test_parse_invalid_geometry(self):
        """Parse output with geometry errors."""
        output = json.dumps(
            {
                "input_file": "test.step",
                "valid": False,
                "errors": [
                    {
                        "type": "invalid_shape",
                        "message": "Shape.isValid() returned False",
                    },
                    {"type": "geometry_error", "message": "Self-intersection detected"},
                ],
                "warnings": [],
                "stats": {},
            }
        )
        findings = parse_freecad_output(output, "test.step")
        assert len(findings) >= 2
        # invalid_shape should be BLOCKER
        invalid_finding = next(f for f in findings if "invalid_shape" in f.rule_id)
        assert invalid_finding.severity == Severity.BLOCKER

    def test_parse_import_error(self):
        """Parse output with import error."""
        output = json.dumps(
            {
                "input_file": "bad.step",
                "valid": False,
                "errors": [
                    {"type": "import_error", "message": "Failed to import STEP file"},
                ],
                "warnings": [],
                "stats": {},
            }
        )
        findings = parse_freecad_output(output, "bad.step")
        assert len(findings) == 1
        assert "import_error" in findings[0].rule_id
        assert findings[0].severity == Severity.ERROR

    def test_parse_invalid_json(self):
        """Gracefully handle invalid JSON output."""
        findings = parse_freecad_output("not valid json", "test.step")
        assert len(findings) == 1
        assert "parse_error" in findings[0].rule_id
        assert findings[0].severity == Severity.ERROR

    def test_object_ref_construction(self):
        """Check object_ref is properly constructed."""
        output = json.dumps({"valid": True, "errors": [], "warnings": [], "stats": {}})
        findings = parse_freecad_output(output, "/path/to/my_part.step")
        assert findings[0].object_ref == "mech://part/my_part"


class TestSFAAdapter:
    """Tests for SFA adapter."""

    def test_tool_name(self):
        adapter = SFAAdapter()
        assert adapter.tool_name == "sfa"

    def test_is_available_returns_bool(self):
        """is_available should return bool, not raise."""
        adapter = SFAAdapter()
        result = adapter.is_available()
        assert isinstance(result, bool)

    def test_run_raises_for_missing_file(self):
        """run should raise FileNotFoundError for missing artifact."""
        adapter = SFAAdapter()
        with patch.object(adapter, "is_available", return_value=True):
            with pytest.raises(FileNotFoundError):
                adapter.run("/nonexistent/file.step")


class TestSFAOutputParsing:
    """Tests for SFA output parsing - always run (no SFA required)."""

    def test_parse_csv_with_errors(self):
        """Parse CSV with validation errors."""
        csv_content = """Entity,Type,Message,Severity
product_definition,PRODUCT_DEFINITION,"Missing name attribute",error
shape_representation,SHAPE_REPRESENTATION,"Recommended Practice not followed",warning
"""
        findings = parse_sfa_csv(csv_content, "test.step")
        assert len(findings) >= 2
        error_finding = next(f for f in findings if f.severity == Severity.ERROR)
        assert "Missing name" in error_finding.message

    def test_parse_csv_with_pmi(self):
        """Parse CSV with PMI-related messages."""
        csv_content = """Entity,Type,Message,Severity
datum,DATUM,"PMI datum feature 'A' found",info
tolerance,TOLERANCE,"PMI tolerance GD&T value",info
"""
        findings = parse_sfa_csv(csv_content, "test.step")
        pmi_findings = [f for f in findings if "pmi" in f.rule_id]
        assert len(pmi_findings) >= 2

    def test_parse_stdout_pmi_found(self):
        """Parse stdout indicating PMI presence."""
        stdout = """
STEP File Analyzer 4.0
Processing: test.step
PMI Representation data found
12345 entities processed
"""
        findings = parse_sfa_stdout(stdout, "test.step")
        pmi_finding = next(
            (f for f in findings if "representation_found" in f.rule_id), None
        )
        assert pmi_finding is not None
        assert pmi_finding.severity == Severity.INFO

    def test_parse_stdout_no_pmi(self):
        """Parse stdout indicating no PMI."""
        stdout = """
STEP File Analyzer 4.0
Processing: test.step
PMI not found
No geometric PMI
"""
        findings = parse_sfa_stdout(stdout, "test.step")
        no_pmi = [f for f in findings if "not_found" in f.rule_id or "no_" in f.rule_id]
        assert len(no_pmi) >= 1
        assert all(f.severity == Severity.WARN for f in no_pmi)

    def test_parse_stdout_syntax_error(self):
        """Parse stdout with STEP syntax errors."""
        stdout = """
STEP File Analyzer 4.0
SYNTAX ERROR at line 1234
"""
        findings = parse_sfa_stdout(stdout, "test.step")
        error_finding = next((f for f in findings if "syntax_error" in f.rule_id), None)
        assert error_finding is not None
        assert error_finding.severity == Severity.ERROR

    def test_parse_empty_csv(self):
        """Gracefully handle empty CSV."""
        findings = parse_sfa_csv("", "test.step")
        assert findings == []

    def test_object_ref_construction(self):
        """Check object_ref is properly constructed."""
        csv_content = """Entity,Type,Message,Severity
test,TEST,"Test message",info
"""
        findings = parse_sfa_csv(csv_content, "/path/to/bracket.step")
        assert findings[0].object_ref == "mech://part/bracket"


class TestIntegration:
    """Integration tests for external tools API."""

    def test_run_external_tools_disabled(self):
        """run_external_tools returns empty when disabled."""
        results = run_external_tools("/any/path.step", enabled=False)
        assert results == []

    def test_run_external_tools_enabled_but_unavailable(self):
        """run_external_tools gracefully handles unavailable tools."""
        # Even with enabled=True, if tools not installed, should not crash
        results = run_external_tools("/nonexistent.step", enabled=True)
        # Either empty or contains results from available tools
        assert isinstance(results, list)

    def test_get_available_tools_returns_list(self):
        """get_available_tools always returns list."""
        tools = get_available_tools()
        assert isinstance(tools, list)
        # All elements should be strings
        assert all(isinstance(t, str) for t in tools)

    def test_get_unavailable_tools_returns_list(self):
        """get_unavailable_tools always returns list."""
        tools = get_unavailable_tools()
        assert isinstance(tools, list)

    def test_create_tool_missing_unknown(self):
        """create_tool_missing_unknown creates proper Unknown."""
        unknown = create_tool_missing_unknown(
            "freecad",
            "/path/to/part.step",
            "geometry validation",
        )
        assert "freecad" in unknown.summary.lower()
        assert "geometry validation" in unknown.impact
        assert unknown.object_ref == "mech://part/part"
        assert unknown.created_by_rule_id == "external_tools.freecad.missing"

    def test_default_registry_has_adapters(self):
        """Default registry has FreeCAD and SFA registered."""
        names = default_registry.list_registered()
        assert "freecad" in names
        assert "sfa" in names


class TestProtocolCompliance:
    """Tests that adapters properly implement ExternalToolAdapter protocol."""

    @pytest.mark.parametrize("adapter_class", [FreeCADAdapter, SFAAdapter])
    def test_adapter_is_protocol_compliant(self, adapter_class):
        """Verify adapter implements protocol."""
        adapter = adapter_class()
        # Check protocol properties/methods exist
        assert hasattr(adapter, "tool_name")
        assert hasattr(adapter, "is_available")
        assert hasattr(adapter, "run")
        # tool_name should be string
        assert isinstance(adapter.tool_name, str)
        # is_available should be callable returning bool
        assert callable(adapter.is_available)
        result = adapter.is_available()
        assert isinstance(result, bool)

    @pytest.mark.parametrize("adapter_class", [FreeCADAdapter, SFAAdapter])
    def test_adapter_isinstance_check(self, adapter_class):
        """Verify isinstance check works with protocol."""
        adapter = adapter_class()
        assert isinstance(adapter, ExternalToolAdapter)


@pytest.mark.integration
class TestFreeCADIntegration:
    """Integration tests that actually run FreeCAD when available.

    These tests are skipped if FreeCAD is not installed.
    Run with: pytest -m integration
    """

    @pytest.fixture
    def freecad_adapter(self):
        adapter = FreeCADAdapter()
        if not adapter.is_available():
            pytest.skip("FreeCAD not installed")
        return adapter

    @pytest.fixture
    def simple_step_file(self, tmp_path):
        """Create a minimal STEP file for testing."""
        # Minimal valid STEP file structure (a simple cube-like entity)
        step_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Simple test file'),'2;1');
FILE_NAME('test.step','2024-01-01T00:00:00',('Author'),(''),'','','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
#1=SHAPE_DEFINITION_REPRESENTATION(#2,#3);
#2=PRODUCT_DEFINITION_SHAPE('',$,#4);
#3=SHAPE_REPRESENTATION('',(#5),#6);
#4=PRODUCT_DEFINITION('','',#7,#8);
#5=AXIS2_PLACEMENT_3D('',#9,$,$);
#6=(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#10))GLOBAL_UNIT_ASSIGNED_CONTEXT((#11,#12,#13))REPRESENTATION_CONTEXT('','3D'));
#7=PRODUCT_DEFINITION_FORMATION('',$,#14);
#8=PRODUCT_DEFINITION_CONTEXT('',#15,'design');
#9=CARTESIAN_POINT('',(0.,0.,0.));
#10=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-06),#11,'','');
#11=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));
#12=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));
#13=(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());
#14=PRODUCT('test','test','',(#16));
#15=APPLICATION_CONTEXT('automotive design');
#16=PRODUCT_CONTEXT('',#15,'mechanical');
ENDSEC;
END-ISO-10303-21;
"""
        step_file = tmp_path / "test_cube.step"
        step_file.write_text(step_content)
        return step_file

    def test_freecad_runs_on_step_file(self, freecad_adapter, simple_step_file):
        """FreeCAD adapter can process a STEP file."""
        invocation, findings, evidence = freecad_adapter.run(str(simple_step_file))

        assert invocation.tool_name == "freecad"
        assert invocation.exit_code is not None
        assert isinstance(findings, list)
        assert isinstance(evidence, list)

    def test_freecad_produces_findings(self, freecad_adapter, simple_step_file):
        """FreeCAD produces meaningful findings."""
        invocation, findings, evidence = freecad_adapter.run(str(simple_step_file))

        # Should have at least one finding (valid or error)
        assert len(findings) >= 1

        # Each finding should have required fields
        for f in findings:
            assert f.rule_id is not None
            assert f.severity is not None
            assert f.message is not None

    def test_freecad_produces_evidence(self, freecad_adapter, simple_step_file):
        """FreeCAD produces evidence artifacts."""
        invocation, findings, evidence = freecad_adapter.run(str(simple_step_file))

        # Should have at least tool invocation evidence
        assert len(evidence) >= 1


@pytest.mark.integration
class TestCLIWithExternalTools:
    """Integration tests for CLI with external tools enabled."""

    @pytest.fixture
    def has_external_tools(self):
        """Skip if no external tools available."""
        freecad = FreeCADAdapter()
        sfa = SFAAdapter()
        if not freecad.is_available() and not sfa.is_available():
            pytest.skip("No external tools available")
        return True

    def test_cli_external_tools_flag(self, has_external_tools):
        """CLI --use-external-tools flag runs external adapters."""
        import json
        from pathlib import Path

        from click.testing import CliRunner

        from mech_verify.cli import verify

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create minimal MDS
            mds = {
                "schema_version": "mech.mds.v1",
                "domain": "mech",
                "units": {"length": "mm", "angle": "deg"},
                "parts": [
                    {
                        "part_id": "test",
                        "object_ref": "mech://part/test",
                        "mass_props": {"volume": 100.0},
                    }
                ],
                "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
            }
            Path("input.json").write_text(json.dumps(mds))

            result = runner.invoke(
                verify, ["input.json", "-o", "./out", "--use-external-tools"]
            )

            # Should complete (even if tools not available for JSON input)
            assert result.exit_code in [0, 1, 2]  # PASS, FAIL, or UNKNOWN

            # Check report has tool_invocations field
            report_path = Path("out/report.json")
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                assert "tool_invocations" in report
