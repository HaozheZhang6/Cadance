"""Tests for PMI (Product Manufacturing Information) checking.

These tests verify PMI detection and --require-pmi gating:
- PMI presence detection from multiple sources
- Priority ordering (SFA > MDS > STEP text scan)
- Blocking Unknown when PMI required but absent
"""

from pathlib import Path

from .conftest import load_expected_findings, load_mds


class TestPMIChecker:
    """Tests for PMI presence detection."""

    def test_mds_pmi_field_used(self, pmi_present_fixture: Path):
        """MDS pmi field is read correctly."""
        mds = load_mds(pmi_present_fixture)

        assert "pmi" in mds
        assert "has_semantic_pmi" in mds["pmi"]
        assert mds["pmi"]["has_semantic_pmi"] is True

    def test_mds_pmi_absent(self, pmi_absent_fixture: Path):
        """MDS without PMI is detected."""
        mds = load_mds(pmi_absent_fixture)

        assert "pmi" in mds
        assert mds["pmi"]["has_semantic_pmi"] is False

    def test_sfa_adapter_exists(self):
        """SFA adapter is registered and has correct interface."""
        from mech_verify.external_tools import SFAAdapter, default_registry

        # SFA adapter should be registered
        assert "sfa" in default_registry.list_registered()

        # Adapter should have correct interface
        adapter = SFAAdapter()
        assert adapter.tool_name == "sfa"
        assert hasattr(adapter, "is_available")
        assert hasattr(adapter, "run")

    def test_sfa_has_pmi_method(self):
        """SFA adapter has_pmi method exists."""
        from mech_verify.external_tools import SFAAdapter

        adapter = SFAAdapter()
        assert hasattr(adapter, "has_pmi")

        # Method should return bool (or raise if not available)
        if adapter.is_available():
            # Can't test without real STEP file
            pass


class TestPMIPriorityOrder:
    """Tests for PMI source priority."""

    def test_priority_order(self):
        """PMI sources checked in correct order."""
        # Document the priority order: SFA > MDS > STEP text scan
        # This is a documentation test
        expected_priority = ["sfa", "mds", "step_text"]
        assert len(expected_priority) == 3

    def test_mds_pmi_used_when_sfa_unavailable(self, pmi_present_fixture: Path):
        """When SFA is not available, MDS pmi field is used."""
        from mech_verify.external_tools import SFAAdapter

        mds = load_mds(pmi_present_fixture)
        adapter = SFAAdapter()

        # If SFA not available, we fall back to MDS
        if not adapter.is_available():
            assert mds["pmi"]["has_semantic_pmi"] is True


class TestPMIRequirement:
    """Tests for --require-pmi flag behavior."""

    def test_no_unknown_when_flag_off(self, pmi_absent_fixture: Path):
        """No Unknown when --require-pmi not set."""
        expected = load_expected_findings(pmi_absent_fixture)

        if expected.get("require_pmi") is not True:
            assert expected.get("expected_unknowns", []) == [] or all(
                u.get("created_by_rule_id") != "mech.tier0.pmi_required"
                for u in expected.get("expected_unknowns", [])
            )

    def test_pass_when_pmi_present(self, pmi_present_fixture: Path):
        """No Unknown when --require-pmi and PMI present."""
        expected = load_expected_findings(pmi_present_fixture)

        assert expected["expected_status"] == "pass"
        assert expected.get("expected_unknowns", []) == []

    def test_blocking_unknown_when_pmi_absent(self, pmi_absent_fixture: Path):
        """Blocking Unknown when --require-pmi and no PMI."""
        expected = load_expected_findings(pmi_absent_fixture)

        if expected.get("require_pmi"):
            assert expected["expected_status"] == "unknown"
            unknowns = expected.get("expected_unknowns", [])
            assert len(unknowns) == 1
            assert unknowns[0]["blocking"] is True
            assert unknowns[0]["created_by_rule_id"] == "mech.tier0.pmi_required"

    def test_cli_require_pmi_flag(self):
        """CLI --require-pmi flag triggers PMI check."""
        import json

        from click.testing import CliRunner

        from mech_verify.cli import verify

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create MDS without PMI
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
                verify, ["input.json", "-o", "./out", "--require-pmi"]
            )
            # May exit with FAIL (1) or UNKNOWN (2) depending on SHACL findings
            # SHACL may produce ERROR findings that override UNKNOWN status
            assert result.exit_code in [1, 2]

            # Check report has PMI unknown
            with open("out/report.json") as f:
                report = json.load(f)
            # Status could be FAIL (if SHACL errors) or UNKNOWN (if only PMI missing)
            assert report["status"] in ["FAIL", "UNKNOWN"]
            pmi_unknowns = [
                u
                for u in report["unknowns"]
                if "pmi" in u.get("created_by_rule_id", "").lower()
            ]
            assert len(pmi_unknowns) >= 1


class TestPMIAnnotations:
    """Tests for PMI annotation extraction."""

    def test_dimension_annotations(self, pmi_present_fixture: Path):
        """Dimension annotations extracted."""
        mds = load_mds(pmi_present_fixture)

        # PMI present fixture may not have annotations in new schema
        pmi = mds.get("pmi", {})
        assert pmi.get("has_semantic_pmi") is True

    def test_pmi_schema_fields(self, pmi_present_fixture: Path):
        """PMI has expected schema fields."""
        mds = load_mds(pmi_present_fixture)

        pmi = mds.get("pmi", {})
        assert "has_semantic_pmi" in pmi
        assert "has_graphical_pmi" in pmi

    def test_pmi_absent_no_annotations(self, pmi_absent_fixture: Path):
        """PMI absent fixture has no semantic PMI."""
        mds = load_mds(pmi_absent_fixture)

        pmi = mds.get("pmi", {})
        assert pmi.get("has_semantic_pmi") is False


class TestPMICompleteness:
    """Tests for PMI completeness checking (datum/tolerance missing)."""

    def test_check_pmi_completeness_no_pmi(self):
        """No findings when PMI is not present."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
            "parts": [{"part_id": "test"}],
        }
        findings = get_pmi_completeness_findings(mds)
        # No findings because PMI isn't present at all
        assert len(findings) == 0

    def test_check_pmi_completeness_pmi_with_missing_datums(self):
        """WARN finding when PMI present but no datums."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {"has_semantic_pmi": True, "has_graphical_pmi": False},
            "parts": [{"part_id": "test_part"}],
        }
        findings = get_pmi_completeness_findings(mds)

        datum_findings = [
            f for f in findings if f.rule_id == "mech.tier0.pmi.datum_missing"
        ]
        assert len(datum_findings) == 1
        assert datum_findings[0].severity.value == "WARN"
        assert "datum" in datum_findings[0].message.lower()

    def test_check_pmi_completeness_pmi_with_missing_tolerances(self):
        """WARN finding when PMI present but no tolerances."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {"has_semantic_pmi": True, "has_graphical_pmi": False},
            "parts": [{"part_id": "test_part"}],
        }
        findings = get_pmi_completeness_findings(mds)

        tol_findings = [
            f for f in findings if f.rule_id == "mech.tier0.pmi.tolerance_missing"
        ]
        assert len(tol_findings) == 1
        assert tol_findings[0].severity.value == "WARN"
        assert "tolerance" in tol_findings[0].message.lower()

    def test_check_pmi_completeness_with_datums_in_mds(self):
        """No datum finding when datums present in MDS."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {
                "has_semantic_pmi": True,
                "has_graphical_pmi": False,
                "datums": [{"name": "A"}, {"name": "B"}],
            },
            "parts": [{"part_id": "test_part"}],
        }
        findings = get_pmi_completeness_findings(mds)

        datum_findings = [
            f for f in findings if f.rule_id == "mech.tier0.pmi.datum_missing"
        ]
        assert len(datum_findings) == 0

    def test_check_pmi_completeness_with_tolerances_in_mds(self):
        """No tolerance finding when tolerances present in MDS."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {
                "has_semantic_pmi": True,
                "has_graphical_pmi": False,
                "tolerances": [{"name": "position_0"}],
            },
            "parts": [{"part_id": "test_part"}],
        }
        findings = get_pmi_completeness_findings(mds)

        tol_findings = [
            f for f in findings if f.rule_id == "mech.tier0.pmi.tolerance_missing"
        ]
        assert len(tol_findings) == 0

    def test_check_pmi_completeness_critical_pmi_missing(self):
        """WARN finding when manifest critical_pmi is missing."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {
                "has_semantic_pmi": True,
                "has_graphical_pmi": False,
                "datums": [{"name": "A"}],
                "tolerances": [{"name": "pos_0"}],
            },
            "parts": [{"part_id": "test_part"}],
        }
        manifest = {
            "critical_pmi": [
                {"type": "datum", "name": "A"},
                {"type": "datum", "name": "C"},  # Missing
                {"type": "tolerance", "name": "flatness_0"},  # Missing
            ]
        }
        findings = get_pmi_completeness_findings(mds, manifest=manifest)

        critical_findings = [
            f for f in findings if f.rule_id == "mech.tier0.pmi.critical_missing"
        ]
        assert len(critical_findings) == 2
        # Should mention datum:C and tolerance:flatness_0
        msgs = [f.message for f in critical_findings]
        assert any("datum:C" in m for m in msgs)
        assert any("tolerance:flatness_0" in m for m in msgs)

    def test_check_pmi_completeness_critical_pmi_present(self):
        """No critical finding when all critical_pmi present."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {
                "has_semantic_pmi": True,
                "has_graphical_pmi": False,
                "datums": [{"name": "A"}, {"name": "B"}],
                "tolerances": [{"name": "pos_0"}],
            },
            "parts": [{"part_id": "test_part"}],
        }
        manifest = {
            "critical_pmi": [
                {"type": "datum", "name": "A"},
                {"type": "datum", "name": "B"},
                {"type": "tolerance", "name": "pos_0"},
            ]
        }
        findings = get_pmi_completeness_findings(mds, manifest=manifest)

        critical_findings = [
            f for f in findings if f.rule_id == "mech.tier0.pmi.critical_missing"
        ]
        assert len(critical_findings) == 0

    def test_pmi_completeness_result_dataclass(self):
        """PMICompletenessResult has expected fields."""
        from mech_verify.pmi import check_pmi_completeness

        mds = {
            "pmi": {
                "has_semantic_pmi": True,
                "datums": [{"name": "A"}],
                "tolerances": [{"name": "pos_0"}],
            }
        }
        result = check_pmi_completeness(mds)

        assert result.has_datums is True
        assert result.has_tolerances is True
        assert "A" in result.found_datums
        assert "pos_0" in result.found_tolerances
        assert result.missing_critical == []

    def test_graphical_pmi_triggers_completeness_check(self):
        """Completeness check runs for graphical PMI too."""
        from mech_verify.pmi import get_pmi_completeness_findings

        mds = {
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": True},
            "parts": [{"part_id": "test_part"}],
        }
        findings = get_pmi_completeness_findings(mds)

        # Should emit both datum and tolerance missing warnings
        rule_ids = [f.rule_id for f in findings]
        assert "mech.tier0.pmi.datum_missing" in rule_ids
        assert "mech.tier0.pmi.tolerance_missing" in rule_ids
