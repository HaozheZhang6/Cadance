"""End-to-end tests for assembly verification (TDD)."""

import json
import subprocess
from pathlib import Path

from .conftest import requires_occt

pytestmark = requires_occt


def test_cli_assembly_interference_blocks():
    """Assembly with interference → exit 1, BLOCKER finding."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_interference/inputs/assembly.step"
    )
    output_dir = Path("/tmp/test_asm_interference")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["mech-verify", "verify", str(asm_path), "-o", str(output_dir)],
        capture_output=True,
        text=True,
    )

    # Exit 1 = FAIL
    assert result.returncode == 1

    # Check report.json
    report_path = output_dir / "report.json"
    assert report_path.exists()

    with open(report_path) as f:
        report = json.load(f)

    assert report["status"] == "FAIL"
    assert len(report["findings"]) > 0

    # Find interference finding
    interference = [
        f for f in report["findings"] if f["rule_id"] == "mech.tier0.interference"
    ]
    assert len(interference) > 0
    assert interference[0]["severity"] == "BLOCKER"


def test_cli_assembly_clearance_warns():
    """Assembly with tight clearance → WARN finding detected."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clearance/inputs/assembly.step"
    )
    output_dir = Path("/tmp/test_asm_clearance")
    output_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["mech-verify", "verify", str(asm_path), "-o", str(output_dir)],
        capture_output=True,
        text=True,
    )

    report_path = output_dir / "report.json"
    assert report_path.exists()

    with open(report_path) as f:
        report = json.load(f)

    # Find clearance warning
    clearance = [
        f for f in report["findings"] if f["rule_id"] == "mech.tier0.clearance"
    ]
    assert len(clearance) > 0
    assert clearance[0]["severity"] == "WARN"


def test_cli_assembly_clean_pass():
    """Assembly with proper spacing → no interference/clearance findings."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    output_dir = Path("/tmp/test_asm_clean")
    output_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["mech-verify", "verify", str(asm_path), "-o", str(output_dir)],
        capture_output=True,
        text=True,
    )

    report_path = output_dir / "report.json"
    assert report_path.exists()

    with open(report_path) as f:
        report = json.load(f)

    # No assembly findings (clean spacing)
    asm_findings = [
        f
        for f in report["findings"]
        if "interference" in f["rule_id"] or "clearance" in f["rule_id"]
    ]
    assert len(asm_findings) == 0


def test_deterministic_findings():
    """Assembly findings deterministic across multiple runs."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_interference/inputs/assembly.step"
    )

    output_dir1 = Path("/tmp/test_asm_det1")
    output_dir2 = Path("/tmp/test_asm_det2")
    output_dir1.mkdir(parents=True, exist_ok=True)
    output_dir2.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["mech-verify", "verify", str(asm_path), "-o", str(output_dir1)],
        capture_output=True,
    )
    subprocess.run(
        ["mech-verify", "verify", str(asm_path), "-o", str(output_dir2)],
        capture_output=True,
    )

    with open(output_dir1 / "report.json") as f:
        report1 = json.load(f)
    with open(output_dir2 / "report.json") as f:
        report2 = json.load(f)

    # Filter to assembly findings (interference/clearance)
    asm1 = sorted(
        [
            (f["rule_id"], f["object_ref"], f["severity"])
            for f in report1["findings"]
            if "interference" in f["rule_id"] or "clearance" in f["rule_id"]
        ]
    )
    asm2 = sorted(
        [
            (f["rule_id"], f["object_ref"], f["severity"])
            for f in report2["findings"]
            if "interference" in f["rule_id"] or "clearance" in f["rule_id"]
        ]
    )

    assert asm1 == asm2
    assert len(asm1) > 0  # Should have at least interference finding


def test_backward_compat_single_part():
    """Single-part STEP still works (no regressions)."""
    single_part = Path(
        "src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"
    )
    output_dir = Path("/tmp/test_single_part")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["mech-verify", "verify", str(single_part), "-o", str(output_dir)],
        capture_output=True,
        text=True,
    )

    # Should pass
    assert result.returncode == 0

    report_path = output_dir / "report.json"
    assert report_path.exists()

    with open(report_path) as f:
        report = json.load(f)

    assert report["status"] == "PASS"
    # No assembly findings for single-part
    asm_findings = [
        f
        for f in report["findings"]
        if "interference" in f["rule_id"] or "clearance" in f["rule_id"]
    ]
    assert len(asm_findings) == 0
