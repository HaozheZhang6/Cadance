"""Tests for fixture/test data hygiene and consistency."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Valid lowercase status values
VALID_STATUS_VALUES = frozenset({"pass", "fail", "warn", "unknown"})

# Path to test projects directory
TEST_PROJECTS_DIR = (
    Path(__file__).parent.parent.parent / "src" / "mech_verifier" / "test_projects"
)


def iter_expected_findings_files():
    """Iterate over all expected_findings.json files in test_projects."""
    if not TEST_PROJECTS_DIR.exists():
        return
    yield from TEST_PROJECTS_DIR.rglob("expected_findings.json")


class TestExpectedStatusNormalization:
    """Validate that expected_status values use lowercase conventions."""

    def test_expected_status_values_are_lowercase(self):
        """
        Scan all expected_findings.json files and validate that expected_status
        values are lowercase (pass/fail/warn/unknown).

        Fails if any use uppercase like "PASS" or "FAIL".
        """
        violations = []
        files_checked = 0

        for filepath in iter_expected_findings_files():
            files_checked += 1
            try:
                data = json.loads(filepath.read_text())
            except (json.JSONDecodeError, OSError) as e:
                violations.append(f"{filepath}: Failed to parse JSON: {e}")
                continue

            # Check top-level expected_status
            if "expected_status" in data:
                status = data["expected_status"]
                if not isinstance(status, str):
                    violations.append(
                        f"{filepath}: expected_status is not a string: {status!r}"
                    )
                elif status not in VALID_STATUS_VALUES:
                    violations.append(
                        f"{filepath}: expected_status '{status}' is not lowercase. "
                        f"Use one of: {', '.join(sorted(VALID_STATUS_VALUES))}"
                    )

        assert files_checked > 0, (
            f"No expected_findings.json files found in {TEST_PROJECTS_DIR}. "
            "Test projects may be missing."
        )

        if violations:
            violation_msg = "\n".join(f"  - {v}" for v in violations)
            pytest.fail(
                f"Found {len(violations)} expected_status casing violation(s):\n"
                f"{violation_msg}\n\n"
                f"Expected status values must be lowercase: {', '.join(sorted(VALID_STATUS_VALUES))}"
            )

    def test_all_expected_findings_have_status(self):
        """Ensure all expected_findings.json files have an expected_status field."""
        missing = []

        for filepath in iter_expected_findings_files():
            try:
                data = json.loads(filepath.read_text())
            except (json.JSONDecodeError, OSError):
                continue  # Parsing errors caught by other test

            if "expected_status" not in data:
                missing.append(
                    str(filepath.relative_to(TEST_PROJECTS_DIR.parent.parent.parent))
                )

        if missing:
            missing_msg = "\n".join(f"  - {m}" for m in missing)
            pytest.fail(
                f"Found {len(missing)} expected_findings.json file(s) missing expected_status:\n"
                f"{missing_msg}"
            )


# --- Absolute Path Detection Tests ---

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Directories to scan for JSON fixtures
FIXTURE_DIRS = [
    PROJECT_ROOT / "src" / "mech_verifier" / "test_projects",
    PROJECT_ROOT / "tests",
]

# Pattern to detect absolute paths
# Matches:
#   - Unix home directories: /home/username/..., /Users/..., /root/...
#   - Windows drive letters: C:\, D:\, etc.
#   - UNC paths: \\server\share or //server/share
# Note: Uses negative lookahead to exclude URI schemes (e.g., mech://, file://)
ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:"
    r"/home/"  # Unix /home/ paths
    r"|"
    r"/Users/"  # macOS /Users/ paths
    r"|"
    r"/root/"  # Unix /root/ paths
    r"|"
    r"[A-Za-z]:\\\\"  # Windows paths with escaped backslash (C:\\)
    r"|"
    r"[A-Za-z]:/(?!/)"  # Windows paths with forward slash (C:/) but not :// (URIs)
    r"|"
    r"\\\\\\\\"  # UNC paths with escaped backslashes (\\\\server)
    r"|"
    r"(?<![a-zA-Z]:)//"  # UNC paths with forward slashes (//server) but not after drive letter
    r")",
    re.IGNORECASE,
)


def collect_json_fixtures() -> list[Path]:
    """Collect all JSON files from fixture directories.

    Excludes:
    - demos/results/ - generated demo output files (not fixtures)
    - data/ - runtime data directory
    """
    json_files = []
    # Directories to exclude (contain generated output, not fixtures)
    exclude_patterns = ["demos/results", "/data/"]

    for fixture_dir in FIXTURE_DIRS:
        if fixture_dir.exists():
            for json_file in fixture_dir.rglob("*.json"):
                # Skip files in excluded directories
                path_str = str(json_file)
                if any(excl in path_str for excl in exclude_patterns):
                    continue
                json_files.append(json_file)
    return sorted(json_files)


def check_file_for_absolute_paths(filepath: Path) -> list[tuple[int, str]]:
    """Check a file for absolute paths, returning list of (line_number, line) tuples."""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), start=1):
            if ABSOLUTE_PATH_PATTERN.search(line):
                violations.append((i, line.strip()))
    except (OSError, UnicodeDecodeError):
        pass  # Skip unreadable files
    return violations


# Collect fixtures at module load time for parametrization
_json_fixtures = collect_json_fixtures()


@pytest.mark.parametrize(
    "json_file",
    _json_fixtures,
    ids=[str(f.relative_to(PROJECT_ROOT)) for f in _json_fixtures],
)
def test_no_absolute_paths_in_fixture(json_file: Path) -> None:
    """Ensure JSON fixtures do not contain absolute paths."""
    violations = check_file_for_absolute_paths(json_file)

    if violations:
        rel_path = json_file.relative_to(PROJECT_ROOT)
        violation_details = "\n".join(
            f"  Line {line_num}: {line[:100]}{'...' if len(line) > 100 else ''}"
            for line_num, line in violations
        )
        pytest.fail(
            f"Absolute path(s) found in {rel_path}:\n{violation_details}\n"
            f"Fixtures should use relative paths or placeholders."
        )
