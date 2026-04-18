#!/usr/bin/env python
"""Test code generation stability across temperature values.

Run with: uv run python scripts/temperature_experiment.py
"""

import json
import subprocess
from pathlib import Path

# Config
TEMPERATURES = [0.0, 0.5, 1.0]
RUNS_PER_TEMP = 3
SEED = 42
ARTIFACT_DIR = Path("data/artifacts")


def get_latest_artifact() -> Path | None:
    """Get most recent artifact JSON by run_id timestamp in filename."""
    jsons = list(ARTIFACT_DIR.glob("*.json"))
    # Filter to those with _<timestamp>.json pattern (exclude reports)
    artifacts = [p for p in jsons if not p.name.startswith("report_")]
    if not artifacts:
        return None
    # Sort by modification time (most recent first)
    return max(artifacts, key=lambda p: p.stat().st_mtime)


def run_pipeline(temperature: float, seed: int) -> dict:
    """Run pipeline and return results."""
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "src.cli",
        "resume",
        "--from-step",
        "artifact",
        "--only",
        "--seed",
        str(seed),
        "--temperature",
        str(temperature),
    ]

    print(f"  Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
        )
        success = result.returncode == 0
        error = result.stderr if not success else None
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "iterations": None}
    except Exception as e:
        return {"success": False, "error": str(e), "iterations": None}

    # Find the artifact that was just created
    artifact = get_latest_artifact()
    if not artifact:
        return {"success": False, "error": "no artifact found", "iterations": None}

    # Parse iterations from pipeline_trace
    try:
        data = json.loads(artifact.read_text())
        trace = data.get("pipeline_trace", {})
        iterations = trace.get("synthesis", {}).get("iterations", None)
        has_code = bool(data.get("generated_cadquery_code"))
    except Exception as e:
        return {"success": False, "error": f"parse error: {e}", "iterations": None}

    return {
        "success": success and has_code,
        "iterations": iterations,
        "artifact": artifact.name,
        "error": error if not success else None,
    }


def main():
    print("=" * 60)
    print("Temperature Experiment")
    print(f"Temps: {TEMPERATURES}, Runs/temp: {RUNS_PER_TEMP}, Seed: {SEED}")
    print("=" * 60)

    results = []

    for temp in TEMPERATURES:
        print(f"\n--- Temperature {temp} ---")
        for run in range(1, RUNS_PER_TEMP + 1):
            print(f"\nRun {run}/{RUNS_PER_TEMP}")
            res = run_pipeline(temp, SEED)
            res["temperature"] = temp
            res["run"] = run
            results.append(res)

            status = "OK" if res["success"] else "FAIL"
            iters = res["iterations"] if res["iterations"] is not None else "?"
            print(f"  Result: {status}, iterations={iters}")
            if res.get("artifact"):
                print(f"  Artifact: {res['artifact']}")

    # Summary table
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Temp':<6} {'Run':<4} {'Status':<6} {'Iters':<6} {'Artifact'}")
    print("-" * 60)

    for r in results:
        status = "OK" if r["success"] else "FAIL"
        iters = str(r["iterations"]) if r["iterations"] is not None else "?"
        artifact = r.get("artifact", "")[:30] if r.get("artifact") else "-"
        print(f"{r['temperature']:<6} {r['run']:<4} {status:<6} {iters:<6} {artifact}")

    # Stats per temperature
    print("\n" + "-" * 60)
    print("Per-temperature stats:")
    for temp in TEMPERATURES:
        temp_results = [r for r in results if r["temperature"] == temp]
        successes = sum(1 for r in temp_results if r["success"])
        iters = [r["iterations"] for r in temp_results if r["iterations"] is not None]
        avg_iters = sum(iters) / len(iters) if iters else 0
        print(
            f"  temp={temp}: {successes}/{len(temp_results)} success, avg_iters={avg_iters:.1f}"
        )

    # Save results
    output_path = Path("/tmp/temperature_experiment_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
