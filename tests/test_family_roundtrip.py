"""Per-family roundtrip unit test — runs ONCE per family in CI, replacing the
expensive per-sample `validate_roundtrip` in pool_runner.

For each `simple_*` family in the registry, we sample params at all 3
difficulties, build via `family.build(params)`, emit gt_code via
`render_program_to_code`, exec the emitted code in a fresh namespace, and
compare face counts. Any divergence indicates a bug in either family code
or the emitter.

If this test passes, we trust roundtrip per-family — pool_runner can skip
per-sample roundtrip and rely on the unit test.
"""

from __future__ import annotations

import numpy as np
import pytest

from scripts.data_generation.cad_synth.pipeline.builder import render_program_to_code
from scripts.data_generation.cad_synth.pipeline.registry import (
    get_family,
    list_families,
)


SIMPLE_FAMILIES = sorted(f for f in list_families() if f.startswith("simple_"))


def _exec_code(code: str):
    code_clean = "\n".join(
        line
        for line in code.splitlines()
        if line.strip() not in ("import cadquery as cq", "import cadquery")
    )
    import cadquery as cq

    globs = {"cq": cq, "show_object": lambda *a, **kw: None}
    exec(compile(code_clean, "<roundtrip>", "exec"), globs)
    return globs.get("result") or globs.get("r")


@pytest.mark.parametrize("fam_name", SIMPLE_FAMILIES)
def test_family_roundtrip(fam_name: str) -> None:
    """For each (family, difficulty), sample → build → emit code → exec →
    compare face counts. ±2 face tolerance for chamfer/fillet rounding.
    """
    fam = get_family(fam_name)
    failures: list[str] = []
    for diff in ("easy", "medium", "hard"):
        # Try up to 8 params samples per difficulty; skip if no valid params.
        rng = np.random.default_rng(hash((fam_name, diff)) % (2**31))
        params = None
        for _ in range(8):
            cand = fam.sample_params(diff, rng)
            if fam.validate_params(cand):
                params = cand
                break
        if params is None:
            continue  # family has no valid params at this difficulty — skip

        if "base_plane" not in params:
            params["base_plane"] = "XY"

        try:
            program = fam.make_program(params)
            wp = fam.build(params)
            code = render_program_to_code(program)
            r = _exec_code(code)
        except Exception as e:
            failures.append(f"{diff}: build/exec failed — {type(e).__name__}: {str(e)[:80]}")
            continue

        if r is None:
            failures.append(f"{diff}: emitted code did not produce 'result'")
            continue

        wp_faces = len(wp.val().Faces())
        r_faces = len(r.val().Faces())
        if abs(wp_faces - r_faces) > 2:
            failures.append(f"{diff}: face mismatch wp={wp_faces} code={r_faces}")

    assert not failures, f"family={fam_name}: " + "; ".join(failures)
