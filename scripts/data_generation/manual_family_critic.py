"""Heuristic critic for manual family prototypes.

This is not a vision model. It is a reproducible checklist runner that ties:
1. family-specific real-world reference notes
2. code-level structural expectations
3. a manual visual review checklist against a rendered PNG

Usage:
  uv run python scripts/data_generation/manual_family_critic.py \
    --family bellows \
    --code tmp/manual_family_previews/manual_bellows.py \
    --image tmp/manual_family_previews/rendered_bellows/composite.png
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


RULES = {
    "pipe_elbow": {
        "reference_summary": [
            "Real flanged elbows are continuous bent pipes with two coaxial end connections.",
            "End flanges sit square to each pipe axis and bolt holes are normal to the flange face.",
            "The bend should read as one swept flow path, not detached cylinders with floating plates.",
        ],
        "code_checks": [
            ("uses_torus_or_sweep_bend", r"makeTorus|sweep\("),
            ("has_two_end_flanges", r"flange_x|flange_z"),
            ("cuts_through_bore", r"cut\(.*inner|leg_x_inner|leg_z_inner"),
            ("cuts_bolt_holes", r"bolt_hole_radius|bolt_count"),
        ],
        "visual_checks": [
            "The two flanges look attached to the elbow, not hovering near it.",
            "Each flange face is perpendicular to its own pipe axis.",
            "The centerline bend reads as 90 or 45 degrees, not a crooked branch.",
        ],
    },
    "bellows": {
        "reference_summary": [
            "Metal expansion joints are built around one or more bellows plus connectors at both ends.",
            "The bellows body is hollow and the end flanges usually provide bolt patterns and sealing land.",
            "Flange margin should remain visibly wider than the bore and bolt holes.",
        ],
        "code_checks": [
            ("uses_outer_inner_profiles", r"outer_profile|inner_profile"),
            ("uses_revolve", r"revolve\("),
            ("makes_hollow_body", r"cut\(inner\)|outer\.cut\(inner\)"),
            ("cuts_bolt_holes", r"bolt_count|bolt_hole_radius"),
        ],
        "visual_checks": [
            "Both ends are visibly open and the body is truly through-bored.",
            "Bolt holes are not too close to the flange edge or bore.",
            "Convolutions read as a bellows, not a stack of washers.",
        ],
    },
    "threaded_adapter": {
        "reference_summary": [
            "Real threaded adapters read as one continuous fitting body with shoulders and connection ends.",
            "Threads should appear as shallow helical surface detail, not floating rings or a spring.",
            "Both threaded stubs need clear continuity into the hex or central body.",
        ],
        "code_checks": [
            ("has_hex_body", r"polygon\(6"),
            ("has_continuous_shoulders", r"shoulder|blend|loft"),
            ("has_thread_logic", r"makeHelix|sweep\(|thread"),
            ("has_center_bore", r"hole\("),
        ],
        "visual_checks": [
            "Neither threaded end looks detached from the hex body.",
            "Thread detail hugs the cylinder surface instead of floating outside it.",
            "The part reads as a fitting/adapter, not a hex block with random stubs.",
        ],
    },
    "lathe_turned_part": {
        "reference_summary": [
            "A turned part should read as an axial sequence of shoulders, lands, grooves, chamfers, and bores.",
            "The geometry should be rotationally symmetric except for optional keyways or flats.",
            "A relief groove and counterbore usually help it read as a real machined part rather than an abstract mushroom.",
        ],
        "code_checks": [
            ("uses_profile_revolve", r"Workplane\\(\"XZ\"\\)|revolve\("),
            ("has_relief_or_groove", r"relief"),
            ("has_bore", r"hole\("),
            ("has_chamfer_or_counterbore", r"chamfer|counterbore"),
        ],
        "visual_checks": [
            "The axial silhouette has multiple meaningful shoulders, not one smooth blob.",
            "Front and back read as machined faces with clear diameter changes.",
            "The part could plausibly come off a lathe.",
        ],
    },
    "manifold_block": {
        "reference_summary": [
            "Hydraulic manifolds are blocks with drilled flow paths connecting multiple ports.",
            "Port bosses should be obvious and the block should suggest orthogonal drilling directions.",
            "A plain wedge with a few holes is too weak; the routing intent should be visible.",
        ],
        "code_checks": [
            ("has_block_body", r"box\(|polyline\("),
            ("has_multiple_ports", r"main_port_x|side_port_z"),
            ("has_bosses", r"pad"),
            ("cuts_drilled_passages", r"cut\("),
        ],
        "visual_checks": [
            "Ports are clearly grouped and aligned like a manifold, not random decorative holes.",
            "Top and side bosses look intentional and connected to drilled passages.",
            "The block reads as fluid routing hardware.",
        ],
    },
    "cam": {
        "reference_summary": [
            "A cam should have a deliberate non-circular lobe profile around a shaft bore.",
            "A hub and keyway often help the part read as a driven cam rather than a decorative disc.",
            "The lobe should be visually directional and asymmetric.",
        ],
        "code_checks": [
            ("uses_non_circular_profile", r"polyline\(pts\)"),
            ("has_shaft_bore", r"shaft_bore|hole\("),
            ("has_keyway", r"keyway|box\("),
            ("has_hub", r"hub"),
        ],
        "visual_checks": [
            "The outer silhouette is obviously cam-like, not nearly circular.",
            "The bore, keyway, and hub make the drive direction legible.",
            "The primary lobe dominates the profile.",
        ],
    },
}


def run_checks(code: str, family: str) -> list[dict]:
    checks = []
    for name, pattern in RULES[family]["code_checks"]:
        ok = re.search(pattern, code, flags=re.S) is not None
        checks.append({"name": name, "ok": ok})
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description="Critique manual family code + render against real-world heuristics")
    ap.add_argument("--family", required=True, choices=sorted(RULES))
    ap.add_argument("--code", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    args = ap.parse_args()

    code_path = Path(args.code).resolve()
    image_path = Path(args.image).resolve()
    code = code_path.read_text()
    rule = RULES[args.family]
    results = run_checks(code, args.family)

    report = {
        "family": args.family,
        "code_path": str(code_path),
        "image_path": str(image_path),
        "reference_summary": rule["reference_summary"],
        "code_checks": results,
        "visual_checks": rule["visual_checks"],
        "failed_code_checks": [x["name"] for x in results if not x["ok"]],
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"# Critic Report: {args.family}")
    print()
    print(f"- code: {code_path}")
    print(f"- image: {image_path}")
    print()
    print("## Real-world cues")
    for line in rule["reference_summary"]:
        print(f"- {line}")
    print()
    print("## Code checks")
    for item in results:
        mark = "PASS" if item["ok"] else "FAIL"
        print(f"- [{mark}] {item['name']}")
    print()
    print("## Visual checklist")
    for line in rule["visual_checks"]:
        print(f"- [ ] {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
