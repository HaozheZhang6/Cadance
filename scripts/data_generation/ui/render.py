"""Run CQ code → STEP → normalized composite PNG."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LD = "/workspace/.local/lib"


def _patch_export(code: str, out_step: str) -> str:
    """Replace last exportStep call to write to out_step."""
    patched = re.sub(
        r'(\.exportStep\s*\()["\'].*?["\']\)',
        f'.exportStep("{out_step}")',
        code,
    )
    if ".exportStep" not in patched:
        patched += f'\nresult.val().exportStep("{out_step}")\n'
    return patched


def run_cq(cq_path: str, timeout: int = 90) -> tuple[str | None, str | None]:
    """Execute CQ file. Returns (step_path, error). step_path is a temp file."""
    code = Path(cq_path).read_text()
    step_tmp = tempfile.mktemp(suffix=".step")
    patched = _patch_export(code, step_tmp)

    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    try:
        r = subprocess.run(
            [sys.executable, "-c", patched],
            env=env,
            timeout=timeout,
            capture_output=True,
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"

    if r.returncode != 0 or not Path(step_tmp).exists():
        return None, r.stderr.decode(errors="replace")[:800]

    return step_tmp, None


def render_step(step_path: str, out_dir: str) -> str | None:
    """Render STEP → composite.png. Returns composite path or None."""
    sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))
    try:
        from render_normalized_views import render_step_normalized
        paths = render_step_normalized(step_path, out_dir)
        return paths["composite"]
    except Exception as e:
        return None


def render_cq(cq_path: str, out_dir: str) -> tuple[str | None, str | None]:
    """Execute CQ → render → save composite. Returns (composite_path, error)."""
    step, err = run_cq(cq_path)
    if err:
        return None, err
    composite = render_step(step, out_dir)
    Path(step).unlink(missing_ok=True)
    return composite, None
