"""Programmatic example for DAG multi-agent orchestrator."""

from __future__ import annotations

from src.orchestrator.orchestrator import MultiAgentOrchestrator


def main() -> None:
    intent = "Design a mounting bracket for a 5kg load"
    orchestrator = MultiAgentOrchestrator(mock_llm=True)
    result = orchestrator.run(intent)
    print(f"Run dir: {result.run_dir}")
    print(f"Final sigma: {result.sigma:.2f}")
    if result.artifacts:
        print("Artifacts:")
        for path in result.artifacts:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
