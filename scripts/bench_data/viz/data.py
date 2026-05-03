"""Data loaders for BenchCAD viz."""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/data_generation"


def synth_parts() -> pd.DataFrame:
    df = pd.read_csv(DATA / "synth_parts.csv")
    df["macro"] = df["family"].apply(bucket_family)
    return df


def bench_subset_meta() -> dict:
    return json.loads((DATA / "bench_subset_1200.json").read_text())


def bucket_family(name: str) -> str:
    """Keyword-based bucketing — covers all 112 families in synth_parts.csv.

    6 macro buckets aligned with mechanical-engineering taxonomy:
      fastener  | rotational  | plate_panel | section_channel | pipe_tube | block_assembly
    """
    n = name.lower()
    # 1. fasteners (most specific first)
    if any(k in n for k in ("bolt", "screw", "nut", "rivet", "washer",
                              "stud", "cotter", "pin_", "_pin", "split_pin",
                              "anchor", "set_screw")):
        return "fastener"
    # 2. plates / panels / sheets
    if any(k in n for k in ("plate", "panel", "sheet", "corrugat")):
        return "plate_panel"
    # 3. pipes / tubes / hollow
    if any(k in n for k in ("pipe", "duct", "elbow", "fitting",
                              "_tube", "tube_", "hollow_pipe", "split_tube",
                              "radial_holes_tube")):
        return "pipe_tube"
    # 4. extruded sections / channels / beams
    if any(k in n for k in ("section", "channel", "beam", "_strip",
                              "unistrut", "_hat", "hat_section", "wedge",
                              "obelisk", "pyramid", "step_solid", "_t_solid",
                              "_l_solid")):
        return "section_channel"
    # 5. cylindrical / rotational
    if any(k in n for k in ("shaft", "ring", "_disc", "disc_", "knob",
                              "cam", "piston", "spring", "gear", "pulley",
                              "sprocket", "wheel", "flange", "bearing",
                              "cylinder", "cone", "frustum", "hemisphere",
                              "drill", "rotor", "impeller", "propeller", "lobe",
                              "_lid", "lid_", "ball_knob", "ball", "spindle",
                              "torus", "annulus", "axle", "worm", "boss",
                              "spline", "skirt", "yoke")):
        return "rotational"
    # 6. assemblies / blocks / brackets / frames / holders
    if any(k in n for k in ("block", "bracket", "frame", "chair", "stand",
                              "clevis", "bin", "hinge", "latch", "holder",
                              "retainer", "battery", "house", "pegs", "_studs",
                              "studs_", "locator", "phone", "gridfinity",
                              "wall_", "_link", "link_", "flat_link",
                              "rect_frame", "open_box", "box_section",
                              "capsule", "bellows", "funnel", "bucket",
                              "grommet", "nozzle", "grease", "eyebolt",
                              "dovetail", "v_block", "handle", "button",
                              "arrow", "_d_shape", "diamond", "chevron",
                              "crescent", "cross_plate", "dogbone", "_shape",
                              "stadium", "trapezoid", "parallelogram", "house_plate",
                              "pie_slice", "n_star", "keyhole", "y_shape",
                              "z_section_struct", "twisted", "multi_extrude")):
        return "block_assembly"
    return "block_assembly"  # default fallback (better than "other")
