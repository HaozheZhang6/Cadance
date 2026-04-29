"""Split the 106-family gallery into 3 pages, 3 columns, larger fonts.

Page 1: essentials A — axisymmetric / ring / U-J / helical / twisted / ball
Page 2: essentials B — loft / taper / shell / arrays / polar / sweep / cuts + uncertain (yellow)
Page 3: N/A — every family with no essential spec
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "bench/research/outputs/run_2026_04_27"
sys.path.insert(0, str(Path(__file__).parent))

from canonical_ops import (  # noqa: E402
    ESSENTIAL_BY_FAMILY, essential_pass, find_ops, fmt_spec,
)

# ── manual category ordering (within green) ───────────────────────────────
PAGE_1_CATS = {
    "axisymmetric (revolve | sweep)": [
        "bellows", "bucket", "cotter_pin", "dome_cap", "grease_nipple",
        "grommet", "lathe_turned_part", "nozzle", "piston", "pulley",
        "rivet", "taper_pin", "venturi_tube",
    ],
    "ring / torus":   ["torus_link", "eyebolt"],
    "U/J bend":       ["u_bolt", "j_hook"],
    "helical (sweep+helix)": ["torsion_spring", "worm_screw", "coil_spring"],
    "twisted axis":   ["twisted_drill", "twisted_bracket"],
    "ball / sphere":  ["ball_knob", "capsule"],
    "hex polygon":    ["bolt", "hex_nut", "hex_standoff", "threaded_adapter"],
}

PAGE_2_CATS = {
    "loft / taper": ["bevel_gear", "helical_gear", "propeller", "tapered_boss",
                     "wing_nut", "knob"],
    "shell":          ["enclosure", "sheet_metal_tray"],
    "polar array":    ["motor_end_cap"],
    "linear array":   ["cable_routing_panel", "heat_sink", "mesh_panel", "rib_plate",
                       "slotted_plate", "vented_panel", "waffle_plate"],
    "sweep (non-helical)": ["duct_elbow", "pipe_elbow"],
    "irregular profile (gears / cams / stars / cross / etc.)": [
        "spur_gear", "sprocket", "double_simplex_sprocket", "cam", "impeller",
        "star_blank", "cruciform", "ratchet_sector", "circlip", "dog_bone",
        "snap_clip", "handwheel", "spline_hub", "dovetail_slide",
    ],
}

PAGE_3_CATS = {
    "defined-by-cuts (cut | hole — material removal is structural)": [
        "battery_holder", "clevis", "gridfinity_bin", "hex_key_organizer",
        "keyhole_plate", "lobed_knob", "u_channel",
        "bearing_retainer_cap", "connecting_rod", "hinge", "locator_block",
        "pillow_block", "turnbuckle", "pan_head_screw",
        "fan_shroud", "flat_link", "gusseted_bracket", "hollow_tube",
        "l_bracket", "manifold_block", "mounting_angle", "mounting_plate",
        "pcb_standoff_plate", "pipe_flange", "rect_frame", "shaft_collar",
        "spacer_ring", "standoff", "t_slot_rail", "washer", "wire_grid",
        "z_bracket", "connector_faceplate",
    ],
}


def _decode_render(cp) -> Image.Image:
    if isinstance(cp, dict) and "bytes" in cp:
        return Image.open(io.BytesIO(cp["bytes"]))
    if isinstance(cp, bytes):
        return Image.open(io.BytesIO(cp))
    return cp


def _render_page(title: str, family_groups: dict, df, fam_n, out: Path,
                 default_class: str | None = None) -> None:
    """family_groups = {category_label: [fam, ...]}"""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "STIXGeneral"],
        "mathtext.fontset": "stix",
    })

    cols = 3

    # collect all families flatly in section order
    flat = []
    for cat, fams in family_groups.items():
        for fam in fams:
            if fam not in fam_n:
                continue
            spec = ESSENTIAL_BY_FAMILY.get(fam)
            if spec:
                sub = df[df.family == fam]
                gt_pass = sum(1 for c in sub["gt_code"] if essential_pass(fam, find_ops(c or "")))
                cov = gt_pass / len(sub)
                cls = "green" if cov >= 0.9 else "yellow" if cov >= 0.5 else "orange"
            else:
                cov = None
                cls = "gray"
            flat.append((cat, fam, cov, cls, spec, fam_n[fam]))

    # collect renders
    rec = {}
    for _, r in df.iterrows():
        if r["family"] in rec:
            continue
        rec[r["family"]] = _decode_render(r["composite_png"])

    # rows = ceil(len/cols)
    n = len(flat)
    grid_rows = (n + cols - 1) // cols

    panel_h = 2.0     # bigger panel
    title_h = 0.9
    fig_w = 14.5
    fig_h = grid_rows * panel_h + title_h + 0.4
    fig = plt.figure(figsize=(fig_w, fig_h))

    # title
    title_ax = fig.add_axes([0.02, 1 - title_h / fig_h, 0.96, title_h / fig_h])
    title_ax.axis("off")
    title_ax.text(0.0, 0.7, title, fontsize=16, fontweight="bold",
                  va="top", ha="left", transform=title_ax.transAxes)
    title_ax.text(
        0.0, 0.30,
        "GREEN ✓ cov ≥ 0.9 (strict essential)   ·   "
        "YELLOW ? 0.5–0.9 (variants)   ·   "
        "GRAY — N/A (no essential, any valid construction works)",
        fontsize=10, color="#444",
        va="top", ha="left", transform=title_ax.transAxes,
    )

    BG   = {"green":"#e9f5e0","yellow":"#fff3c4","orange":"#fde0c8","gray":"#e8e8e8"}
    EDGE = {"green":"#3a7a2c","yellow":"#b5891b","orange":"#a85b1a","gray":"#999"}
    SYM  = {"green":"✓","yellow":"?","orange":"!","gray":"—"}

    body_top = 1 - title_h / fig_h
    body_bot = 0.005
    body_h = body_top - body_bot
    cell_h = body_h / grid_rows
    cell_w = 1.0 / cols

    last_cat = None
    for i, (cat, fam, cov, cls, spec, n_stems) in enumerate(flat):
        r, c = divmod(i, cols)
        x0 = 0.005 + c * cell_w
        y0 = body_top - (r + 1) * cell_h

        # cell BG
        bg_ax = fig.add_axes([x0 + 0.004, y0 + 0.005, cell_w - 0.012, cell_h - 0.01])
        bg_ax.set_xticks([]); bg_ax.set_yticks([])
        bg_ax.set_facecolor(BG[cls])
        for s in bg_ax.spines.values():
            s.set_edgecolor(EDGE[cls])
            s.set_linewidth(0.8)

        # render
        thumb_h_frac = cell_h * 0.85
        thumb_h_in = thumb_h_frac * fig_h
        thumb_w_frac = thumb_h_in / fig_w
        ax_img = fig.add_axes([x0 + 0.013, y0 + cell_h * 0.075, thumb_w_frac, thumb_h_frac])
        ax_img.axis("off")
        ax_img.imshow(rec[fam])

        # text
        text_x = x0 + thumb_w_frac + 0.020
        text_w = cell_w - thumb_w_frac - 0.026
        ax_txt = fig.add_axes([text_x, y0, text_w, cell_h])
        ax_txt.axis("off")

        # category label (small, only on first cell of each cat)
        if cat != last_cat:
            ax_txt.text(0.0, 0.97, f"[{cat}]",
                        fontsize=8.5, color="#777", style="italic",
                        va="top", ha="left", transform=ax_txt.transAxes)
            last_cat = cat

        ax_txt.text(0.0, 0.78, f"{SYM[cls]}  {fam.replace('_',' ')}",
                    fontsize=11.5, fontweight="bold", color=EDGE[cls],
                    va="top", ha="left", transform=ax_txt.transAxes)
        if spec is None:
            ax_txt.text(0.0, 0.46, "N/A — no essential",
                        fontsize=10, color="#666",
                        va="top", ha="left", transform=ax_txt.transAxes)
        else:
            ax_txt.text(0.0, 0.50, "essential:",
                        fontsize=10, fontweight="bold", color="#222",
                        va="top", ha="left", transform=ax_txt.transAxes)
            ax_txt.text(0.0, 0.31, fmt_spec(spec),
                        fontsize=10.5, color="#222",
                        va="top", ha="left", transform=ax_txt.transAxes)
        ax_txt.text(0.0, 0.10,
                    f"N={n_stems}" + (f"  cov={cov:.2f}" if cov is not None else ""),
                    fontsize=9, color="#555",
                    va="top", ha="left", transform=ax_txt.transAxes)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}  ({grid_rows} rows × {cols} cols, {n} families)")


def _na_groups(df, fam_n) -> dict:
    """All N/A families split alphabetically into named buckets so each is small."""
    na_fams = sorted([f for f in fam_n if f not in ESSENTIAL_BY_FAMILY])
    return {"no essential — soft feature_f1 only": na_fams}


def main():
    from datasets import load_dataset
    print("loading cad_bench_722 ...")
    df = load_dataset("BenchCAD/cad_bench_722")["train"].to_pandas()
    fam_n = df["family"].value_counts().to_dict()

    _render_page(
        "Page 1 / 4 — Rotational primitives  (revolve / sphere / polygon / helical / twisted)",
        PAGE_1_CATS, df, fam_n, OUT / "tab_ess_p1.png",
    )
    _render_page(
        "Page 2 / 4 — Structural construction  (loft / taper / shell / arrays / sweep / irregular profile)",
        PAGE_2_CATS, df, fam_n, OUT / "tab_ess_p2.png",
    )
    _render_page(
        "Page 3 / 4 — Material removal & uncertain  (cut | hole essentials + variants)",
        PAGE_3_CATS, df, fam_n, OUT / "tab_ess_p3.png",
    )
    _render_page(
        "Page 4 / 4 — N/A families  (no essential — any valid construction works)",
        _na_groups(df, fam_n), df, fam_n, OUT / "tab_ess_p4_na.png",
    )


if __name__ == "__main__":
    main()
