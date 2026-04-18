#!/usr/bin/env python
"""Evaluate verification coverage enhancement (not just confidence)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_integration.fixtures.confidence_analyzer import (
    ConfidenceAnalyzer,
)
from tests.test_integration.fixtures.verification_runner import (
    VerificationConfig,
    VerificationRunner,
)


def run_coverage_evaluation(test_steps_dir: Path, output_dir: Path):
    """Evaluate verification coverage enhancement."""
    # Load manifest
    manifest_path = test_steps_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Setup runners
    baseline_runner = VerificationRunner(
        VerificationConfig(validate_schema=False, shacl=False)
    )
    enhanced_runner = VerificationRunner(
        VerificationConfig(validate_schema=True, shacl=True)
    )

    analyzer = ConfidenceAnalyzer()
    results = []

    print("=" * 80)
    print("VERIFICATION COVERAGE EVALUATION")
    print("=" * 80)
    print("\nDemonstrating how enhanced verification provides:")
    print("  1. More evidence types (broader coverage)")
    print("  2. More comprehensive checks (additional findings)")
    print("  3. Better traceability (more verification layers)")

    for test_case in manifest["test_cases"]:
        step_path = Path(test_case["path"])
        name = test_case["name"]
        level = test_case["level"]

        print(f"\n{'='*80}")
        print(f"[Level {level}] {name}")
        print("=" * 80)

        # Baseline verification
        baseline_result = baseline_runner.verify_step(step_path)
        baseline_score = analyzer.analyze_result(baseline_result)

        # Enhanced verification
        enhanced_result = enhanced_runner.verify_step(step_path, enable_shacl=True)
        enhanced_score = analyzer.analyze_result(enhanced_result)

        # Comparison
        comparison = analyzer.compare_results(baseline_result, enhanced_result)

        # Display coverage metrics
        print("\nBASELINE (Geometry only):")
        print(f"  Status: {baseline_result.status}")
        print(f"  Evidence types: {len(baseline_score.evidence_types)}")
        for et in baseline_score.evidence_types:
            conf = baseline_score.confidence_by_source.get(et.split(":")[0], "N/A")
            print(f"    - {et}: {conf}")
        print(f"  Findings: {len(baseline_result.findings)}")
        print(f"  Unknowns: {len(baseline_result.unknowns)}")

        print("\nENHANCED (Geometry + Schema + SHACL):")
        print(f"  Status: {enhanced_result.status}")
        print(f"  Evidence types: {len(enhanced_score.evidence_types)}")
        for et in enhanced_score.evidence_types:
            et_key = et.split(":")[0]
            conf = enhanced_score.confidence_by_source.get(et_key, "N/A")
            print(f"    - {et}: {conf}")
        print(f"  Findings: {len(enhanced_result.findings)}")
        print(f"  Unknowns: {len(enhanced_result.unknowns)}")

        # Coverage enhancement
        print("\nCOVERAGE ENHANCEMENT:")
        additional_evidence = comparison.additional_evidence
        print(f"  Additional evidence types: {len(additional_evidence)}")
        for ae in additional_evidence:
            print(f"    + {ae}")

        additional_findings = len(enhanced_result.findings) - len(
            baseline_result.findings
        )
        print(f"  Additional findings: {additional_findings:+d}")

        if additional_findings > 0:
            print("  New issues detected:")
            baseline_rule_ids = {f.rule_id for f in baseline_result.findings}
            for f in enhanced_result.findings:
                if f.rule_id not in baseline_rule_ids:
                    print(f"    - {f.rule_id} [{f.severity.value}]")

        # Confidence
        print("\nCONFIDENCE:")
        print(f"  Baseline:  {baseline_score.overall_confidence:.3f}")
        print(f"  Enhanced:  {enhanced_score.overall_confidence:.3f}")
        print(f"  Delta:     {comparison.confidence_improvement:+.3f}")

        if comparison.has_improvement:
            print(f"  Improvement: {comparison.improvement_percentage:.1f}%")
        else:
            print(
                "  Note: Confidence unchanged due to averaging (both use first-principles evidence)"
            )
            print(
                "        Enhancement is in COVERAGE (more checks run), not confidence value"
            )

        # Store result
        result = {
            "test_case": name,
            "level": level,
            "baseline": {
                "status": baseline_result.status,
                "evidence_types": baseline_score.evidence_types,
                "findings": len(baseline_result.findings),
                "confidence": baseline_score.overall_confidence,
            },
            "enhanced": {
                "status": enhanced_result.status,
                "evidence_types": enhanced_score.evidence_types,
                "findings": len(enhanced_result.findings),
                "confidence": enhanced_score.overall_confidence,
            },
            "coverage_enhancement": {
                "additional_evidence_types": len(additional_evidence),
                "additional_evidence": additional_evidence,
                "additional_findings": additional_findings,
                "confidence_delta": comparison.confidence_improvement,
            },
        }
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_cases = len(results)
    avg_baseline_evidence = (
        sum(len(r["baseline"]["evidence_types"]) for r in results) / total_cases
    )
    avg_enhanced_evidence = (
        sum(len(r["enhanced"]["evidence_types"]) for r in results) / total_cases
    )

    total_additional_evidence = sum(
        r["coverage_enhancement"]["additional_evidence_types"] for r in results
    )
    total_additional_findings = sum(
        r["coverage_enhancement"]["additional_findings"] for r in results
    )

    print(f"Test cases: {total_cases}")
    print("\nEvidence coverage:")
    print(f"  Avg baseline evidence types:  {avg_baseline_evidence:.1f}")
    print(f"  Avg enhanced evidence types:  {avg_enhanced_evidence:.1f}")
    print(f"  Total additional evidence:    {total_additional_evidence}")
    print("\nDetection capability:")
    print(f"  Total additional findings:    {total_additional_findings}")

    print("\nKEY INSIGHT:")
    print(
        f"Enhanced verification provides {avg_enhanced_evidence/avg_baseline_evidence:.1f}x more"
    )
    print("evidence types, demonstrating broader verification coverage even though")
    print(
        "confidence values are averaged (both geometry and SHACL are first-principles)."
    )

    # Write results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "coverage_evaluation.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_cases": total_cases,
                    "avg_baseline_evidence": avg_baseline_evidence,
                    "avg_enhanced_evidence": avg_enhanced_evidence,
                    "total_additional_evidence": total_additional_evidence,
                    "total_additional_findings": total_additional_findings,
                },
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results: {output_path}")
    return 0


def main():
    """Main entry point."""
    test_steps_dir = Path(__file__).parent.parent / "tests" / "evaluation_steps"
    output_dir = Path(__file__).parent.parent / "results"

    if not test_steps_dir.exists():
        print(f"Error: {test_steps_dir} not found")
        return 1

    return run_coverage_evaluation(test_steps_dir, output_dir)


if __name__ == "__main__":
    exit(main())
