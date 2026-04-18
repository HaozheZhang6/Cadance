"""Execute CadQuery code safely and export STEP files."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Project root for adding to PYTHONPATH
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()


@dataclass
class CadQueryResult:
    """Result from CadQuery code execution."""

    success: bool
    step_path: Path | None
    manifest_path: Path | None
    error: str | None
    stdout: str
    stderr: str


class CadQueryExecutor:
    """Execute CadQuery code in isolated subprocess."""

    def __init__(self, timeout: int = 30):
        """Initialize executor with timeout."""
        self.timeout = timeout

    def execute(self, code: str, output_dir: Path | None = None) -> CadQueryResult:
        """
        Execute CadQuery code and export STEP file.

        Args:
            code: CadQuery Python code to execute
            output_dir: Output directory for STEP file (temp if None)

        Returns:
            CadQueryResult with execution status and paths
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        step_path = output_dir / "output.step"
        manifest_path = output_dir / "manifest.json"

        # Build Python script that executes code
        script = self._build_script(code, step_path, manifest_path)
        script_path = output_dir / "script.py"
        script_path.write_text(script, encoding="utf-8")

        try:
            # Add project root to PYTHONPATH for compat modules
            env = os.environ.copy()
            pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                f"{_PROJECT_ROOT}:{pythonpath}" if pythonpath else str(_PROJECT_ROOT)
            )

            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=output_dir,
                env=env,
            )

            if result.returncode != 0:
                return CadQueryResult(
                    success=False,
                    step_path=None,
                    manifest_path=None,
                    error=f"CadQuery script failed: {result.stderr}",
                    stdout=result.stdout,
                    stderr=result.stderr,
                )

            if not step_path.exists():
                return CadQueryResult(
                    success=False,
                    step_path=None,
                    manifest_path=None,
                    error="STEP file not generated",
                    stdout=result.stdout,
                    stderr=result.stderr,
                )

            return CadQueryResult(
                success=True,
                step_path=step_path,
                manifest_path=manifest_path if manifest_path.exists() else None,
                error=None,
                stdout=result.stdout,
                stderr=result.stderr,
            )

        except subprocess.TimeoutExpired:
            return CadQueryResult(
                success=False,
                step_path=None,
                manifest_path=None,
                error=f"Execution timeout after {self.timeout}s",
                stdout="",
                stderr="",
            )
        except Exception as e:
            return CadQueryResult(
                success=False,
                step_path=None,
                manifest_path=None,
                error=f"Execution error: {e}",
                stdout="",
                stderr="",
            )

    def _build_script(self, code: str, step_path: Path, manifest_path: Path) -> str:
        """Build Python script that executes CadQuery code and exports STEP."""
        return f"""
import json
import sys
from pathlib import Path

# Apply OCP 7.9.x compatibility patch before importing cadquery
try:
    import src.compat.cadquery_ocp79  # noqa: F401
except ImportError:
    pass

try:
    import cadquery as cq
except ImportError:
    print("ERROR: cadquery not installed", file=sys.stderr)
    sys.exit(1)

# Execute user code
result = None
try:
{self._indent_code(code, "    ")}
except Exception as e:
    print(f"ERROR: CadQuery code execution failed: {{e}}", file=sys.stderr)
    sys.exit(1)

# Export STEP file
if result is None:
    print("ERROR: CadQuery code did not produce a result", file=sys.stderr)
    sys.exit(1)

try:
    step_path = Path("{step_path}")
    if hasattr(result, "val"):
        # Workplane/Assembly
        cq.exporters.export(result, str(step_path))
    else:
        # Shape
        cq.exporters.export(cq.Workplane("XY").add(result), str(step_path))

    # Create manifest with basic metadata
    manifest = {{
        "schema_version": "cadquery.manifest.v1",
        "parts": [
            {{
                "index": 0,
                "part_id": "cadquery_part_0",
                "name": "generated_part"
            }}
        ]
    }}
    manifest_path = Path("{manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"SUCCESS: STEP exported to {{step_path}}")
except Exception as e:
    print(f"ERROR: STEP export failed: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

    @staticmethod
    def _indent_code(code: str, indent: str) -> str:
        """Indent code block."""
        lines = code.strip().split("\n")
        return "\n".join(indent + line for line in lines)
