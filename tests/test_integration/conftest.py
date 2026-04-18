"""Pytest fixtures for integration tests."""

import json
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from src.mech_verifier.mech_verify.orchestrator import VerificationConfig
from tests.test_integration.fixtures import (
    CadQueryExecutor,
    ConfidenceAnalyzer,
    VerificationRunner,
)


class EvaluationTestCase(NamedTuple):
    """Represents a single evaluation test case."""

    id: str
    name: str
    level: int
    intent: str
    spec: dict[str, Any]
    ground_truth_path: Path
    ground_truth_code: str


@pytest.fixture(scope="session")
def evaluation_suite_dir() -> Path:
    """Path to evaluation suite directory."""
    return (
        Path(__file__).parent.parent
        / "test_tools"
        / "test_cadquery"
        / "evaluation_suite"
    )


@pytest.fixture(scope="session")
def test_cases(evaluation_suite_dir: Path) -> list[EvaluationTestCase]:
    """Load all 20 test cases from evaluation suite."""
    test_cases = []

    # Scan all levels
    for level_dir in sorted(evaluation_suite_dir.glob("level_*")):
        level_num = int(level_dir.name.split("_")[1])

        # Scan all test cases in this level
        for case_dir in sorted(level_dir.iterdir()):
            if not case_dir.is_dir():
                continue

            # Load test case files
            intent_path = case_dir / "intent.txt"
            spec_path = case_dir / "spec.json"
            ground_truth_path = case_dir / "ground_truth.py"

            if not all(p.exists() for p in [intent_path, spec_path, ground_truth_path]):
                continue

            # Read files
            intent = intent_path.read_text().strip()
            spec = json.loads(spec_path.read_text())
            ground_truth_code = ground_truth_path.read_text()

            test_cases.append(
                EvaluationTestCase(
                    id=spec["id"],
                    name=spec["name"],
                    level=level_num,
                    intent=intent,
                    spec=spec,
                    ground_truth_path=ground_truth_path,
                    ground_truth_code=ground_truth_code,
                )
            )

    return test_cases


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for STEP files and verification outputs."""
    output_dir = tmp_path / "verification_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def cadquery_tool() -> CadQueryExecutor:
    """CadQuery code executor."""
    return CadQueryExecutor(timeout=60)


@pytest.fixture(scope="session")
def verification_orchestrator() -> VerificationRunner:
    """Verification runner with default config."""
    config = VerificationConfig(
        validate_schema=False,
        shacl=False,
        require_pmi=False,
        use_external_tools=False,
        units_length="mm",
        units_angle="deg",
    )
    return VerificationRunner(config)


@pytest.fixture(scope="session")
def verification_orchestrator_enhanced() -> VerificationRunner:
    """Verification runner with enhanced checks."""
    config = VerificationConfig(
        validate_schema=True,
        shacl=True,
        require_pmi=False,
        use_external_tools=True,
        units_length="mm",
        units_angle="deg",
    )
    return VerificationRunner(config)


@pytest.fixture(scope="session")
def confidence_calculator() -> ConfidenceAnalyzer:
    """Confidence score analyzer."""
    return ConfidenceAnalyzer()


@pytest.fixture
def sample_cadquery_code() -> str:
    """Sample CadQuery code for testing."""
    return """
import cadquery as cq

# Create simple box
result = cq.Workplane("XY").box(10, 10, 5)
"""


@pytest.fixture
def sample_cadquery_bracket() -> str:
    """Sample CadQuery bracket code (more complex)."""
    return """
import cadquery as cq

# Create mounting bracket
result = (
    cq.Workplane("XY")
    .box(50, 30, 5)
    .faces(">Z")
    .workplane()
    .hole(8)
    .faces(">Y")
    .workplane()
    .rect(20, 10, forConstruction=True)
    .vertices()
    .hole(4)
    .edges("|Z")
    .fillet(2)
)
"""
