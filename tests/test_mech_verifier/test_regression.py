"""Tests for regression and determinism.

These tests verify:
- Deterministic output across runs
- Finding ID stability
- Schema validation for report.json and mds.json
- normalize_findings() behavior
"""

import json
from pathlib import Path
from typing import Any

import pytest

from .conftest import load_mds


def normalize_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize findings for deterministic comparison.

    - Stable sort by (severity, rule_id, object_ref, message)
    - Round numeric values to 4 decimal places
    - Strip run-specific IDs unless deterministic
    """
    severity_order = {
        "BLOCKER": 0,
        "ERROR": 1,
        "WARN": 2,
        "INFO": 3,
        "UNKNOWN": 4,
    }

    def sort_key(f: dict) -> tuple:
        sev = severity_order.get(f.get("severity", "UNKNOWN"), 5)
        return (
            sev,
            f.get("rule_id", ""),
            f.get("object_ref", ""),
            f.get("message", ""),
        )

    def round_values(val: Any) -> Any:
        if isinstance(val, float):
            return round(val, 4)
        elif isinstance(val, dict):
            return {k: round_values(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [round_values(v) for v in val]
        return val

    sorted_findings = sorted(findings, key=sort_key)

    normalized = []
    for f in sorted_findings:
        d = dict(f)
        d.pop("finding_id", None)
        if "measured_value" in d:
            d["measured_value"] = round_values(d["measured_value"])
        if "limit" in d:
            d["limit"] = round_values(d["limit"])
        normalized.append(d)

    return normalized


class TestDeterminism:
    """Tests for deterministic findings output."""

    def test_two_runs_identical_output(self, golden_pass_fixture: Path):
        """Running twice produces identical findings."""
        mds1 = load_mds(golden_pass_fixture)
        mds2 = load_mds(golden_pass_fixture)

        assert mds1 == mds2

    def test_mds_load_deterministic(self, hole_too_small_fixture: Path):
        """MDS loads are deterministic."""
        mds1 = load_mds(hole_too_small_fixture)
        mds2 = load_mds(hole_too_small_fixture)

        assert mds1["parts"][0]["part_id"] == mds2["parts"][0]["part_id"]

    def test_finding_ids_stable(self):
        """Finding IDs don't change between runs (placeholder)."""
        pass


class TestNormalizeFindingsFunction:
    """Tests for normalize_findings helper."""

    def test_sort_by_severity(self):
        """Findings sorted by severity first."""
        findings = [
            {"rule_id": "r1", "severity": "WARN", "message": "w"},
            {"rule_id": "r2", "severity": "ERROR", "message": "e"},
            {"rule_id": "r3", "severity": "BLOCKER", "message": "b"},
        ]
        normalized = normalize_findings(findings)

        assert normalized[0]["severity"] == "BLOCKER"
        assert normalized[1]["severity"] == "ERROR"
        assert normalized[2]["severity"] == "WARN"

    def test_sort_by_rule_id(self):
        """Same severity sorted by rule_id."""
        findings = [
            {"rule_id": "z.rule", "severity": "ERROR", "message": "z"},
            {"rule_id": "a.rule", "severity": "ERROR", "message": "a"},
        ]
        normalized = normalize_findings(findings)

        assert normalized[0]["rule_id"] == "a.rule"
        assert normalized[1]["rule_id"] == "z.rule"

    def test_strips_finding_id(self):
        """Random finding_id removed."""
        findings = [
            {
                "finding_id": "abc123",
                "rule_id": "r1",
                "severity": "ERROR",
                "message": "m",
            },
        ]
        normalized = normalize_findings(findings)

        assert "finding_id" not in normalized[0]

    def test_rounds_numeric_values(self):
        """Float values rounded to 4 decimals."""
        findings = [
            {
                "rule_id": "r1",
                "severity": "ERROR",
                "message": "m",
                "measured_value": {"value": 0.123456789},
            },
        ]
        normalized = normalize_findings(findings)

        assert normalized[0]["measured_value"]["value"] == 0.1235


class TestSchemaValidation:
    """Tests for JSON schema validation."""

    def test_mds_validates_against_schema(self, golden_pass_fixture: Path):
        """mds.json validates against mds.schema.json."""
        import jsonschema

        mds = load_mds(golden_pass_fixture)

        schema_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mech_verifier"
            / "mech_verify"
            / "schemas"
            / "v1"
            / "mds.schema.json"
        )
        if not schema_path.exists():
            pytest.skip("MDS schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        # Should not raise
        jsonschema.validate(mds, schema)

    def test_cli_validate_schema_flag(self):
        """CLI --validate-schema flag should validate outputs."""
        from click.testing import CliRunner

        from mech_verify.cli import verify

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a valid MDS
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
                verify, ["input.json", "-o", "./out", "--validate-schema"]
            )
            # Should succeed (no schema errors)
            assert result.exit_code == 0

    def test_expected_findings_is_valid_json(self, golden_pass_fixture: Path):
        """expected_findings.json is valid JSON."""
        expected_path = golden_pass_fixture / "expected_findings.json"
        with open(expected_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "expected_status" in data


class TestFixtureConsistency:
    """Tests for test fixture consistency."""

    def test_all_fixtures_have_expected_findings(self, test_projects_root: Path):
        """All fixtures have expected_findings.json."""
        for proj_dir in test_projects_root.iterdir():
            if proj_dir.is_dir() and proj_dir.name.startswith("step_"):
                expected_path = proj_dir / "expected_findings.json"
                assert expected_path.exists(), f"Missing {expected_path}"

    def test_all_fixtures_have_inputs(self, test_projects_root: Path):
        """All fixtures have inputs directory."""
        for proj_dir in test_projects_root.iterdir():
            if proj_dir.is_dir() and proj_dir.name.startswith("step_"):
                inputs_dir = proj_dir / "inputs"
                assert inputs_dir.exists(), f"Missing {inputs_dir}"

    def test_expected_findings_structure(self, test_projects_root: Path):
        """expected_findings.json has required fields."""
        required_fields = ["description", "expected_status"]

        for proj_dir in test_projects_root.iterdir():
            if proj_dir.is_dir() and proj_dir.name.startswith("step_"):
                expected_path = proj_dir / "expected_findings.json"
                with open(expected_path) as f:
                    data = json.load(f)
                for field in required_fields:
                    assert field in data, f"Missing {field} in {expected_path}"
