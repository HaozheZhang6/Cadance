#!/usr/bin/env python3
"""Generate manifest.json with train/eval split assignments.

Discovers all test samples from the train/ and eval/ subdirectories.
Split is determined by directory location:
- samples in train/ → train
- samples in eval/ → eval

The manifest provides a central source of truth for split assignments,
enabling reproducible train/eval filtering in the evaluation runner.

Usage:
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_manifest.py
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_manifest.py --show
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def extract_test_id(test_dir: Path) -> str:
    """Extract test ID from directory name.

    Examples:
        L1_01_simple_box -> L1_01
        L1_E01_cone -> L1_E01
    """
    parts = test_dir.name.split("_")
    if len(parts) >= 2:
        # Handle both L1_01 and L1_E01 patterns
        if parts[1].startswith("E"):
            # Eval sample: L1_E01_name -> L1_E01
            return f"{parts[0]}_{parts[1]}"
        else:
            # Train sample: L1_01_name -> L1_01
            return f"{parts[0]}_{parts[1]}"
    return test_dir.name


def extract_level(test_id: str) -> int:
    """Extract level number from test ID.

    Examples:
        L1_01 -> 1
        L2_E03 -> 2
    """
    if test_id.startswith("L") and len(test_id) > 1:
        return int(test_id[1])
    return 0


def discover_samples(base_dir: Path) -> list[dict]:
    """Discover all test samples in the evaluation suite.

    Searches in train/ and eval/ subdirectories.
    Split is determined by directory location.
    """
    samples = []

    for split in ["train", "eval"]:
        split_dir = base_dir / split
        if not split_dir.exists():
            continue

        for level_dir in sorted(split_dir.iterdir()):
            if not level_dir.is_dir() or not level_dir.name.startswith("level_"):
                continue

            for test_dir in sorted(level_dir.iterdir()):
                if not test_dir.is_dir():
                    continue

                # Must have either ground_truth.py or spec.json
                has_ground_truth = (test_dir / "ground_truth.py").exists()
                has_spec = (test_dir / "spec.json").exists()

                if not (has_ground_truth or has_spec):
                    continue

                test_id = extract_test_id(test_dir)
                level = extract_level(test_id)

                samples.append(
                    {
                        "test_id": test_id,
                        "level": level,
                        "split": split,  # Determined by directory location
                        "directory": test_dir.name,
                    }
                )

    return samples


def generate_manifest(base_dir: Path) -> dict:
    """Generate the manifest dictionary."""
    samples = discover_samples(base_dir)

    # Build samples dict
    samples_dict = {}
    for sample in samples:
        samples_dict[sample["test_id"]] = {
            "split": sample["split"],
            "level": sample["level"],
        }

    # Compute statistics
    train_count = sum(1 for s in samples if s["split"] == "train")
    eval_count = sum(1 for s in samples if s["split"] == "eval")

    train_by_level = {}
    eval_by_level = {}
    for sample in samples:
        level = sample["level"]
        if sample["split"] == "train":
            train_by_level[level] = train_by_level.get(level, 0) + 1
        else:
            eval_by_level[level] = eval_by_level.get(level, 0) + 1

    manifest = {
        "version": "1.0",
        "description": "CAD evaluation suite manifest with train/eval splits",
        "generated_at": datetime.now(UTC).isoformat(),
        "statistics": {
            "total_samples": len(samples),
            "train_samples": train_count,
            "eval_samples": eval_count,
            "train_by_level": train_by_level,
            "eval_by_level": eval_by_level,
        },
        "split_convention": {
            "train": "Samples in train/ directory",
            "eval": "Samples in eval/ directory (held-out test set)",
        },
        "samples": samples_dict,
    }

    return manifest


def print_summary(manifest: dict) -> None:
    """Print a summary of the manifest."""
    stats = manifest["statistics"]

    print("=" * 50)
    print("MANIFEST SUMMARY")
    print("=" * 50)
    print(f"\nTotal samples: {stats['total_samples']}")
    print(f"  Train: {stats['train_samples']}")
    print(f"  Eval:  {stats['eval_samples']}")

    print("\nBy level:")
    all_levels = sorted(
        set(stats["train_by_level"].keys()) | set(stats["eval_by_level"].keys())
    )
    for level in all_levels:
        train = stats["train_by_level"].get(level, 0)
        eval_ = stats["eval_by_level"].get(level, 0)
        print(f"  L{level}: {train} train, {eval_} eval")

    print("\nSamples:")
    for test_id, info in sorted(manifest["samples"].items()):
        split_marker = "[TRAIN]" if info["split"] == "train" else "[EVAL] "
        print(f"  {split_marker} {test_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate manifest.json with train/eval split assignments.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Only show current manifest without regenerating",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and display manifest without writing to file",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    manifest_path = base_dir / "manifest.json"

    if args.show and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        print_summary(manifest)
        return 0

    manifest = generate_manifest(base_dir)
    print_summary(manifest)

    if args.dry_run:
        print("\n[DRY RUN] Manifest not written to file")
        return 0

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nManifest written to: {manifest_path}")
    return 0


if __name__ == "__main__":
    exit(main())
