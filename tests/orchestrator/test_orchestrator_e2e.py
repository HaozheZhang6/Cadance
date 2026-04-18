from __future__ import annotations

from pathlib import Path

from src.orchestrator.orchestrator import MultiAgentOrchestrator


def test_mocked_intent_to_cad_run(tmp_path: Path) -> None:
    orchestrator = MultiAgentOrchestrator(
        agent_runs_dir=tmp_path,
        mock_llm=True,
        max_agents=6,
    )

    result = orchestrator.run("Design a mounting bracket for a 5kg load")

    assert result.status == "complete"
    assert result.run_dir.exists()

    cad_dirs = [p for p in result.run_dir.iterdir() if p.name.startswith("cad_")]
    assert cad_dirs, "Expected a CAD agent workspace"

    artifacts_dir = cad_dirs[0] / "artifacts"
    assert artifacts_dir.exists()

    json_files = list(artifacts_dir.glob("*.json"))
    step_files = list(artifacts_dir.glob("*.step"))

    assert json_files, "Expected ops_program JSON artifact"
    assert step_files, "Expected STEP artifact"
