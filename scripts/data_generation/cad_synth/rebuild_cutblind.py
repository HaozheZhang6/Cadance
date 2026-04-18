"""Rebuild STEP + code artifacts for s1502 samples affected by cutBlind sign bug.

Targets: helical_gear medium+hard and bevel_gear medium+hard from synth_gears_kw_s1502.
These had web_recess / bearing_seat cutBlind ops that cut into empty space (positive depth).
builder.py now auto-negates, so re-running make_program + build_from_program produces correct geometry.

Usage:
    export PATH="$HOME/.local/bin:$PATH"
    LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 \
        scripts/data_generation/cad_synth/rebuild_cutblind.py [--dry-run]
"""

import argparse
import json
import sys
import traceback
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def _patch_ocp_hashcode():
    from OCP.TopoDS import (
        TopoDS_Compound, TopoDS_CompSolid, TopoDS_Edge, TopoDS_Face,
        TopoDS_Shape, TopoDS_Shell, TopoDS_Solid, TopoDS_Vertex, TopoDS_Wire,
    )
    for cls in [
        TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
        TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid,
    ]:
        if not hasattr(cls, "HashCode"):
            cls.HashCode = lambda self, ub=2147483647: id(self) % ub


def rebuild_one(row, dry_run: bool) -> str:
    """Rebuild one sample. Returns 'ok', 'skip', or 'fail:<msg>'."""
    import cadquery as cq
    from scripts.data_generation.cad_synth.pipeline.builder import (
        build_from_program, render_program_to_code,
    )
    from scripts.data_generation.cad_synth.pipeline.registry import get_family

    _patch_ocp_hashcode()

    family_name = row["family"]
    params = json.loads(row["params_json"])

    step_path = ROOT / row["step_path"]
    code_path = ROOT / row["code_path"]
    gt_step = step_path.parent.parent / "gt" / "gt.step"

    if dry_run:
        return "dry-ok"

    fam = get_family(family_name)
    prog = fam.make_program(params)
    wp = build_from_program(prog)

    # Export STEP
    step_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(wp, str(step_path), exportType=cq.exporters.ExportTypes.STEP)

    # Sync GT STEP
    import shutil
    gt_step.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(step_path, gt_step)

    # Export code
    code = render_program_to_code(prog)
    code_path.write_text(code)

    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Parse only, no writes")
    ap.add_argument("--families", nargs="+",
                    default=["helical_gear", "bevel_gear"],
                    help="Families to rebuild")
    ap.add_argument("--difficulties", nargs="+",
                    default=["medium", "hard"],
                    help="Difficulties to rebuild")
    ap.add_argument("--run", default="synth_gears_kw_s1502")
    args = ap.parse_args()

    csv_path = ROOT / "data" / "data_generation" / "synth_parts.csv"
    df = pd.read_csv(csv_path)

    mask = (
        df["pipeline_run"].eq(args.run)
        & df["family"].isin(args.families)
        & df["difficulty"].isin(args.difficulties)
        & df["status"].eq("accepted")
        & df["step_path"].notna()
    )
    targets = df[mask].reset_index(drop=True)
    print(f"Targets: {len(targets)} rows")
    print(targets.groupby(["family", "difficulty"]).size().to_string())

    ok = fail = skip = 0
    for idx, row in targets.iterrows():
        try:
            result = rebuild_one(row, args.dry_run)
            if result.startswith("ok") or result == "dry-ok":
                ok += 1
            elif result == "skip":
                skip += 1
            else:
                fail += 1
                print(f"  FAIL gid={row['gid']}: {result}")
        except Exception as e:
            fail += 1
            print(f"  FAIL gid={row['gid']} ({row['family']} {row['difficulty']}): {e}")
            if fail <= 5:
                traceback.print_exc()

        if (ok + fail + skip) % 50 == 0:
            print(f"  progress: ok={ok} fail={fail} skip={skip} / {len(targets)}")

    print(f"\ndone: ok={ok} fail={fail} skip={skip}")


if __name__ == "__main__":
    main()
