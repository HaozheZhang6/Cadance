"""
Smoke-test all registered families across XY / YZ / XZ base planes.
For each family × plane, builds easy+medium+hard, checks bbox is non-degenerate.
Prints a summary table: PASS / FAIL per family × plane.
"""
import sys, traceback
import numpy as np

sys.path.insert(0, "/workspace/scripts/data_generation")
sys.path.insert(0, "/workspace")

PLANES = ["XY", "YZ", "XZ"]
DIFFS  = ["easy", "medium", "hard"]

# Families known to be sweep-path-sensitive — still test but flag separately
SWEEP_FAMILIES = {"coil_spring", "worm_screw", "pipe_elbow", "t_pipe_fitting", "propeller", "bellows"}


def test_family(fam_name: str) -> dict:
    """Sample params once per diff, build all 3 planes. Returns {plane: (ok, msg)}."""
    from scripts.data_generation.cad_synth.pipeline.registry import get_family
    from scripts.data_generation.cad_synth.pipeline.builder import build_from_program

    fam = get_family(fam_name)
    plane_errs = {p: [] for p in PLANES}

    for diff in DIFFS:
        # Try multiple seeds; use first that produces valid params
        base_params = None
        for trial in range(5):
            seed = hash((fam_name, diff, trial)) & 0xFFFFFFFF
            local_rng = np.random.default_rng(seed)
            try:
                p = fam.sample_params(diff, local_rng)
                if fam.validate_params(p):
                    base_params = p
                    break
            except Exception:
                pass
        if base_params is None:
            for p in PLANES:
                plane_errs[p].append(f"{diff}:invalid_params(all_trials)")
            continue

        for plane in PLANES:
            params = {**base_params, "base_plane": plane}
            try:
                prog = fam.make_program(params)
                prog.base_plane = plane
                wp = build_from_program(prog)
                bb = wp.val().BoundingBox()
                dims = [bb.xlen, bb.ylen, bb.zlen]
                if any(d < 0.5 for d in dims):
                    plane_errs[plane].append(
                        f"{diff}:degenerate({dims[0]:.1f},{dims[1]:.1f},{dims[2]:.1f})"
                    )
            except Exception as e:
                plane_errs[plane].append(f"{diff}:{type(e).__name__}({str(e)[:60]})")

    return {p: (len(plane_errs[p]) == 0, "; ".join(plane_errs[p])) for p in PLANES}


def main():
    from scripts.data_generation.cad_synth.pipeline.registry import list_families

    families = sorted(list_families())
    print(f"Testing {len(families)} families × {len(PLANES)} planes\n")

    results = {}  # family → {plane: (ok, msg)}
    for fam in families:
        results[fam] = test_family(fam)
        row = "  ".join(
            ("✓" if results[fam][p][0] else "✗") + p
            for p in PLANES
        )
        sweep_tag = " [sweep]" if fam in SWEEP_FAMILIES else ""
        print(f"{fam:<28} {row}{sweep_tag}")
        if not all(results[fam][p][0] for p in PLANES):
            for p in PLANES:
                ok, msg = results[fam][p]
                if not ok:
                    print(f"  {p}: {msg}")

    # Summary
    print("\n--- SUMMARY ---")
    all_pass = [f for f in families if all(results[f][p][0] for p in PLANES)]
    xy_only  = [f for f in families if results[f]["XY"][0] and not all(results[f][p][0] for p in PLANES)]
    broken   = [f for f in families if not results[f]["XY"][0]]
    print(f"All-plane pass : {len(all_pass):3d}  {all_pass}")
    print(f"XY-only (partial): {len(xy_only):3d}  {xy_only}")
    print(f"XY broken      : {len(broken):3d}  {broken}")


if __name__ == "__main__":
    main()
