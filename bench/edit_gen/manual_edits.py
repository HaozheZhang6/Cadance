"""Hand-authored edits for individual families.

Each entry specifies the family, orig file, and the exact op_code to append.
Reviewed individually — we build one at a time, render, and check.

Outputs under data/data_generation/bench_edit/topup_manual/.
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from bench.edit_gen.topup_edits import exec_cq, splice_gt_code

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
OUT = BENCH / "topup_manual"


MANUAL_SPECS: list[dict] = [
    # === battery_holder ===
    # Already has: top_slot. Add: outer corner fillets (easy).
    {
        "record_id": "manual_battery_holder_corner_fillet",
        "family": "battery_holder",
        "orig": "battery_holder_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the four outer vertical corners by 4 mm.",
        "op_code": "result = result.edges('|Z').fillet(4.0)",
    },
    # === bearing_retainer_cap ===
    # Has: top_slot (medium). Add: top circle chamfer (easy).
    {
        "record_id": "manual_bearing_retainer_cap_top_chamfer",
        "family": "bearing_retainer_cap",
        "orig": "bearing_retainer_cap_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top circular edges of the hub by 1.2 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(1.2)",
    },
    # === bevel_gear ===
    # Has: top_slot. Add: widen bore (easy visible).
    {
        "record_id": "manual_bevel_gear_widen_bore",
        "family": "bevel_gear",
        "orig": "bevel_gear_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Widen the central bore to 14 mm diameter.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').cylinder(200.0, 7.0))"
        ),
    },
    # === bolt ===
    # Has: top_slot (slotted head). Add: outer fillet on hex head.
    {
        "record_id": "manual_bolt_head_fillet",
        "family": "bolt",
        "orig": "bolt_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the six vertical edges of the hex head by 5 mm.",
        "op_code": "result = result.edges('|Z').fillet(5.0)",
    },
    # === bucket ===
    # Revolved along Y. Add handle slot in wall + big top chamfer.
    {
        "record_id": "manual_bucket_handle_slot",
        "family": "bucket",
        "orig": "bucket_easy_r0_orig.py",
        "edit_type": "add_slot",
        "difficulty": "medium",
        "instruction": "Cut a 40×14 mm horizontal handle slot through the bucket wall near the top.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').transformed(offset=cq.Vector(0,70,0))"
            ".box(200.0, 14.0, 40.0))"
        ),
    },
    {
        "record_id": "manual_bucket_side_drain",
        "family": "bucket",
        "orig": "bucket_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Drill a 24 mm diameter drain hole through the side wall near the bottom.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').transformed(offset=cq.Vector(0,20,0))"
            ".cylinder(200.0, 12.0))"
        ),
    },
    # === cable_routing_panel === (plate 213×151×3.9, already has 5 slots)
    {
        "record_id": "manual_cable_routing_panel_corner_fillet",
        "family": "cable_routing_panel",
        "orig": "cable_routing_panel_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the four outer corner vertical edges by 6 mm.",
        "op_code": "result = result.edges('|Z').fillet(6.0)",
    },
    # === capsule === (already have 2 records in P2; skip)
    # === circlip === (thin ring 1.2mm thick, OD 33.5, ID 20) — very thin
    {
        "record_id": "manual_circlip_top_chamfer",
        "family": "circlip",
        "orig": "circlip_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top circular edges by 0.5 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(0.5)",
    },
    {
        "record_id": "manual_circlip_tool_hole",
        "family": "circlip",
        "orig": "circlip_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 5 mm tool hole through the ring tab near the gap.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').transformed(offset=cq.Vector(13,4,0))"
            ".cylinder(20.0, 2.5))"
        ),
    },
    # === clevis === (31×27.9×57.2 box with top cutout + holes)
    {
        "record_id": "manual_clevis_outer_fillet",
        "family": "clevis",
        "orig": "clevis_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the four outer vertical corners by 3 mm.",
        "op_code": "result = result.edges('|Z').fillet(3.0)",
    },
    # === clevis_pin === (5mm Ø × 100mm pin) — very thin
    {
        "record_id": "manual_clevis_pin_cross_hole",
        "family": "clevis_pin",
        "orig": "clevis_pin_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 2 mm cotter-pin hole through the pin near the end.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('YZ').transformed(offset=cq.Vector(0,0,45))"
            ".cylinder(20.0, 1.0))"
        ),
    },
    {
        "record_id": "manual_clevis_pin_extra_chamfer",
        "family": "clevis_pin",
        "orig": "clevis_pin_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Add a larger 1 mm chamfer to both end edges.",
        "op_code": "result = result.edges('%CIRCLE').chamfer(1.0)",
    },
    # === coil_spring === (helical sweep — hard to edit in place)
    # Skip — sweep geometry breaks most ops. Use rotation fallback later.
    # === connecting_rod === (dumbbell shape with 2 bores)
    {
        "record_id": "manual_connecting_rod_bore_chamfer",
        "family": "connecting_rod",
        "orig": "connecting_rod_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "medium",
        "instruction": "Chamfer the top circular bore edges by 0.5 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(0.5)",
    },
    {
        "record_id": "manual_connecting_rod_big_end_widen",
        "family": "connecting_rod",
        "orig": "connecting_rod_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Widen the big-end bore to 14 mm diameter.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').cylinder(50.0, 7.0))"
        ),
    },
    # === cotter_pin === (two 1.25mm Ø pins × 10mm)  — very thin
    {
        "record_id": "manual_cotter_pin_end_chamfer",
        "family": "cotter_pin",
        "orig": "cotter_pin_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the bottom circular edges by 0.3 mm.",
        "op_code": "result = result.edges('%CIRCLE and <Z').chamfer(0.3)",
    },
    {
        "record_id": "manual_cotter_pin_mid_chamfer",
        "family": "cotter_pin",
        "orig": "cotter_pin_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "medium",
        "instruction": "Chamfer the top circular edges by 0.3 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(0.3)",
    },
    # === cruciform === (plus shape plate — use existing in P2)
    # === dome_cap === (revolved Y-axis dome)
    {
        "record_id": "manual_dome_cap_top_bore",
        "family": "dome_cap",
        "orig": "dome_cap_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 20 mm diameter axial bore through the dome along its Y axis.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XZ').cylinder(300.0, 10.0))"
        ),
    },
    {
        "record_id": "manual_dome_cap_side_hole",
        "family": "dome_cap",
        "orig": "dome_cap_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Drill a 16 mm diameter hole through the dome side wall.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('XY').transformed(offset=cq.Vector(0,30,0))"
            ".cylinder(200.0, 8.0))"
        ),
    },
    # === Batch 3: 20 more families ===
    # cam — complex with hub+disc
    {
        "record_id": "manual_cam_outer_fillet",
        "family": "cam",
        "orig": "cam_hard_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the outer vertical edges by 2 mm.",
        "op_code": "result = result.edges('|Z').fillet(2.0)",
    },
    # capsule (already has 2 P2, but let's add if needed — skip)
    # double_simplex_sprocket
    {
        "record_id": "manual_double_simplex_sprocket_bore_widen",
        "family": "double_simplex_sprocket",
        "orig": "double_simplex_sprocket_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Widen the sprocket bore by drilling an 18 mm hole through the center.",
        "op_code": "result = result.cut(cq.Workplane('XY').cylinder(200.0, 9.0))",
    },
    # dovetail_slide (161.9mm along Z prism)
    {
        "record_id": "manual_dovetail_slide_top_slot",
        "family": "dovetail_slide",
        "orig": "dovetail_slide_easy_r0_orig.py",
        "edit_type": "add_slot",
        "difficulty": "medium",
        "instruction": "Cut a 120×16 mm slot 5 mm deep into the +Y top face.",
        "op_code": (
            "result = result.faces('>Y').workplane("
            "centerOption='CenterOfBoundBox')"
            ".slot2D(120.0, 16.0).cutBlind(-5.0)"
        ),
    },
    {
        "record_id": "manual_dovetail_slide_end_chamfer",
        "family": "dovetail_slide",
        "orig": "dovetail_slide_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top end-face edges by 2 mm.",
        "op_code": "result = result.faces('>Z').chamfer(2.0)",
    },
    # duct_elbow (revolve / sweep)
    {
        "record_id": "manual_duct_elbow_end_chamfer",
        "family": "duct_elbow",
        "orig": "duct_elbow_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer all circular edges by 2 mm.",
        "op_code": "result = result.edges('%CIRCLE').chamfer(2.0)",
    },
    # eyebolt
    {
        "record_id": "manual_eyebolt_shank_chamfer",
        "family": "eyebolt",
        "orig": "eyebolt_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer all circular edges by 0.8 mm.",
        "op_code": "result = result.edges('%CIRCLE').chamfer(0.8)",
    },
    {
        "record_id": "manual_eyebolt_cross_hole",
        "family": "eyebolt",
        "orig": "eyebolt_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 4 mm cross-hole through the shank.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('YZ').transformed(offset=cq.Vector(0,0,-10))"
            ".cylinder(50.0, 2.0))"
        ),
    },
    # fan_shroud (revolve/sweep)
    {
        "record_id": "manual_fan_shroud_outer_chamfer",
        "family": "fan_shroud",
        "orig": "fan_shroud_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the outer circular edges by 2 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(2.0)",
    },
    # gusseted_bracket (has P2 top_slot, need easy)
    {
        "record_id": "manual_gusseted_bracket_outer_fillet",
        "family": "gusseted_bracket",
        "orig": "gusseted_bracket_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the outer vertical edges by 3 mm.",
        "op_code": "result = result.edges('|Z').fillet(3.0)",
    },
    # handwheel
    {
        "record_id": "manual_handwheel_bore_widen",
        "family": "handwheel",
        "orig": "handwheel_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Widen the central bore to 20 mm diameter.",
        "op_code": "result = result.cut(cq.Workplane('XY').cylinder(200.0, 10.0))",
    },
    # heat_sink (plate with fins)
    {
        "record_id": "manual_heat_sink_corner_fillet",
        "family": "heat_sink",
        "orig": "heat_sink_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the four outer vertical corners by 3 mm.",
        "op_code": "result = result.edges('|Z').fillet(3.0)",
    },
    # helical_gear
    {
        "record_id": "manual_helical_gear_bore_widen",
        "family": "helical_gear",
        "orig": "helical_gear_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Widen the central bore to 12 mm diameter.",
        "op_code": "result = result.cut(cq.Workplane('XY').cylinder(200.0, 6.0))",
    },
    # hex_key_organizer
    {
        "record_id": "manual_hex_key_organizer_outer_fillet",
        "family": "hex_key_organizer",
        "orig": "hex_key_organizer_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the four outer vertical corners by 4 mm.",
        "op_code": "result = result.edges('|Z').fillet(4.0)",
    },
    # hex_nut (has P2 hole)
    {
        "record_id": "manual_hex_nut_top_chamfer",
        "family": "hex_nut",
        "orig": "hex_nut_hard_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top circular bore edge by 1 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(1.0)",
    },
    # hex_standoff (hex + bore)
    {
        "record_id": "manual_hex_standoff_cross_hole",
        "family": "hex_standoff",
        "orig": "hex_standoff_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 3 mm radial cross-hole through the side wall.",
        "op_code": (
            "result = result.cut("
            "cq.Workplane('YZ').cylinder(50.0, 1.5))"
        ),
    },
    # hinge (rotating joint)
    {
        "record_id": "manual_hinge_top_chamfer",
        "family": "hinge",
        "orig": "hinge_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top circular edges by 0.5 mm.",
        "op_code": "result = result.edges('%CIRCLE and >Z').chamfer(0.5)",
    },
    {
        "record_id": "manual_hinge_outer_fillet",
        "family": "hinge",
        "orig": "hinge_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "medium",
        "instruction": "Fillet the outer vertical edges by 2 mm.",
        "op_code": "result = result.edges('|Z').fillet(2.0)",
    },
    # i_beam — no easy_r0, use hard_r0
    {
        "record_id": "manual_i_beam_cross_hole",
        "family": "i_beam",
        "orig": "i_beam_hard_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "medium",
        "instruction": "Drill a 10 mm cross-hole through the web.",
        "op_code": "result = result.cut(cq.Workplane('YZ').cylinder(200.0, 5.0))",
    },
    {
        "record_id": "manual_i_beam_top_chamfer",
        "family": "i_beam",
        "orig": "i_beam_hard_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer the top face edges by 1 mm.",
        "op_code": "result = result.faces('>Z').chamfer(1.0)",
    },
    # impeller (complex)
    {
        "record_id": "manual_impeller_bore_widen",
        "family": "impeller",
        "orig": "impeller_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Widen the central hub bore to 14 mm diameter.",
        "op_code": "result = result.cut(cq.Workplane('XY').cylinder(200.0, 7.0))",
    },
    # j_hook (curved hook)
    {
        "record_id": "manual_j_hook_shank_chamfer",
        "family": "j_hook",
        "orig": "j_hook_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer all circular edges by 0.8 mm.",
        "op_code": "result = result.edges('%CIRCLE').chamfer(0.8)",
    },
    # keyhole_plate
    {
        "record_id": "manual_keyhole_plate_corner_fillet",
        "family": "keyhole_plate",
        "orig": "keyhole_plate_easy_r0_orig.py",
        "edit_type": "add_fillet",
        "difficulty": "easy",
        "instruction": "Fillet the four outer corner vertical edges by 4 mm.",
        "op_code": "result = result.edges('|Z').fillet(4.0)",
    },
    # lathe_turned_part
    {
        "record_id": "manual_lathe_turned_part_end_chamfer",
        "family": "lathe_turned_part",
        "orig": "lathe_turned_part_easy_r0_orig.py",
        "edit_type": "add_chamfer",
        "difficulty": "easy",
        "instruction": "Chamfer all circular edges by 1 mm.",
        "op_code": "result = result.edges('%CIRCLE').chamfer(1.0)",
    },
    # lobed_knob
    {
        "record_id": "manual_lobed_knob_bore_add",
        "family": "lobed_knob",
        "orig": "lobed_knob_easy_r0_orig.py",
        "edit_type": "add_hole",
        "difficulty": "easy",
        "instruction": "Drill an 8 mm axial through-hole.",
        "op_code": "result = result.cut(cq.Workplane('XY').cylinder(100.0, 4.0))",
    },
    # === Batch 4: remaining 45 families ===
    {"record_id":"manual_locator_block_corner_fillet","family":"locator_block","orig":"locator_block_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 5 mm.","op_code":"result = result.edges('|Z').fillet(5.0)"},
    {"record_id":"manual_manifold_block_corner_fillet","family":"manifold_block","orig":"manifold_block_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 5 mm.","op_code":"result = result.edges('|Z').fillet(5.0)"},
    {"record_id":"manual_manifold_block_end_chamfer","family":"manifold_block","orig":"manifold_block_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"medium","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_mesh_panel_corner_fillet","family":"mesh_panel","orig":"mesh_panel_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 3 mm.","op_code":"result = result.edges('|Z').fillet(3.0)"},
    {"record_id":"manual_motor_end_cap_top_chamfer","family":"motor_end_cap","orig":"motor_end_cap_add_hole_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer the top circular edges by 2 mm.","op_code":"result = result.edges('%CIRCLE and >Z').chamfer(2.0)"},
    {"record_id":"manual_motor_end_cap_bore_widen","family":"motor_end_cap","orig":"motor_end_cap_add_hole_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Widen the shaft bore to 40 mm diameter.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(100.0, 20.0))"},
    {"record_id":"manual_mounting_angle_corner_fillet","family":"mounting_angle","orig":"mounting_angle_add_hole_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the outer vertical edges by 2 mm.","op_code":"result = result.edges('|Z').fillet(2.0)"},
    {"record_id":"manual_mounting_plate_corner_fillet","family":"mounting_plate","orig":"mounting_plate_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 8 mm.","op_code":"result = result.edges('|Z').fillet(8.0)"},
    {"record_id":"manual_nozzle_end_chamfer","family":"nozzle","orig":"nozzle_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_pcb_standoff_plate_corner_fillet","family":"pcb_standoff_plate","orig":"pcb_standoff_plate_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 5 mm.","op_code":"result = result.edges('|Z').fillet(5.0)"},
    {"record_id":"manual_pillow_block_corner_fillet","family":"pillow_block","orig":"pillow_block_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 4 mm.","op_code":"result = result.edges('|Z').fillet(4.0)"},
    {"record_id":"manual_pipe_elbow_end_chamfer","family":"pipe_elbow","orig":"pipe_elbow_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_pipe_flange_corner_fillet","family":"pipe_flange","orig":"pipe_flange_add_chamfer_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 10 mm.","op_code":"result = result.edges('|Z').fillet(10.0)"},
    {"record_id":"manual_pipe_flange_bore_widen","family":"pipe_flange","orig":"pipe_flange_add_chamfer_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Widen the bore to 70 mm diameter.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(100.0, 35.0))"},
    {"record_id":"manual_piston_side_hole","family":"piston","orig":"piston_easy_r0_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Drill a 10 mm wrist-pin cross hole.","op_code":"result = result.cut(cq.Workplane('XZ').cylinder(200.0, 5.0))"},
    {"record_id":"manual_propeller_bore_widen","family":"propeller","orig":"propeller_easy_r0_orig.py","edit_type":"add_hole","difficulty":"easy","instruction":"Widen the hub bore to 14 mm.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(200.0, 7.0))"},
    {"record_id":"manual_pull_handle_cross_hole","family":"pull_handle","orig":"pull_handle_easy_r0_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Drill a 4 mm cross-hole through the grip bar.","op_code":"result = result.cut(cq.Workplane('XY').transformed(offset=cq.Vector(0,0,16)).cylinder(200.0, 2.0))"},
    {"record_id":"manual_pulley_bore_widen","family":"pulley","orig":"pulley_gid10233_medium_r0_orig.py","edit_type":"add_hole","difficulty":"easy","instruction":"Widen the bore along the Y axis by drilling a 40 mm hole.","op_code":"result = result.cut(cq.Workplane('XZ').cylinder(100.0, 20.0))"},
    {"record_id":"manual_rect_frame_outer_fillet","family":"rect_frame","orig":"rect_frame_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 5 mm.","op_code":"result = result.edges('|Z').fillet(5.0)"},
    {"record_id":"manual_rect_frame_corner_hole","family":"rect_frame","orig":"rect_frame_easy_r0_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Add a 6 mm mounting hole at the (20, 40) position.","op_code":"result = result.faces('>Z').workplane().pushPoints([(20,40)]).hole(6.0)"},
    {"record_id":"manual_rib_plate_corner_fillet","family":"rib_plate","orig":"rib_plate_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 5 mm.","op_code":"result = result.edges('|Z').fillet(5.0)"},
    {"record_id":"manual_rivet_end_chamfer","family":"rivet","orig":"rivet_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 0.3 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(0.3)"},
    {"record_id":"manual_round_flange_corner_fillet","family":"round_flange","orig":"round_flange_hard_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet all vertical edges by 2 mm.","op_code":"result = result.edges('|Z').fillet(2.0)"},
    {"record_id":"manual_shaft_collar_top_chamfer","family":"shaft_collar","orig":"shaft_collar_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer the top circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE and >Z').chamfer(1.0)"},
    {"record_id":"manual_shaft_collar_side_hole","family":"shaft_collar","orig":"shaft_collar_easy_r0_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Drill a 5 mm radial setscrew hole through the wall.","op_code":"result = result.cut(cq.Workplane('YZ').cylinder(50.0, 2.5))"},
    {"record_id":"manual_slotted_plate_corner_fillet","family":"slotted_plate","orig":"slotted_plate_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 6 mm.","op_code":"result = result.edges('|Z').fillet(6.0)"},
    {"record_id":"manual_snap_clip_end_chamfer","family":"snap_clip","orig":"snap_clip_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all vertical edges by 0.5 mm.","op_code":"result = result.edges('|Z').chamfer(0.5)"},
    {"record_id":"manual_spacer_ring_chamfer","family":"spacer_ring","orig":"spacer_ring_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 0.5 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(0.5)"},
    {"record_id":"manual_spline_hub_bore_widen","family":"spline_hub","orig":"spline_hub_easy_r0_orig.py","edit_type":"add_hole","difficulty":"easy","instruction":"Add a 20 mm axial through-hole.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(100.0, 10.0))"},
    {"record_id":"manual_sprocket_bore_widen","family":"sprocket","orig":"sprocket_easy_r0_orig.py","edit_type":"add_hole","difficulty":"easy","instruction":"Widen the bore to 16 mm diameter.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(100.0, 8.0))"},
    {"record_id":"manual_spur_gear_bore_widen","family":"spur_gear","orig":"spur_gear_hard_r0_orig.py","edit_type":"add_hole","difficulty":"easy","instruction":"Widen the bore to 10 mm diameter.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(100.0, 5.0))"},
    {"record_id":"manual_standoff_side_hole","family":"standoff","orig":"standoff_easy_r0_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Drill a 4 mm radial hole through the standoff wall.","op_code":"result = result.cut(cq.Workplane('YZ').cylinder(50.0, 2.0))"},
    {"record_id":"manual_t_pipe_fitting_chamfer","family":"t_pipe_fitting","orig":"t_pipe_fitting_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_t_slot_rail_end_chamfer","family":"t_slot_rail","orig":"t_slot_rail_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all vertical edges by 1 mm.","op_code":"result = result.edges('|Z').chamfer(1.0)"},
    {"record_id":"manual_taper_pin_cross_hole","family":"taper_pin","orig":"taper_pin_easy_r0_orig.py","edit_type":"add_hole","difficulty":"medium","instruction":"Drill a 1.5 mm cross-hole through the pin.","op_code":"result = result.cut(cq.Workplane('YZ').transformed(offset=cq.Vector(0,0,10)).cylinder(20.0, 0.75))"},
    {"record_id":"manual_tapered_boss_bore_widen","family":"tapered_boss","orig":"tapered_boss_easy_r0_orig.py","edit_type":"add_hole","difficulty":"easy","instruction":"Widen the bore to 12 mm.","op_code":"result = result.cut(cq.Workplane('XY').cylinder(100.0, 6.0))"},
    {"record_id":"manual_tee_nut_top_chamfer","family":"tee_nut","orig":"tee_nut_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_threaded_adapter_chamfer","family":"threaded_adapter","orig":"threaded_adapter_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_torsion_spring_end_chamfer","family":"torsion_spring","orig":"torsion_spring_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 0.5 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(0.5)"},
    {"record_id":"manual_torus_link_chamfer","family":"torus_link","orig":"torus_link_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_turnbuckle_chamfer","family":"turnbuckle","orig":"turnbuckle_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_twisted_bracket_outer_fillet","family":"twisted_bracket","orig":"twisted_bracket_hard_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the outer vertical edges by 2 mm.","op_code":"result = result.edges('|Z').fillet(2.0)"},
    {"record_id":"manual_u_bolt_end_chamfer","family":"u_bolt","orig":"u_bolt_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_u_channel_outer_fillet","family":"u_channel","orig":"u_channel_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the outer vertical edges by 3 mm.","op_code":"result = result.edges('|Z').fillet(3.0)"},
    {"record_id":"manual_vented_panel_corner_fillet","family":"vented_panel","orig":"vented_panel_hard_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 5 mm.","op_code":"result = result.edges('|Z').fillet(5.0)"},
    {"record_id":"manual_venturi_tube_chamfer","family":"venturi_tube","orig":"venturi_tube_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    {"record_id":"manual_waffle_plate_corner_fillet","family":"waffle_plate","orig":"waffle_plate_easy_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 6 mm.","op_code":"result = result.edges('|Z').fillet(6.0)"},
    {"record_id":"manual_washer_chamfer","family":"washer","orig":"washer_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 0.3 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(0.3)"},
    {"record_id":"manual_wing_nut_top_chamfer","family":"wing_nut","orig":"wing_nut_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer the top circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE and >Z').chamfer(1.0)"},
    {"record_id":"manual_worm_screw_end_chamfer","family":"worm_screw","orig":"worm_screw_easy_r0_orig.py","edit_type":"add_chamfer","difficulty":"easy","instruction":"Chamfer all circular edges by 1 mm.","op_code":"result = result.edges('%CIRCLE').chamfer(1.0)"},
    # === remaining rerun candidates ===
    {"record_id":"manual_connector_faceplate_corner_fillet","family":"connector_faceplate","orig":"connector_faceplate_hard_r0_orig.py","edit_type":"add_fillet","difficulty":"easy","instruction":"Fillet the four outer vertical corners by 3 mm.","op_code":"result = result.edges('|Z').fillet(3.0)"},
]


def process(spec: dict) -> dict:
    orig_path = BENCH / "codes" / spec["orig"]
    if not orig_path.exists():
        return {**spec, "status": "fail_orig_missing",
                "err": f"missing: {spec['orig']}"}
    orig_text = orig_path.read_text()
    orig_step_src = BENCH / "steps" / (orig_path.stem + ".step")
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(parents=True, exist_ok=True)
    steps_dir.mkdir(parents=True, exist_ok=True)

    rid = spec["record_id"]
    orig_out_code = codes_dir / f"{rid}_orig.py"
    gt_out_code = codes_dir / f"{rid}_gt.py"
    orig_out_step = steps_dir / f"{rid}_orig.step"
    gt_out_step = steps_dir / f"{rid}_gt.step"

    # Resume: if gt_out_step exists and is non-trivial, skip exec + recompute IoU
    if gt_out_step.exists() and gt_out_step.stat().st_size > 100:
        from bench.metrics import compute_iou
        iou, _ = compute_iou(str(orig_out_step), str(gt_out_step))
        status = "ok"
        if iou is None or iou >= 0.99:
            status = "iou_too_high"
        elif iou < 0.3:
            status = "fail_iou_too_low"
        return {
            **spec, "status": status, "iou": iou,
            "orig_code_path": f"codes/{rid}_orig.py",
            "gt_code_path": f"codes/{rid}_gt.py",
            "orig_step_path": f"steps/{rid}_orig.step",
            "gt_step_path": f"steps/{rid}_gt.step",
        }

    orig_out_code.write_text(orig_text)
    if orig_step_src.exists():
        orig_out_step.write_bytes(orig_step_src.read_bytes())

    gt_text = splice_gt_code(orig_text, spec["op_code"])
    gt_out_code.write_text(gt_text)

    ok, err = exec_cq(gt_text, gt_out_step, timeout=30)
    if not ok:
        return {**spec, "status": "fail_gt_exec", "err": err}

    from bench.metrics import compute_iou
    iou, _ = compute_iou(str(orig_out_step), str(gt_out_step))

    status = "ok"
    if iou >= 0.99:
        status = "iou_too_high"

    return {
        **spec,
        "status": status,
        "iou": iou,
        "orig_code_path": f"codes/{rid}_orig.py",
        "gt_code_path": f"codes/{rid}_gt.py",
        "orig_step_path": f"steps/{rid}_orig.step",
        "gt_step_path": f"steps/{rid}_gt.step",
    }


def render(rec: dict) -> bool:
    if rec.get("status") != "ok":
        return False
    from PIL import Image, ImageDraw, ImageFont
    from scripts.data_generation.render_normalized_views import (
        render_step_normalized,
    )
    rid = rec["record_id"]
    prev_dir = OUT / "previews"
    prev_dir.mkdir(exist_ok=True)
    png = prev_dir / f"{rid}.png"
    orig = OUT / rec["orig_step_path"]
    gt = OUT / rec["gt_step_path"]
    with tempfile.TemporaryDirectory() as td:
        o = render_step_normalized(str(orig), td, size=360, prefix="o_")
        g = render_step_normalized(str(gt), td, size=360, prefix="g_")
        oi = Image.open(o["composite"]).copy()
        gi = Image.open(g["composite"]).copy()
    w = oi.width + gi.width + 20
    h = max(oi.height, gi.height) + 80
    canvas = Image.new("RGB", (w, h), "white")
    canvas.paste(oi, (0, 70))
    canvas.paste(gi, (oi.width + 20, 70))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font = ImageFont.load_default(); small = ImageFont.load_default()
    d.text((10, 8), rid, fill="black", font=font)
    d.text((10, 34),
           f"{rec['edit_type']}  IoU={rec['iou']:.3f}  fam={rec['family']}",
           fill="gray", font=small)
    d.text((10, 50), rec["instruction"][:150], fill="gray", font=small)
    d.text((oi.width // 2 - 20, h - 22), "ORIG", fill="black", font=font)
    d.text((oi.width + 20 + gi.width // 2 - 10, h - 22), "GT",
           fill="black", font=font)
    canvas.save(str(png))
    print(f"preview → {png.name}")
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for spec in MANUAL_SPECS:
        print(f"\n>>> {spec['record_id']}", flush=True)
        try:
            rec = process(spec)
        except Exception as e:
            rec = {**spec, "status": "fail_exception", "err": str(e)[:200]}
        iou = rec.get("iou")
        iou_s = f"{iou:.3f}" if isinstance(iou, float) else "?"
        print(f"    status={rec['status']}  IoU={iou_s}", flush=True)
        if rec["status"] != "ok":
            print(f"    err: {rec.get('err', '')[:200]}", flush=True)
        else:
            try:
                render(rec)
            except Exception as e:
                print(f"    render fail: {e}", flush=True)
        records.append(rec)

    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records)
    )
    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["num", "record_id", "family", "edit_type", "difficulty",
                    "iou", "status", "instruction"])
        for idx, r in enumerate(records, 1):
            w.writerow([
                idx, r["record_id"], r["family"], r["edit_type"],
                r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float)
                else "",
                r["status"], r["instruction"],
            ])
    print(f"\nwrote {csv_path}")


if __name__ == "__main__":
    main()
