#!/usr/bin/env python
"""Run confidence evaluation on test STEP files."""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_integration.fixtures.confidence_analyzer import (
    ConfidenceAnalyzer,
)
from tests.test_integration.fixtures.verification_runner import (
    VerificationConfig,
    VerificationRunner,
)


def run_evaluation(test_steps_dir: Path, output_dir: Path):
    """Run evaluation on all test STEP files."""
    # Load manifest
    manifest_path = test_steps_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Setup runners
    baseline_runner = VerificationRunner(
        VerificationConfig(validate_schema=False, shacl=False)
    )
    enhanced_runner = VerificationRunner(
        VerificationConfig(
            validate_schema=True,
            shacl=True,
            use_external_tools=False,  # Skip FreeCAD/SFA for now
        )
    )

    analyzer = ConfidenceAnalyzer()
    results = []

    print("=" * 80)
    print("CONFIDENCE ENHANCEMENT EVALUATION")
    print("=" * 80)

    for test_case in manifest["test_cases"]:
        step_path = Path(test_case["path"])
        name = test_case["name"]
        level = test_case["level"]

        print(f"\n[Level {level}] {name}")
        print("-" * 80)

        # Baseline verification
        baseline_result = baseline_runner.verify_step(step_path)

        # Enhanced verification
        enhanced_result = enhanced_runner.verify_step(step_path)

        # Compare confidence
        comparison = analyzer.compare_results(baseline_result, enhanced_result)

        baseline_conf = comparison.baseline.overall_confidence
        enhanced_conf = comparison.enhanced.overall_confidence
        delta = comparison.confidence_improvement

        # Display results
        print(
            f"  Baseline:  {baseline_result.status:8s} | Confidence: {baseline_conf:.3f}"
        )
        print(
            f"  Enhanced:  {enhanced_result.status:8s} | Confidence: {enhanced_conf:.3f}"
        )
        print(
            f"  Delta:     {delta:+.3f} ({'IMPROVED' if comparison.has_improvement else 'NO CHANGE'})"
        )

        if len(enhanced_result.findings) > 0:
            print(f"  Findings:  {len(enhanced_result.findings)} issues detected")

        if len(enhanced_result.unknowns) > 0:
            print(f"  Unknowns:  {len(enhanced_result.unknowns)} uncertainty sources")

        # Store result
        result = {
            "test_case": name,
            "level": level,
            "baseline": {
                "status": baseline_result.status,
                "confidence": baseline_conf,
                "findings": len(baseline_result.findings),
                "unknowns": len(baseline_result.unknowns),
            },
            "enhanced": {
                "status": enhanced_result.status,
                "confidence": enhanced_conf,
                "findings": len(enhanced_result.findings),
                "unknowns": len(enhanced_result.unknowns),
            },
            "improvement": {
                "delta": delta,
                "has_improvement": comparison.has_improvement,
                "improvement_percentage": comparison.improvement_percentage,
                "additional_evidence": comparison.additional_evidence,
            },
        }
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_cases = len(results)
    improved = sum(1 for r in results if r["improvement"]["has_improvement"])
    degraded = sum(1 for r in results if r["improvement"]["delta"] < -0.01)
    unchanged = total_cases - improved - degraded

    avg_baseline = sum(r["baseline"]["confidence"] for r in results) / total_cases
    avg_enhanced = sum(r["enhanced"]["confidence"] for r in results) / total_cases
    avg_delta = avg_enhanced - avg_baseline

    print(f"Total test cases:     {total_cases}")
    print(f"Confidence improved:  {improved}")
    print(f"Confidence unchanged: {unchanged}")
    print(f"Confidence degraded:  {degraded}")
    print(f"\nAverage baseline confidence:  {avg_baseline:.3f}")
    print(f"Average enhanced confidence:  {avg_enhanced:.3f}")
    print(f"Average delta:                {avg_delta:+.3f}")

    # Write results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_cases": total_cases,
                    "improved": improved,
                    "unchanged": unchanged,
                    "degraded": degraded,
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
    test_steps_dir = Path(__file__).parent.parent / "tests" / "evaluation_steps"
    output_dir = Path(__file__).parent.parent / "results"

    if not test_steps_dir.exists():
        print(f"Error: Test steps directory not found: {test_steps_dir}")
        print("Run generate_evaluation_steps.py first")
        return 1

    return run_evaluation(test_steps_dir, output_dir)


if __name__ == "__main__":
    exit(main())
