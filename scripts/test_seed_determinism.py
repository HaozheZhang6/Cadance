#!/usr/bin/env python
"""Test deterministic mode (seed + temperature=0).

Run with: uv run python scripts/test_seed_determinism.py

Deterministic mode requires:
- seed (fixed value, e.g., 42)
- temperature=0
- same model
- same system_fingerprint (OpenAI backend)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_deterministic_mode():
    """Test that deterministic mode (seed=42, temp=0) produces identical outputs."""
    import openai

    client = openai.OpenAI()

    # Deterministic settings (matches --deterministic flag)
    seed = 42
    temperature = 0.0
    model = "gpt-5.2"  # Use configured model (deterministic with seed)

    prompt = """Create CadQuery code for a simple L-bracket:
- Base: 50mm x 30mm x 5mm
- Vertical wall: 30mm x 5mm x 40mm
- 4mm mounting holes in base corners
- 2mm fillet on inner corner
Variable name: result
"""

    system_prompt = "You are a CadQuery code generator. Output only valid Python code."

    print("=" * 60)
    print("Testing DETERMINISTIC mode (seed=42, temperature=0)")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"Seed: {seed}")
    print(f"Temperature: {temperature}")

    results = []
    fingerprints = []

    for i in range(3):
        print(f"\n[Run {i + 1}] Generating...")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_completion_tokens=1500,
            seed=seed,
        )

        content = response.choices[0].message.content
        fingerprint = response.system_fingerprint

        results.append(content)
        fingerprints.append(fingerprint)

        print(f"  Length: {len(content)} chars")
        print(f"  Fingerprint: {fingerprint}")

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    # Check fingerprints
    unique_fps = set(fingerprints)
    print(f"\nFingerprints: {len(unique_fps)} unique")
    for fp in unique_fps:
        count = fingerprints.count(fp)
        print(f"  {fp}: {count}x")

    if len(unique_fps) > 1:
        print("\n⚠ WARNING: Multiple fingerprints detected")
        print("  OpenAI backend changed between calls - outputs may differ")

    # Check outputs
    unique_outputs = len(set(results))
    all_identical = unique_outputs == 1

    print(f"\nOutputs: {unique_outputs} unique out of {len(results)} runs")

    if all_identical:
        print("\n✓ SUCCESS: All outputs IDENTICAL")
        print("\nFirst 500 chars of output:")
        print("-" * 40)
        print(results[0][:500])
        print("-" * 40)
    else:
        print("\n✗ DIFFERENT: Outputs vary (unexpected with temp=0)")

        # Show lengths
        for i, r in enumerate(results):
            print(f"  Run {i + 1}: {len(r)} chars")

    return all_identical


def test_non_deterministic():
    """Show that without temp=0, outputs differ even with seed."""
    import openai

    client = openai.OpenAI()

    seed = 42
    temperature = 0.2  # Non-zero temperature
    model = "gpt-5.2"

    prompt = "Create CadQuery code for a 10x20x5mm box. Variable: result"

    print("\n" + "=" * 60)
    print("Testing NON-DETERMINISTIC (seed=42, temperature=0.2)")
    print("=" * 60)

    results = []
    for i in range(3):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_completion_tokens=500,
            seed=seed,
        )
        results.append(response.choices[0].message.content)
        print(f"[Run {i + 1}] {len(results[-1])} chars")

    unique = len(set(results))
    print(f"\nUnique outputs: {unique}/{len(results)}")

    if unique > 1:
        print("  (Expected - temperature > 0 allows variation)")
    else:
        print("  (Happened to be identical - possible with simple prompts)")

    return unique > 1  # Expected to differ


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    print("Deterministic Mode Test")
    print("Tests --deterministic flag behavior (seed=42, temp=0)\n")

    # Test deterministic mode
    det_pass = test_deterministic_mode()

    # Test that non-zero temp causes variation
    nondet_varies = test_non_deterministic()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Deterministic mode (temp=0): {'PASS' if det_pass else 'FAIL'}")
    print(f"Non-deterministic varies:    {'YES' if nondet_varies else 'NO'}")

    if det_pass:
        print("\n✓ --deterministic flag will produce reproducible outputs")
        print(
            "  Usage: uv run python -m src.cli resume --from-step artifact --deterministic"
        )

    sys.exit(0 if det_pass else 1)
