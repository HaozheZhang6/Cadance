#!/usr/bin/env python
"""
Run confidence enhancement evaluation.

Evaluates how mech_verify verification enhances confidence scores
by running baseline vs enhanced verification configurations.
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mech_verify.orchestrator import VerificationConfig
from tests.test_integration.fixtures import (
    ConfidenceAnalyzer,
    VerificationRunner,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run confidence enhancement evaluation"
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing STEP files to evaluate",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("evaluation_results"),
        help="Output directory for results (default: evaluation_results)",
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Run baseline verification only (no enhanced checks)",
    )
    parser.add_argument(
        "--enhanced-only",
        action="store_true",
        help="Run enhanced verification only (no baseline)",
    )
    parser.add_argument(
        "--use-external-tools",
        action="store_true",
        help="Enable external tool adapters (FreeCAD, SFA)",
    )
    parser.add_argument(
        "--require-pmi",
        action="store_true",
        help="Require PMI data in verification",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    return parser.parse_args()


def find_step_files(input_dir: Path) -> list[Path]:
    """Find all STEP files in input directory."""
    step_files = []
    for ext in ["*.step", "*.stp", "*.STEP", "*.STP"]:
        step_files.extend(input_dir.glob(f"**/{ext}"))
    return sorted(step_files)


def run_evaluation(args):
    """Run full evaluation pipeline."""
    print("Confidence Enhancement Evaluation")
    print("=" * 80)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output}")
    print()

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Find STEP files
    step_files = find_step_files(args.input_dir)
    if not step_files:
        print(f"ERROR: No STEP files found in {args.input_dir}")
        return 1

    print(f"Found {len(step_files)} STEP files")
    print()

    # Initialize components
    analyzer = ConfidenceAnalyzer()

    # Baseline config (minimal checks)
    baseline_config = VerificationConfig(
        validate_schema=False,
        shacl=False,
        require_pmi=args.require_pmi,
        use_external_tools=False,
        units_length="mm",
        units_angle="deg",
    )
    baseline_runner = VerificationRunner(baseline_config)

    # Enhanced config (full checks)
    enhanced_config = VerificationConfig(
        validate_schema=True,
        shacl=True,
        require_pmi=args.require_pmi,
        use_external_tools=args.use_external_tools,
        units_length="mm",
        units_angle="deg",
    )
    enhanced_runner = VerificationRunner(enhanced_config)

    # Run evaluation on each file
    results = []
    for i, step_file in enumerate(step_files, 1):
        print(f"[{i}/{len(step_files)}] Evaluating {step_file.name}...")

        result = {
            "file": str(step_file),
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Run baseline verification
            if not args.enhanced_only:
                if args.verbose:
                    print("  Running baseline verification...")
                baseline = baseline_runner.verify_step(step_file)
                result["baseline"] = {
                    "status": baseline.status,
                    "findings": len(baseline.findings),
                    "unknowns": len(baseline.unknowns),
                    "has_blockers": baseline.has_blockers,
                }

            # Run enhanced verification
            if not args.baseline_only:
                if args.verbose:
                    print("  Running enhanced verification...")
                enhanced = enhanced_runner.verify_step(step_file)
                result["enhanced"] = {
                    "status": enhanced.status,
                    "findings": len(enhanced.findings),
                    "unknowns": len(enhanced.unknowns),
                    "has_blockers": enhanced.has_blockers,
                }

            # Compute confidence comparison
            if not args.baseline_only and not args.enhanced_only:
                if args.verbose:
                    print("  Computing confidence comparison...")
                comparison = analyzer.compare_results(baseline, enhanced)
                result["confidence"] = {
                    "baseline": comparison.baseline.overall_confidence,
                    "enhanced": comparison.enhanced.overall_confidence,
                    "improvement": comparison.confidence_improvement,
                    "improvement_pct": comparison.improvement_percentage,
                    "additional_evidence": comparison.additional_evidence,
                    "improvement_factors": comparison.improvement_factors,
                }

                print(
                    f"  Confidence: {comparison.baseline.overall_confidence:.3f} -> "
                    f"{comparison.enhanced.overall_confidence:.3f} "
                    f"(+{comparison.improvement_percentage:.1f}%)"
                )
            elif not args.baseline_only:
                # Enhanced only - compute single confidence
                enhanced_score = analyzer.analyze_result(enhanced)
                result["confidence"] = {
                    "enhanced": enhanced_score.overall_confidence,
                }
                print(f"  Confidence: {enhanced_score.overall_confidence:.3f}")
            else:
                # Baseline only - compute single confidence
                baseline_score = analyzer.analyze_result(baseline)
                result["confidence"] = {
                    "baseline": baseline_score.overall_confidence,
                }
                print(f"  Confidence: {baseline_score.overall_confidence:.3f}")

            result["success"] = True

        except Exception as e:
            print(f"  ERROR: {e}")
            result["success"] = False
            result["error"] = str(e)

        results.append(result)
        print()

    # Write results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.format in ["json", "both"]:
        json_path = args.output / f"results_{timestamp}.json"
        write_json_results(results, json_path)
        print(f"Results written to: {json_path}")

    if args.format in ["csv", "both"]:
        csv_path = args.output / f"results_{timestamp}.csv"
        write_csv_results(results, csv_path)
        print(f"Results written to: {csv_path}")

    # Generate summary
    summary = generate_summary(results)
    summary_path = args.output / f"summary_{timestamp}.txt"
    write_summary(summary, summary_path)
    print(f"Summary written to: {summary_path}")
    print()
    print("Summary:")
    print(summary)

    return 0


def write_json_results(results: list[dict], output_path: Path):
    """Write results to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "evaluation_type": "confidence_enhancement",
                "timestamp": datetime.now().isoformat(),
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


def write_csv_results(results: list[dict], output_path: Path):
    """Write results to CSV file."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(
            [
                "File",
                "Success",
                "Baseline Status",
                "Enhanced Status",
                "Baseline Confidence",
                "Enhanced Confidence",
                "Improvement",
                "Improvement %",
                "Additional Evidence Count",
            ]
        )

        # Data rows
        for result in results:
            confidence = result.get("confidence", {})
            writer.writerow(
                [
                    Path(result["file"]).name,
                    result.get("success", False),
                    result.get("baseline", {}).get("status", "N/A"),
                    result.get("enhanced", {}).get("status", "N/A"),
                    f"{confidence.get('baseline', 0):.3f}",
                    f"{confidence.get('enhanced', 0):.3f}",
                    f"{confidence.get('improvement', 0):.3f}",
                    f"{confidence.get('improvement_pct', 0):.1f}",
                    len(confidence.get("additional_evidence", [])),
                ]
            )


def generate_summary(results: list[dict]) -> str:
    """Generate summary statistics."""
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    failed = total - successful

    # Compute aggregate confidence metrics
    baseline_confidences = [
        r.get("confidence", {}).get("baseline", 0)
        for r in results
        if r.get("success", False) and "baseline" in r.get("confidence", {})
    ]
    enhanced_confidences = [
        r.get("confidence", {}).get("enhanced", 0)
        for r in results
        if r.get("success", False) and "enhanced" in r.get("confidence", {})
    ]
    improvements = [
        r.get("confidence", {}).get("improvement", 0)
        for r in results
        if r.get("success", False) and "improvement" in r.get("confidence", {})
    ]

    summary = []
    summary.append("Confidence Enhancement Evaluation Summary")
    summary.append("=" * 80)
    summary.append(f"Total files: {total}")
    summary.append(f"Successful: {successful}")
    summary.append(f"Failed: {failed}")
    summary.append("")

    if baseline_confidences and enhanced_confidences:
        avg_baseline = sum(baseline_confidences) / len(baseline_confidences)
        avg_enhanced = sum(enhanced_confidences) / len(enhanced_confidences)
        avg_improvement = sum(improvements) / len(improvements)
        avg_improvement_pct = (
            (avg_improvement / avg_baseline * 100) if avg_baseline > 0 else 0
        )

        summary.append("Average Confidence Scores:")
        summary.append(f"  Baseline:    {avg_baseline:.3f}")
        summary.append(f"  Enhanced:    {avg_enhanced:.3f}")
        summary.append(
            f"  Improvement: {avg_improvement:.3f} (+{avg_improvement_pct:.1f}%)"
        )
        summary.append("")

        # Count improvements
        improved = sum(1 for imp in improvements if imp > 0.01)
        unchanged = sum(1 for imp in improvements if abs(imp) <= 0.01)
        degraded = sum(1 for imp in improvements if imp < -0.01)

        summary.append("Confidence Changes:")
        summary.append(
            f"  Improved:  {improved} ({improved/len(improvements)*100:.1f}%)"
        )
        summary.append(
            f"  Unchanged: {unchanged} ({unchanged/len(improvements)*100:.1f}%)"
        )
        summary.append(
            f"  Degraded:  {degraded} ({degraded/len(improvements)*100:.1f}%)"
        )
    elif enhanced_confidences:
        avg_enhanced = sum(enhanced_confidences) / len(enhanced_confidences)
        summary.append("Average Enhanced Confidence:")
        summary.append(f"  {avg_enhanced:.3f}")
    elif baseline_confidences:
        avg_baseline = sum(baseline_confidences) / len(baseline_confidences)
        summary.append("Average Baseline Confidence:")
        summary.append(f"  {avg_baseline:.3f}")

    return "\n".join(summary)


def write_summary(summary: str, output_path: Path):
    """Write summary to file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)
        f.write("\n")


def main():
    """Main entry point."""
    args = parse_args()

    if not args.input_dir.exists():
        print(f"ERROR: Input directory does not exist: {args.input_dir}")
        return 1

    if not args.input_dir.is_dir():
        print(f"ERROR: Input path is not a directory: {args.input_dir}")
        return 1

    return run_evaluation(args)


if __name__ == "__main__":
    sys.exit(main())
