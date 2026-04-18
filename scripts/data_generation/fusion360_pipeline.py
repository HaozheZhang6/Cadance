#!/usr/bin/env python
"""End-to-end Fusion 360 -> JSON -> CadQuery -> STEP -> orthographic drawings.

Outputs:
- processed/json/<stem>.json (deterministic schema with cadquery_code)
- processed/cadquery/<stem>.py
- processed/step/<stem>.step
- processed/drawings/<stem>_{front,right,top}.svg

This initial pipeline only supports profiles with a single loop and curves of
Circle3D, Line3D, or Arc3D, and extrudes with OneSide or Symmetric extents.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SUPPORTED_CURVES = {"Circle3D", "Line3D"}
SUPPORTED_EXTENTS = {"OneSideFeatureExtentType", "SymmetricFeatureExtentType"}
SUPPORTED_OPS = {
    "NewBodyFeatureOperation": "new",
    "JoinFeatureOperation": "join",
    "CutFeatureOperation": "cut",
}


@dataclass(frozen=True)
class SketchPlane:
    origin: tuple[float, float, float]
    x_axis: tuple[float, float, float]
    y_axis: tuple[float, float, float]
    z_axis: tuple[float, float, float]
    name: str | None


def _vec(v: dict) -> tuple[float, float, float]:
    return (float(v["x"]), float(v["y"]), float(v["z"]))


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _to_local(
    pt: tuple[float, float, float],
    origin: tuple[float, float, float],
    x_axis: tuple[float, float, float],
    y_axis: tuple[float, float, float],
    z_axis: tuple[float, float, float],
    fallback_xy: bool,
) -> tuple[float, float]:
    if fallback_xy:
        return (pt[0], pt[1])
    v = _sub(pt, origin)
    d = _dot(v, z_axis)
    if abs(d) > 1e-3:
        return (pt[0], pt[1])
    return (_dot(v, x_axis), _dot(v, y_axis))


def _round(val: float) -> float:
    return round(float(val), 6)


def _plane_from_sketch(sketch: dict) -> SketchPlane:
    transform = sketch.get("transform") or {}
    origin = _vec(transform.get("origin", {"x": 0, "y": 0, "z": 0}))
    x_axis = _vec(transform.get("x_axis", {"x": 1, "y": 0, "z": 0}))
    y_axis = _vec(transform.get("y_axis", {"x": 0, "y": 1, "z": 0}))
    z_axis = _vec(transform.get("z_axis", {"x": 0, "y": 0, "z": 1}))
    ref = sketch.get("reference_plane", {})
    name = ref.get("name") if isinstance(ref, dict) else None
    return SketchPlane(origin, x_axis, y_axis, z_axis, name)


def _parse_profile_curves(
    loop: dict,
    plane: SketchPlane,
    fallback_xy: bool,
) -> list[dict[str, Any]] | None:
    curves = []
    for curve in loop.get("profile_curves", []):
        ctype = curve.get("type")
        if ctype not in SUPPORTED_CURVES:
            return None
        if ctype == "Circle3D":
            center = _vec(curve["center_point"])
            cx, cy = _to_local(center, plane.origin, plane.x_axis, plane.y_axis, plane.z_axis, fallback_xy)
            curves.append(
                {
                    "type": "circle",
                    "center": [_round(cx), _round(cy)],
                    "radius": _round(curve["radius"]),
                }
            )
        elif ctype == "Line3D":
            start = _vec(curve["start_point"])
            end = _vec(curve["end_point"])
            sx, sy = _to_local(start, plane.origin, plane.x_axis, plane.y_axis, plane.z_axis, fallback_xy)
            ex, ey = _to_local(end, plane.origin, plane.x_axis, plane.y_axis, plane.z_axis, fallback_xy)
            curves.append(
                {
                    "type": "line",
                    "start": [_round(sx), _round(sy)],
                    "end": [_round(ex), _round(ey)],
                }
            )
        elif ctype == "Arc3D":
            start = _vec(curve["start_point"])
            end = _vec(curve["end_point"])
            center = _vec(curve["center_point"])
            sx, sy = _to_local(start, plane.origin, plane.x_axis, plane.y_axis, plane.z_axis, fallback_xy)
            ex, ey = _to_local(end, plane.origin, plane.x_axis, plane.y_axis, plane.z_axis, fallback_xy)
            cx, cy = _to_local(center, plane.origin, plane.x_axis, plane.y_axis, plane.z_axis, fallback_xy)
            curves.append(
                {
                    "type": "arc",
                    "start": [_round(sx), _round(sy)],
                    "end": [_round(ex), _round(ey)],
                    "center": [_round(cx), _round(cy)],
                    "radius": _round(curve["radius"]),
                }
            )
    return curves


def _build_sketch_defs(entities: dict) -> dict[str, dict]:
    sketches = {}
    for ent_id, ent in entities.items():
        if ent.get("type") != "Sketch":
            continue
        plane = _plane_from_sketch(ent)
        fallback_xy = False
        for pt in ent.get("points", {}).values():
            vec = _vec(pt)
            v = _sub(vec, plane.origin)
            if abs(_dot(v, plane.z_axis)) > 1e-3:
                fallback_xy = True
                break
        sketch_profiles = []
        for prof in ent.get("profiles", {}).values():
            loops = prof.get("loops", [])
            if len(loops) != 1:
                continue
            loop = loops[0]
            curves = _parse_profile_curves(loop, plane, fallback_xy)
            if curves is None or not curves:
                continue
            sketch_profiles.append(
                {
                    "loops": [
                        {
                            "is_outer": bool(loop.get("is_outer", True)),
                            "curves": curves,
                        }
                    ]
                }
            )
        if sketch_profiles:
            sketches[ent_id] = {
                "id": ent_id,
                "plane": {
                    "origin": list(map(_round, plane.origin)),
                    "x_axis": list(map(_round, plane.x_axis)),
                    "y_axis": list(map(_round, plane.y_axis)),
                    "z_axis": list(map(_round, plane.z_axis)),
                    "name": plane.name,
                    "fallback_xy": fallback_xy,
                },
                "profiles": sketch_profiles,
            }
    return sketches


def _feature_from_extrude(ent: dict) -> dict | None:
    extent_type = ent.get("extent_type")
    if extent_type not in SUPPORTED_EXTENTS:
        return None
    op = SUPPORTED_OPS.get(ent.get("operation"))
    if op is None:
        return None

    extent_one = ent.get("extent_one", {})
    distance = None
    if isinstance(extent_one, dict):
        dist = extent_one.get("distance", {})
        if isinstance(dist, dict):
            distance = dist.get("value")
    if distance is None:
        return None

    profiles = ent.get("profiles", [])
    if not profiles:
        return None

    return {
        "type": "extrude",
        "profile": profiles[0],
        "operation": op,
        "extent_type": "symmetric" if extent_type == "SymmetricFeatureExtentType" else "one_side",
        "distance": _round(distance),
    }


def _convert_fusion_json(path: Path) -> tuple[dict | None, str | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sketches = _build_sketch_defs(data.get("entities", {}))
    if not sketches:
        return None, "no_sketches"

    features = []
    for step in data.get("sequence", []):
        if step.get("type") != "ExtrudeFeature":
            continue
        ent = data["entities"].get(step.get("entity"))
        if not ent:
            continue
        feature = _feature_from_extrude(ent)
        if feature is None:
            continue
        sketch_id = feature["profile"].get("sketch")
        profile_id = feature["profile"].get("profile")
        if sketch_id not in sketches:
            continue
        # Find profile index inside the sketch
        profiles = sketches[sketch_id]["profiles"]
        profile_index = 0
        for idx, _ in enumerate(profiles):
            # Profile IDs are not preserved in the simplified schema; pick first.
            profile_index = idx
            break
        features.append(
            {
                "type": "extrude",
                "sketch_id": sketch_id,
                "profile_index": profile_index,
                "operation": feature["operation"],
                "extent_type": feature["extent_type"],
                "distance": feature["distance"],
            }
        )

    if not features:
        return None, "no_features"

    return {
        "program_name": path.stem,
        "sketches": list(sketches.values()),
        "features": features,
    }, None


def _cadquery_plane_code(plane: dict) -> str:
    if plane.get("fallback_xy"):
        return 'cq.Workplane("XY")'
    name = plane.get("name")
    if name in {"XY", "YZ", "XZ"}:
        return f'cq.Workplane("{name}")'
    origin = plane["origin"]
    x_axis = plane["x_axis"]
    z_axis = plane["z_axis"]
    return (
        "cq.Workplane(cq.Plane("
        f"origin=({origin[0]}, {origin[1]}, {origin[2]}), "
        f"xDir=({x_axis[0]}, {x_axis[1]}, {x_axis[2]}), "
        f"normal=({z_axis[0]}, {z_axis[1]}, {z_axis[2]})))"
    )


def _arc_midpoint(start: tuple[float, float], end: tuple[float, float], center: tuple[float, float]) -> tuple[float, float]:
    ax = math.atan2(start[1] - center[1], start[0] - center[0])
    bx = math.atan2(end[1] - center[1], end[0] - center[0])
    delta = math.atan2(math.sin(bx - ax), math.cos(bx - ax))
    mid = ax + 0.5 * delta
    r = math.hypot(start[0] - center[0], start[1] - center[1])
    return (center[0] + r * math.cos(mid), center[1] + r * math.sin(mid))


def _build_profile_code(curves: list[dict]) -> list[str]:
    lines = []
    if len(curves) == 1 and curves[0]["type"] == "circle":
        r = curves[0]["radius"]
        lines.append(f"wp = wp.circle({r})")
        return lines

    current = None
    for curve in curves:
        ctype = curve["type"]
        if ctype not in {"line"}:
            return []
        start = curve.get("start")
        end = curve.get("end")
        if start is None or end is None:
            return []
        sx, sy = start
        ex, ey = end
        if current is None or abs(current[0] - sx) > 1e-6 or abs(current[1] - sy) > 1e-6:
            lines.append(f"wp = wp.moveTo({sx}, {sy})")
        if ctype == "line":
            lines.append(f"wp = wp.lineTo({ex}, {ey})")
        current = (ex, ey)

    lines.append("wp = wp.close()")
    return lines


def _generate_cadquery(program: dict) -> str | None:
    sketches = {sk["id"]: sk for sk in program["sketches"]}
    code = ["import cadquery as cq", "", "result = None", ""]

    for idx, feat in enumerate(program["features"]):
        sketch = sketches.get(feat["sketch_id"])
        if sketch is None:
            return None
        plane_code = _cadquery_plane_code(sketch["plane"])
        profiles = sketch["profiles"]
        if feat["profile_index"] >= len(profiles):
            return None
        loop = profiles[feat["profile_index"]]["loops"][0]
        curves = loop["curves"]

        code.append(f"# Feature {idx}: extrude")
        code.append(f"wp = {plane_code}")
        profile_lines = _build_profile_code(curves)
        if not profile_lines:
            return None
        code.extend(profile_lines)

        distance = feat["distance"]
        if feat["extent_type"] == "symmetric":
            code.append(f"solid = wp.extrude({distance}, both=True)")
        else:
            code.append(f"solid = wp.extrude({distance})")

        op = feat["operation"]
        if op in {"new", "join"}:
            code.append("result = solid if result is None else result.union(solid)")
        elif op == "cut":
            code.append("result = result.cut(solid) if result is not None else solid")
        else:
            return None
        code.append("")

    code.append("result = result")
    return "\n".join(code) + "\n"


def _run_executor(python_bin: Path, executor_py: Path, code: str, step_path: Path) -> dict:
    payload = {"mode": "execute", "code": code, "step_output_path": str(step_path)}
    import os

    env = dict(os.environ)
    repo_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH','')}"
    proc = subprocess.run(
        [str(python_bin), str(executor_py)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0 and not proc.stdout:
        return {"success": False, "error_message": proc.stderr.strip()}
    stdout = proc.stdout.strip()
    if stdout:
        # Some OCCT exporters print to stdout; extract the last JSON line.
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
    return {"success": False, "error_message": (stdout or proc.stderr).strip()}


def _render_orthographic(python_bin: Path, script: Path, step_path: Path, out_dir: Path, png: bool) -> None:
    cmd = [str(python_bin), str(script), "--step", str(step_path), "--out-dir", str(out_dir)]
    if png:
        cmd.append("--png")
    subprocess.run(cmd, check=False, capture_output=True, text=True)


def _render_isometric(python_bin: Path, script: Path, step_path: Path, out_dir: Path) -> None:
    cmd = [str(python_bin), str(script), "--step", str(step_path), "--out-dir", str(out_dir)]
    subprocess.run(cmd, check=False, capture_output=True, text=True)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/data_generation/open_source/fusion360_gallery/processed"),
    )
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--render", action="store_true", help="Render orthographic drawings")
    parser.add_argument("--png", action="store_true", help="Convert SVG drawings to PNG")
    parser.add_argument("--iso", action="store_true", help="Render isometric PNG view")
    parser.add_argument("--debug", action="store_true", help="Log skip reasons")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    python_bin = Path(sys.executable)
    executor_py = repo_root / "tools" / "cadquery" / "executor.py"
    render_script = repo_root / "scripts" / "data_generation" / "render_orthographic_drawings.py"
    iso_script = repo_root / "scripts" / "data_generation" / "render_isometric_views.py"

    json_out = args.output_dir / "json"
    cad_out = args.output_dir / "cadquery"
    step_out = args.output_dir / "step"
    draw_out = args.output_dir / "drawings"
    iso_out = args.output_dir / "isometric"
    for p in [json_out, cad_out, step_out, draw_out, iso_out]:
        _ensure_dir(p)

    processed = 0
    kept = 0
    skipped = 0
    skip_reasons: dict[str, int] = {}

    for path in sorted(args.input_dir.glob("*.json")):
        if processed >= args.limit:
            break
        processed += 1
        program, reason = _convert_fusion_json(path)
        if program is None:
            skipped += 1
            if reason:
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            continue
        code = _generate_cadquery(program)
        if code is None:
            skipped += 1
            skip_reasons["codegen_failed"] = skip_reasons.get("codegen_failed", 0) + 1
            continue

        stem = path.stem
        json_path = json_out / f"{stem}.json"
        cad_path = cad_out / f"{stem}.py"
        step_path = step_out / f"{stem}.step"

        program["cadquery_code"] = code
        program["cadquery_path"] = str(cad_path)

        json_path.write_text(json.dumps(program, indent=2), encoding="utf-8")
        cad_path.write_text(code, encoding="utf-8")

        result = _run_executor(python_bin, executor_py, code, step_path)
        if not result.get("success"):
            skipped += 1
            skip_reasons["cadquery_failed"] = skip_reasons.get("cadquery_failed", 0) + 1
            continue

        if args.render:
            _render_orthographic(python_bin, render_script, step_path, draw_out, args.png)
        if args.iso:
            _render_isometric(python_bin, iso_script, step_path, iso_out)

        kept += 1

    summary = {
        "processed": processed,
        "kept": kept,
        "skipped": skipped,
        "output_dir": str(args.output_dir),
    }
    if args.debug:
        summary["skip_reasons"] = skip_reasons
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
