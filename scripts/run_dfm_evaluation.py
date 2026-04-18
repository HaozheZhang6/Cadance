#!/usr/bin/env python
"""Run confidence evaluation on DFM test cases."""

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


def run_dfm_evaluation(test_cases_dir: Path, output_dir: Path):
    """Run evaluation on DFM test cases."""
    # Load manifest
    manifest_path = test_cases_dir / "manifest.json"
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
    print("DFM CONFIDENCE ENHANCEMENT EVALUATION")
    print("=" * 80)
    print("\nDemonstrating confidence enhancement with realistic DFM violations")
    print()

    for test_case in manifest["test_cases"]:
        step_path = Path(test_case["path"])
        ops_program_path = (
            Path(test_case.get("ops_program")) if test_case.get("ops_program") else None
        )
        name = test_case["name"]
        level = test_case["level"]
        expected_violations = test_case.get("expected", {}).get("violations", [])

        print(f"{'=' * 80}")
        print(f"[Level {level}] {name}")
        print(
            f"Expected violations: {expected_violations if expected_violations else 'None (golden pass)'}"
        )
        print("=" * 80)

        # Baseline verification (minimal checks)
        baseline_result = baseline_runner.verify_step(
            step_path, ops_program_path=ops_program_path
        )
        baseline_score = analyzer.analyze_result(baseline_result)

        # Enhanced verification (full checks)
        enhanced_result = enhanced_runner.verify_step(
            step_path, ops_program_path=ops_program_path
        )
        enhanced_score = analyzer.analyze_result(enhanced_result)

        # Compare
        comparison = analyzer.compare_results(baseline_result, enhanced_result)

        # Display results
        print("\nBASELINE (Geometry only):")
        print(f"  Status: {baseline_result.status}")
        print(f"  Findings: {len(baseline_result.findings)}")
        print(f"  Evidence types: {baseline_score.evidence_types}")
        print(f"  Confidence: {baseline_score.overall_confidence:.3f}")

        print("\nENHANCED (Geometry + Schema + SHACL):")
        print(f"  Status: {enhanced_result.status}")
        print(f"  Findings: {len(enhanced_result.findings)}")
        for f in enhanced_result.findings:
            severity_color = {"ERROR": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(
                f.severity.value, "•"
            )
            print(f"    {severity_color} {f.rule_id} [{f.severity.value}]")
        print(f"  Evidence types: {enhanced_score.evidence_types}")
        print(f"  Confidence: {enhanced_score.overall_confidence:.3f}")

        delta = comparison.confidence_improvement
        pct_change = (
            (delta / baseline_score.overall_confidence * 100)
            if baseline_score.overall_confidence > 0
            else 0
        )

        print("\nCONFIDENCE ENHANCEMENT:")
        print(f"  Delta: {delta:+.3f} ({pct_change:+.1f}%)")
        print(f"  Improvement: {'YES ✓' if comparison.has_improvement else 'NO'}")
        if comparison.additional_evidence:
            print(f"  Additional evidence: {comparison.additional_evidence}")

        # Store result
        result = {
            "test_case": name,
            "level": level,
            "expected_violations": expected_violations,
            "baseline": {
                "status": baseline_result.status,
                "confidence": baseline_score.overall_confidence,
                "findings": len(baseline_result.findings),
                "evidence_types": baseline_score.evidence_types,
            },
            "enhanced": {
                "status": enhanced_result.status,
                "confidence": enhanced_score.overall_confidence,
                "findings": len(enhanced_result.findings),
                "evidence_types": enhanced_score.evidence_types,
            },
            "improvement": {
                "delta": delta,
                "pct_change": pct_change,
                "has_improvement": comparison.has_improvement,
                "additional_evidence": comparison.additional_evidence,
            },
        }
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_cases = len(results)
    cases_with_improvement = sum(
        1 for r in results if r["improvement"]["has_improvement"]
    )
    cases_with_additional_evidence = sum(
        1 for r in results if r["improvement"]["additional_evidence"]
    )

    avg_baseline = sum(r["baseline"]["confidence"] for r in results) / total_cases
    avg_enhanced = sum(r["enhanced"]["confidence"] for r in results) / total_cases
    avg_delta = avg_enhanced - avg_baseline

    print(f"Total test cases: {total_cases}")
    print(f"Cases with confidence improvement: {cases_with_improvement}")
    print(f"Cases with additional evidence: {cases_with_additional_evidence}")
    print(f"\nAverage baseline confidence:  {avg_baseline:.3f}")
    print(f"Average enhanced confidence:  {avg_enhanced:.3f}")
    print(f"Average delta:                {avg_delta:+.3f}")

    # Per-level breakdown
    by_level = {}
    for r in results:
        level = r["level"]
        by_level.setdefault(level, []).append(r)

    print("\nPer-level confidence deltas:")
    for level in sorted(by_level.keys()):
        level_results = by_level[level]
        level_avg_delta = sum(lr["improvement"]["delta"] for lr in level_results) / len(
            level_results
        )
        print(f"  Level {level}: {level_avg_delta:+.3f}")

    # Write results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "dfm_evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_cases": total_cases,
                    "cases_with_improvement": cases_with_improvement,
                    "cases_with_additional_evidence": cases_with_additional_evidence,
                    "avg_baseline_confidence": avg_baseline,
                    "avg_enhanced_confidence": avg_enhanced,
                    "avg_delta": avg_delta,
                },
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results written to: {output_path}")

    return 0


def main():
    """Main entry point."""
    test_cases_dir = Path(__file__).parent.parent / "tests" / "dfm_test_cases"
    output_dir = Path(__file__).parent.parent / "results"

    if not test_cases_dir.exists():
        print(f"Error: Test cases directory not found: {test_cases_dir}")
        print("Run generate_dfm_test_cases.py first")
        return 1

    return run_dfm_evaluation(test_cases_dir, output_dir)


if __name__ == "__main__":
    exit(main())
