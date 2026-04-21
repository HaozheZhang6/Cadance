"""Edit axes for 106 CAD families — used by pair_builder to generate edit bench.

Each axis declares:
    param:  dict key in sample_params() output
    human:  natural-language name for instruction text
    unit:   measurement unit (mm / deg / N/A)
    pct:    signed percentage delta (negative = shrink, positive = enlarge)
            chosen small (2-5%) and in a pre-selected SAFE direction:
              - bore/inner/hole    → negative  (shrink is safe vs outer wall)
              - outer/length/width/height/thickness → positive (enlarge is safe)
    constraints (optional): list of ordering rules the perturbed value
            must satisfy, e.g. [("lt","outer_diameter")] means
            param < outer_diameter (post-perturbation).

Notes on picks:
  - Skip counts (n_teeth, n_bolts, cell_count, etc.) — discrete/topological.
  - Skip angles on critical helix/thread paths (helix_angle, pitch_angle,
    conv_angle_deg) — geometry very sensitive.
  - For abbreviated DIN/ISO params (d, l, h, s, e), use descriptive `human`.
  - When a family exposes derived & raw (ball_diameter + ball_radius),
    pick only the primary one to keep edits unambiguous.

Families with < 3 obviously-safe axes (capsule, torus_link) carry fewer
entries; pair_builder compensates by sampling more roots.
"""

EDIT_AXES: dict[str, list[dict]] = {
    # --- A ---
    "ball_knob": [
        {"param": "ball_diameter", "human": "ball diameter", "unit": "mm", "pct": +3},
        {"param": "stem_height", "human": "stem height", "unit": "mm", "pct": +4},
        {"param": "stem_radius", "human": "stem radius", "unit": "mm", "pct": +3},
    ],
    "battery_holder": [
        {"param": "block_L", "human": "block length", "unit": "mm", "pct": +3},
        {"param": "block_T", "human": "block thickness", "unit": "mm", "pct": +4},
        {"param": "wall_t", "human": "wall thickness", "unit": "mm", "pct": +3},
    ],
    "bearing_retainer_cap": [
        {
            "param": "flange_diameter",
            "human": "flange diameter",
            "unit": "mm",
            "pct": +3,
        },
        {
            "param": "flange_thickness",
            "human": "flange thickness",
            "unit": "mm",
            "pct": +4,
        },
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "flange_diameter")],
        },
    ],
    "bellows": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {
            "param": "convolution_height",
            "human": "convolution height",
            "unit": "mm",
            "pct": +3,
        },
        {
            "param": "inner_radius",
            "human": "inner radius",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_radius")],
        },
    ],
    "bevel_gear": [
        {"param": "face_width", "human": "face width", "unit": "mm", "pct": +3},
        {"param": "cone_height", "human": "cone height", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "pitch_radius")],
        },
    ],
    "bolt": [
        {"param": "shaft_length", "human": "shaft length", "unit": "mm", "pct": +3},
        {"param": "head_height", "human": "head height", "unit": "mm", "pct": +3},
        {"param": "head_diameter", "human": "head diameter", "unit": "mm", "pct": +3},
    ],
    "bucket": [
        {"param": "r_top", "human": "top radius", "unit": "mm", "pct": +3},
        {"param": "height", "human": "height", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    # --- C ---
    "cable_routing_panel": [
        {"param": "length", "human": "panel length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "panel width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "panel thickness", "unit": "mm", "pct": +4},
    ],
    "cam": [
        {"param": "base_radius", "human": "base radius", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "cam thickness", "unit": "mm", "pct": +4},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "hub_radius")],
        },
    ],
    "capsule": [
        {"param": "radius", "human": "radius", "unit": "mm", "pct": +3},
        {"param": "cyl_height", "human": "cylindrical height", "unit": "mm", "pct": +3},
    ],
    "chair": [
        {"param": "seat_length", "human": "seat length", "unit": "mm", "pct": +3},
        {"param": "seat_width", "human": "seat width", "unit": "mm", "pct": +3},
        {"param": "seat_thickness", "human": "seat thickness", "unit": "mm", "pct": +4},
    ],
    "circlip": [
        {"param": "ring_od", "human": "ring outer diameter", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "axial thickness", "unit": "mm", "pct": +4},
        {"param": "ring_width", "human": "ring width", "unit": "mm", "pct": +3},
    ],
    "clevis": [
        {"param": "arm_thickness", "human": "arm thickness", "unit": "mm", "pct": +4},
        {"param": "arm_height", "human": "arm height", "unit": "mm", "pct": +3},
        {"param": "depth", "human": "body depth", "unit": "mm", "pct": +3},
    ],
    "clevis_pin": [
        {"param": "diameter", "human": "pin diameter", "unit": "mm", "pct": +3},
        {"param": "length", "human": "pin length", "unit": "mm", "pct": +3},
        {"param": "chamfer_length", "human": "chamfer length", "unit": "mm", "pct": +4},
    ],
    "coil_spring": [
        {"param": "wire_diameter", "human": "wire diameter", "unit": "mm", "pct": +3},
        {"param": "coil_radius", "human": "coil radius", "unit": "mm", "pct": +3},
        {"param": "total_height", "human": "total height", "unit": "mm", "pct": +3},
    ],
    "connecting_rod": [
        {"param": "big_end_radius", "human": "big end radius", "unit": "mm", "pct": +3},
        {
            "param": "center_distance",
            "human": "center distance",
            "unit": "mm",
            "pct": +3,
        },
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
    ],
    "connector_faceplate": [
        {"param": "length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "plate width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "plate thickness", "unit": "mm", "pct": +4},
    ],
    "cotter_pin": [
        {"param": "d", "human": "pin diameter", "unit": "mm", "pct": +3},
        {"param": "long_leg", "human": "long-leg length", "unit": "mm", "pct": +3},
        {"param": "short_leg", "human": "short-leg length", "unit": "mm", "pct": +3},
    ],
    "cruciform": [
        {"param": "arm_length", "human": "arm length", "unit": "mm", "pct": +3},
        {"param": "arm_width", "human": "arm width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
    ],
    # --- D ---
    "dog_bone": [
        {"param": "boss_radius", "human": "boss radius", "unit": "mm", "pct": +3},
        {
            "param": "cc_distance",
            "human": "center-to-center distance",
            "unit": "mm",
            "pct": +3,
        },
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
    ],
    "dome_cap": [
        {"param": "radius", "human": "radius", "unit": "mm", "pct": +3},
        {"param": "cyl_height", "human": "cylindrical height", "unit": "mm", "pct": +3},
        {"param": "wall", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    "double_simplex_sprocket": [
        {"param": "tooth_width", "human": "tooth width", "unit": "mm", "pct": +3},
        {"param": "spacer_width", "human": "spacer width", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "root_diameter")],
        },
    ],
    "dovetail_slide": [
        {"param": "width_top", "human": "top width", "unit": "mm", "pct": +3},
        {"param": "length", "human": "slide length", "unit": "mm", "pct": +3},
        {"param": "height", "human": "slide height", "unit": "mm", "pct": +4},
    ],
    "dowel_pin": [
        {"param": "diameter", "human": "pin diameter", "unit": "mm", "pct": +3},
        {"param": "length", "human": "pin length", "unit": "mm", "pct": +3},
        {"param": "chamfer_length", "human": "chamfer length", "unit": "mm", "pct": +3},
    ],
    "duct_elbow": [
        {"param": "duct_width", "human": "duct width", "unit": "mm", "pct": +3},
        {"param": "lead_length", "human": "lead length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    # --- E ---
    "enclosure": [
        {"param": "length", "human": "enclosure length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "enclosure width", "unit": "mm", "pct": +3},
        {"param": "height", "human": "enclosure height", "unit": "mm", "pct": +3},
    ],
    "eyebolt": [
        {"param": "l", "human": "shank length", "unit": "mm", "pct": +3},
        {"param": "d2", "human": "eye outer diameter", "unit": "mm", "pct": +3},
        {
            "param": "d3",
            "human": "eye inner-hole diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "d2")],
        },
    ],
    # --- F ---
    "fan_shroud": [
        {"param": "fan_radius", "human": "fan radius", "unit": "mm", "pct": +3},
        {"param": "plate_side", "human": "plate side length", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "plate thickness", "unit": "mm", "pct": +4},
    ],
    "flat_link": [
        {"param": "boss_radius", "human": "boss radius", "unit": "mm", "pct": +3},
        {
            "param": "cc_distance",
            "human": "center-to-center distance",
            "unit": "mm",
            "pct": +3,
        },
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
    ],
    # --- G ---
    "grease_nipple": [
        {"param": "s", "human": "hex across-flats", "unit": "mm", "pct": +3},
        {"param": "h", "human": "total height", "unit": "mm", "pct": +3},
        {"param": "l", "human": "thread length", "unit": "mm", "pct": +3},
    ],
    "gridfinity_bin": [
        {"param": "cell_size", "human": "cell size", "unit": "mm", "pct": +3},
        {"param": "stack_h", "human": "stack height", "unit": "mm", "pct": +3},
        {"param": "wall_t", "human": "wall thickness", "unit": "mm", "pct": +3},
    ],
    "grommet": [
        {"param": "flange_d3", "human": "flange diameter", "unit": "mm", "pct": +3},
        {"param": "total_height_H", "human": "total height", "unit": "mm", "pct": +3},
        {
            "param": "bore_d1",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "flange_d3")],
        },
    ],
    "gusseted_bracket": [
        {"param": "flange_width", "human": "flange width", "unit": "mm", "pct": +3},
        {"param": "depth", "human": "bracket depth", "unit": "mm", "pct": +3},
        {
            "param": "flange_thickness",
            "human": "flange thickness",
            "unit": "mm",
            "pct": +4,
        },
    ],
    # --- H ---
    "handwheel": [
        {"param": "outer_diameter", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "rim_width", "human": "rim width", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "hub_diameter")],
        },
    ],
    "heat_sink": [
        {"param": "base_length", "human": "base length", "unit": "mm", "pct": +3},
        {"param": "base_thickness", "human": "base thickness", "unit": "mm", "pct": +4},
        {"param": "fin_height", "human": "fin height", "unit": "mm", "pct": +3},
    ],
    "helical_gear": [
        {"param": "face_width", "human": "face width", "unit": "mm", "pct": +3},
        {"param": "bore_diameter", "human": "bore diameter", "unit": "mm", "pct": -3},
        {"param": "helix_angle", "human": "helix angle", "unit": "deg", "pct": +2},
    ],
    "hex_key_organizer": [
        {"param": "block_L", "human": "block length", "unit": "mm", "pct": +3},
        {"param": "block_T", "human": "block thickness", "unit": "mm", "pct": +3},
        {"param": "pitch", "human": "pocket pitch", "unit": "mm", "pct": +3},
    ],
    "hex_nut": [
        {
            "param": "across_flats",
            "human": "across-flats size",
            "unit": "mm",
            "pct": +3,
        },
        {"param": "height", "human": "nut height", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "across_flats")],
        },
    ],
    "hex_standoff": [
        {
            "param": "across_flats",
            "human": "across-flats size",
            "unit": "mm",
            "pct": +3,
        },
        {"param": "height", "human": "standoff height", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "across_flats")],
        },
    ],
    "hinge": [
        {"param": "leaf_size", "human": "leaf size", "unit": "mm", "pct": +3},
        {"param": "leaf_thickness", "human": "leaf thickness", "unit": "mm", "pct": +4},
        {
            "param": "knuckle_diameter",
            "human": "knuckle diameter",
            "unit": "mm",
            "pct": +3,
        },
    ],
    "hollow_tube": [
        {"param": "outer_width", "human": "outer width", "unit": "mm", "pct": +3},
        {"param": "length", "human": "tube length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    # --- I ---
    "i_beam": [
        {"param": "total_height", "human": "total height", "unit": "mm", "pct": +3},
        {"param": "length", "human": "beam length", "unit": "mm", "pct": +3},
        {
            "param": "flange_thickness",
            "human": "flange thickness",
            "unit": "mm",
            "pct": +4,
        },
    ],
    "impeller": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {"param": "hub_radius", "human": "hub radius", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "hub_radius")],
        },
    ],
    # --- J ---
    "j_hook": [
        {"param": "rod_d", "human": "rod diameter", "unit": "mm", "pct": +3},
        {"param": "leg_length", "human": "leg length", "unit": "mm", "pct": +3},
        {"param": "total_length", "human": "total length", "unit": "mm", "pct": +3},
    ],
    # --- K ---
    "keyhole_plate": [
        {"param": "plate_width", "human": "plate width", "unit": "mm", "pct": +3},
        {"param": "plate_height", "human": "plate height", "unit": "mm", "pct": +3},
        {
            "param": "plate_thickness",
            "human": "plate thickness",
            "unit": "mm",
            "pct": +4,
        },
    ],
    "knob": [
        {"param": "knob_diameter", "human": "knob diameter", "unit": "mm", "pct": +3},
        {"param": "total_height", "human": "total height", "unit": "mm", "pct": +3},
        {"param": "base_radius", "human": "base radius", "unit": "mm", "pct": +3},
    ],
    # --- L ---
    "l_bracket": [
        {"param": "leg_size", "human": "leg size", "unit": "mm", "pct": +3},
        {"param": "depth", "human": "bracket depth", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
    ],
    "lathe_turned_part": [
        {"param": "d1", "human": "large step diameter", "unit": "mm", "pct": +3},
        {"param": "h1", "human": "large step height", "unit": "mm", "pct": +3},
        {"param": "h2", "human": "small step height", "unit": "mm", "pct": +3},
    ],
    "lobed_knob": [
        {"param": "d1", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "h1", "human": "body height", "unit": "mm", "pct": +3},
        {"param": "bush_h", "human": "bushing height", "unit": "mm", "pct": +3},
    ],
    "locator_block": [
        {"param": "length", "human": "block length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "block width", "unit": "mm", "pct": +3},
        {"param": "height", "human": "block height", "unit": "mm", "pct": +3},
    ],
    # --- M ---
    "manifold_block": [
        {"param": "length", "human": "block length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "block width", "unit": "mm", "pct": +3},
        {"param": "height", "human": "block height", "unit": "mm", "pct": +3},
    ],
    "mesh_panel": [
        {"param": "panel_length", "human": "panel length", "unit": "mm", "pct": +3},
        {"param": "panel_width", "human": "panel width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "panel thickness", "unit": "mm", "pct": +4},
    ],
    "motor_end_cap": [
        {"param": "outer_diameter", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "cap thickness", "unit": "mm", "pct": +4},
        {
            "param": "shaft_diameter",
            "human": "shaft-hole diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_diameter")],
        },
    ],
    "mounting_angle": [
        {"param": "leg_size", "human": "leg size", "unit": "mm", "pct": +3},
        {"param": "depth", "human": "depth", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
    ],
    "mounting_plate": [
        {"param": "length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "plate width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "plate thickness", "unit": "mm", "pct": +4},
    ],
    # --- N ---
    "nozzle": [
        {"param": "inlet_radius", "human": "inlet radius", "unit": "mm", "pct": +3},
        {"param": "length", "human": "nozzle length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    # --- P ---
    "pan_head_screw": [
        {"param": "head_d_dk", "human": "head diameter", "unit": "mm", "pct": +3},
        {"param": "head_h_k", "human": "head height", "unit": "mm", "pct": +3},
        {"param": "screw_length_l", "human": "screw length", "unit": "mm", "pct": +3},
    ],
    "parallel_key": [
        {"param": "key_length", "human": "key length", "unit": "mm", "pct": +3},
        {"param": "key_width", "human": "key width", "unit": "mm", "pct": +3},
        {"param": "key_height", "human": "key height", "unit": "mm", "pct": +3},
    ],
    "pcb_standoff_plate": [
        {"param": "length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "plate width", "unit": "mm", "pct": +3},
        {"param": "post_height", "human": "post height", "unit": "mm", "pct": +3},
    ],
    "phone_stand": [
        {"param": "base_depth", "human": "base depth", "unit": "mm", "pct": +3},
        {"param": "back_height", "human": "back height", "unit": "mm", "pct": +3},
        {
            "param": "shell_thickness",
            "human": "shell thickness",
            "unit": "mm",
            "pct": +4,
        },
    ],
    "pillow_block": [
        {
            "param": "shaft_bore_diameter",
            "human": "shaft bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "base_width_A")],
        },
        {"param": "base_length_L", "human": "base length", "unit": "mm", "pct": +3},
        {"param": "block_height_Ht", "human": "block height", "unit": "mm", "pct": +3},
    ],
    "pipe_elbow": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {"param": "lead_length", "human": "lead length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    "pipe_flange": [
        {"param": "length", "human": "flange length", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "flange thickness", "unit": "mm", "pct": +4},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "length")],
        },
    ],
    "piston": [
        {"param": "radius", "human": "piston radius", "unit": "mm", "pct": +3},
        {"param": "height", "human": "piston height", "unit": "mm", "pct": +3},
        {"param": "crown_height", "human": "crown height", "unit": "mm", "pct": +3},
    ],
    "propeller": [
        {"param": "hub_radius", "human": "hub radius", "unit": "mm", "pct": +3},
        {"param": "blade_length", "human": "blade length", "unit": "mm", "pct": +3},
        {"param": "hub_height", "human": "hub height", "unit": "mm", "pct": +3},
    ],
    "pull_handle": [
        {"param": "hole_pitch_L", "human": "hole pitch", "unit": "mm", "pct": +3},
        {"param": "grasp_height_H", "human": "grasp height", "unit": "mm", "pct": +3},
        {"param": "bar_diameter_d", "human": "bar diameter", "unit": "mm", "pct": +3},
    ],
    "pulley": [
        {"param": "rim_radius", "human": "rim radius", "unit": "mm", "pct": +3},
        {"param": "width", "human": "pulley width", "unit": "mm", "pct": +3},
        {
            "param": "bore_radius",
            "human": "bore radius",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "hub_radius")],
        },
    ],
    # --- R ---
    "ratchet_sector": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "sector thickness", "unit": "mm", "pct": +4},
        {"param": "angle_deg", "human": "sector angle", "unit": "deg", "pct": +2},
    ],
    "rect_frame": [
        {"param": "outer_length", "human": "outer length", "unit": "mm", "pct": +3},
        {"param": "outer_width", "human": "outer width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "frame thickness", "unit": "mm", "pct": +4},
    ],
    "rib_plate": [
        {"param": "length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "base_thickness", "human": "base thickness", "unit": "mm", "pct": +4},
        {"param": "rib_height", "human": "rib height", "unit": "mm", "pct": +3},
    ],
    "rivet": [
        {"param": "d", "human": "shank diameter", "unit": "mm", "pct": +3},
        {"param": "k", "human": "head height", "unit": "mm", "pct": +3},
        {"param": "shank_length", "human": "shank length", "unit": "mm", "pct": +3},
    ],
    "round_flange": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {"param": "height", "human": "flange height", "unit": "mm", "pct": +4},
        {
            "param": "inner_radius",
            "human": "inner radius",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_radius")],
        },
    ],
    # --- S ---
    "shaft_collar": [
        {"param": "outer_diameter", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "width", "human": "collar width", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_diameter")],
        },
    ],
    "sheet_metal_tray": [
        {"param": "length", "human": "tray length", "unit": "mm", "pct": +3},
        {"param": "height", "human": "tray height", "unit": "mm", "pct": +3},
        {
            "param": "sheet_thickness",
            "human": "sheet thickness",
            "unit": "mm",
            "pct": +4,
        },
    ],
    "slotted_plate": [
        {"param": "length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "plate width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "plate thickness", "unit": "mm", "pct": +4},
    ],
    "snap_clip": [
        {"param": "ring_od", "human": "ring outer diameter", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "axial thickness", "unit": "mm", "pct": +4},
        {"param": "ring_width", "human": "ring width", "unit": "mm", "pct": +3},
    ],
    "spacer_ring": [
        {"param": "outer_diameter", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "ring thickness", "unit": "mm", "pct": +4},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_diameter")],
        },
    ],
    "spline_hub": [
        {
            "param": "hub_outer_dia",
            "human": "hub outer diameter",
            "unit": "mm",
            "pct": +3,
        },
        {"param": "hub_length", "human": "hub length", "unit": "mm", "pct": +3},
        {"param": "spline_length", "human": "spline length", "unit": "mm", "pct": +3},
    ],
    "sprocket": [
        {"param": "disc_thickness", "human": "disc thickness", "unit": "mm", "pct": +4},
        {"param": "tip_diameter", "human": "tip diameter", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "root_diameter")],
        },
    ],
    "spur_gear": [
        {"param": "face_width", "human": "face width", "unit": "mm", "pct": +3},
        {"param": "hub_radius", "human": "hub radius", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "hub_radius")],
        },
    ],
    "standoff": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {"param": "height", "human": "standoff height", "unit": "mm", "pct": +3},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_radius")],
        },
    ],
    "star_blank": [
        {"param": "outer_radius", "human": "outer radius", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "star thickness", "unit": "mm", "pct": +4},
        {
            "param": "inner_radius",
            "human": "inner radius",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_radius")],
        },
    ],
    "stepped_shaft": [
        {"param": "r1", "human": "large step radius", "unit": "mm", "pct": +3},
        {"param": "h1", "human": "large step height", "unit": "mm", "pct": +3},
        {"param": "h2", "human": "small step height", "unit": "mm", "pct": +3},
    ],
    # --- T ---
    "t_pipe_fitting": [
        {"param": "outer_diameter", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "run_length", "human": "run length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    "t_slot_rail": [
        {"param": "size", "human": "profile size", "unit": "mm", "pct": +3},
        {"param": "length", "human": "rail length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    "table": [
        {"param": "top_length", "human": "top length", "unit": "mm", "pct": +3},
        {"param": "top_width", "human": "top width", "unit": "mm", "pct": +3},
        {"param": "leg_height", "human": "leg height", "unit": "mm", "pct": +3},
    ],
    "taper_pin": [
        {"param": "d_nominal", "human": "nominal diameter", "unit": "mm", "pct": +3},
        {"param": "length", "human": "pin length", "unit": "mm", "pct": +3},
        {"param": "d_large", "human": "large-end diameter", "unit": "mm", "pct": +3},
    ],
    "tapered_boss": [
        {"param": "base_diameter", "human": "base diameter", "unit": "mm", "pct": +3},
        {"param": "height", "human": "boss height", "unit": "mm", "pct": +3},
        {
            "param": "top_diameter",
            "human": "top diameter",
            "unit": "mm",
            "pct": +3,
            "constraints": [("lt", "base_diameter")],
        },
    ],
    "tee_nut": [
        {"param": "flange_D", "human": "flange diameter", "unit": "mm", "pct": +3},
        {"param": "barrel_H", "human": "barrel height", "unit": "mm", "pct": +3},
        {
            "param": "thread_d",
            "human": "thread diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "barrel_od")],
        },
    ],
    "threaded_adapter": [
        {"param": "hex_af", "human": "hex across-flats", "unit": "mm", "pct": +3},
        {"param": "stub_height", "human": "stub height", "unit": "mm", "pct": +3},
        {
            "param": "bore_radius",
            "human": "bore radius",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "stub_radius")],
        },
    ],
    "torsion_spring": [
        {"param": "wire_diameter", "human": "wire diameter", "unit": "mm", "pct": +3},
        {"param": "coil_radius", "human": "coil radius", "unit": "mm", "pct": +3},
        {"param": "leg_length", "human": "leg length", "unit": "mm", "pct": +3},
    ],
    "torus_link": [
        {"param": "major_radius", "human": "major radius", "unit": "mm", "pct": +3},
        {"param": "minor_radius", "human": "minor radius", "unit": "mm", "pct": +3},
    ],
    "turnbuckle": [
        {"param": "L1", "human": "body length", "unit": "mm", "pct": +3},
        {"param": "boss_d", "human": "boss diameter", "unit": "mm", "pct": +3},
        {"param": "boss_L", "human": "boss length", "unit": "mm", "pct": +3},
    ],
    "twisted_bracket": [
        {"param": "plate_length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "plate thickness", "unit": "mm", "pct": +4},
        {
            "param": "twist_length",
            "human": "twist-zone length",
            "unit": "mm",
            "pct": +3,
        },
    ],
    "twisted_drill": [
        {"param": "rod_length", "human": "rod length", "unit": "mm", "pct": +3},
        {"param": "rod_radius", "human": "rod radius", "unit": "mm", "pct": +3},
        {"param": "pitch", "human": "flute pitch", "unit": "mm", "pct": +3},
    ],
    # --- U ---
    "u_bolt": [
        {"param": "leg_length", "human": "leg length", "unit": "mm", "pct": +3},
        {"param": "rod_diameter", "human": "rod diameter", "unit": "mm", "pct": +3},
        {
            "param": "center_distance",
            "human": "center distance",
            "unit": "mm",
            "pct": +3,
        },
    ],
    "u_channel": [
        {"param": "outer_width", "human": "outer width", "unit": "mm", "pct": +3},
        {"param": "length", "human": "channel length", "unit": "mm", "pct": +3},
        {"param": "wall_thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    # --- V ---
    "vented_panel": [
        {"param": "length", "human": "panel length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "panel width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "panel thickness", "unit": "mm", "pct": +4},
    ],
    "venturi_tube": [
        {"param": "pipe_diameter", "human": "pipe diameter", "unit": "mm", "pct": +3},
        {"param": "inlet_len", "human": "inlet length", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "wall thickness", "unit": "mm", "pct": +4},
    ],
    # --- W ---
    "waffle_plate": [
        {"param": "length", "human": "plate length", "unit": "mm", "pct": +3},
        {"param": "width", "human": "plate width", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "plate thickness", "unit": "mm", "pct": +4},
    ],
    "wall_anchor": [
        {"param": "length_L", "human": "anchor length", "unit": "mm", "pct": +3},
        {"param": "flange_d", "human": "flange diameter", "unit": "mm", "pct": +3},
        {
            "param": "pilot_bore_d",
            "human": "pilot bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "flange_d")],
        },
    ],
    "washer": [
        {"param": "outer_diameter", "human": "outer diameter", "unit": "mm", "pct": +3},
        {"param": "thickness", "human": "thickness", "unit": "mm", "pct": +4},
        {
            "param": "bore_diameter",
            "human": "bore diameter",
            "unit": "mm",
            "pct": -3,
            "constraints": [("lt", "outer_diameter")],
        },
    ],
    "wing_nut": [
        {"param": "e", "human": "wing span", "unit": "mm", "pct": +3},
        {"param": "h", "human": "total height", "unit": "mm", "pct": +3},
        {"param": "d3", "human": "collar diameter", "unit": "mm", "pct": +3},
    ],
    "wire_grid": [
        {"param": "cell_width", "human": "cell width", "unit": "mm", "pct": +3},
        {"param": "cell_height", "human": "cell height", "unit": "mm", "pct": +3},
        {"param": "wire_diameter", "human": "wire diameter", "unit": "mm", "pct": +3},
    ],
    "worm_screw": [
        {"param": "thread_length", "human": "thread length", "unit": "mm", "pct": +3},
        {"param": "shaft_length", "human": "shaft length", "unit": "mm", "pct": +3},
        {"param": "d1", "human": "pitch diameter", "unit": "mm", "pct": +3},
    ],
    # --- Z ---
    "z_bracket": [
        {"param": "base_length", "human": "base length", "unit": "mm", "pct": +3},
        {"param": "base_thickness", "human": "base thickness", "unit": "mm", "pct": +4},
        {"param": "arm_height", "human": "arm height", "unit": "mm", "pct": +3},
    ],
}


def check_axis_constraints(params: dict, axis: dict) -> bool:
    """Return True if perturbed params satisfy axis ordering constraints."""
    for typ, other in axis.get("constraints", []):
        if other not in params:
            continue
        if typ == "lt" and not (params[axis["param"]] < params[other]):
            return False
        if typ == "gt" and not (params[axis["param"]] > params[other]):
            return False
    return True
