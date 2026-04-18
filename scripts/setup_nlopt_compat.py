#!/usr/bin/env python
"""
Setup nlopt compatibility stub for CadQuery.

Run after `uv sync` to enable CadQuery with scipy-based nlopt fallback:
    uv run python scripts/setup_nlopt_compat.py

This creates a stub in .venv that redirects nlopt imports to our
scipy-based compatibility layer.

WARNING: This script writes to site-packages. Use --yes to confirm.
"""

import argparse
import sys
from pathlib import Path

STUB_CONTENT = '''\
"""
nlopt compatibility stub for CadQuery.

Redirects to mech_verify.optimization.nlopt_compat for actual optimization.
"""

# Re-export everything from our compatibility layer
from mech_verify.optimization.nlopt_compat import *
from mech_verify.optimization.nlopt_compat import opt, OptimizationError
'''


def main():
    parser = argparse.ArgumentParser(
        description="Setup nlopt compatibility stub for CadQuery"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Confirm writing to site-packages without prompting",
    )
    args = parser.parse_args()

    # Find site-packages in current venv
    for p in sys.path:
        if "site-packages" in p and ".venv" in p:
            site_packages = Path(p)
            break
    else:
        print("ERROR: Could not find .venv site-packages")
        sys.exit(1)

    nlopt_path = site_packages / "nlopt.py"

    # Check if real nlopt exists
    try:
        import nlopt

        if hasattr(nlopt, "_nlopt"):  # Real nlopt has C extension
            print(f"Real nlopt already installed at {nlopt.__file__}")
            return
    except ImportError:
        pass

    # Confirm before writing
    if not args.yes:
        print(f"WARNING: This will write to site-packages: {nlopt_path}")
        print("This may affect environment reproducibility from lockfiles.")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Write stub
    nlopt_path.write_text(STUB_CONTENT, encoding="utf-8")
    print(f"Created nlopt compatibility stub at {nlopt_path}")

    # Verify it works
    try:
        import importlib

        importlib.invalidate_caches()
        import nlopt

        print("Verification: nlopt imports successfully")
    except Exception as e:
        print(f"WARNING: Verification failed: {e}")


if __name__ == "__main__":
    main()
