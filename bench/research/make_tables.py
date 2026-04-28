"""Render result tables (PDF/PNG) — paper draft."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "bench/research/outputs/run_2026_04_27"

mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "STIXGeneral"],
        "mathtext.fontset": "stix",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
    }
)


def render_table(
    *,
    rows: list,  # list of dicts: {"kind": "header"/"section"/"data"/"rule"/"sep", ...}
    column_widths: list[float],  # relative widths (sum doesn't matter)
    col_aligns: list[str],  # 'l' / 'c' / 'r'
    caption: str,
    label: str,
    out: Path,
    row_height: float = 0.32,  # inches
    fig_width: float = 6.5,  # inches
):
    n_cols = len(column_widths)
    total_w = sum(column_widths)
    norm_widths = [w / total_w for w in column_widths]
    # x positions = left edge of each cell
    x_left = [0.0]
    for w in norm_widths[:-1]:
        x_left.append(x_left[-1] + w)
    x_centers = [x_left[i] + norm_widths[i] / 2 for i in range(n_cols)]
    x_right = [x_left[i] + norm_widths[i] for i in range(n_cols)]

    n_rows = len(rows)
    table_h = n_rows * row_height
    cap_h = 0.6
    fig_h = table_h + cap_h + 0.25

    fig = plt.figure(figsize=(fig_width, fig_h))
    ax = fig.add_axes([0.02, 0.02, 0.96, table_h / fig_h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n_rows)
    ax.axis("off")

    # caption above
    cap_ax = fig.add_axes([0.02, (table_h + 0.05) / fig_h, 0.96, cap_h / fig_h])
    cap_ax.axis("off")
    cap_ax.text(
        0.0,
        0.95,
        f"Table {label}. ",
        transform=cap_ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        fontweight="bold",
    )
    cap_ax.text(
        0.105,
        0.95,
        caption,
        transform=cap_ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        wrap=True,
    )

    pad = 0.02

    for i, r in enumerate(rows):
        y = n_rows - 1 - i + 0.5  # row centerline (top → bottom)
        kind = r.get("kind", "data")
        if kind == "rule":
            kind_w = r.get("weight", "mid")
            lw = {"top": 1.1, "bot": 1.1, "mid": 0.5}.get(kind_w, 0.5)
            ax.plot(
                [0, 1], [n_rows - i, n_rows - i], color="black", lw=lw, clip_on=False
            )
            continue
        if kind == "section":
            ax.text(
                0.0,
                y,
                r["text"],
                ha="left",
                va="center",
                fontsize=8.5,
                style="italic",
            )
            continue
        if kind == "spancell":
            # single cell spanning all columns
            ax.text(
                0.0,
                y,
                r["text"],
                ha="left",
                va="center",
                fontsize=8.5,
                fontweight=r.get("weight", "normal"),
                style=r.get("style", "normal"),
            )
            continue
        # header / data
        cells = r["cells"]
        for j, txt in enumerate(cells):
            align = col_aligns[j]
            if align == "l":
                xx, ha = x_left[j] + pad, "left"
            elif align == "r":
                xx, ha = x_right[j] - pad, "right"
            else:
                xx, ha = x_centers[j], "center"
            ax.text(
                xx,
                y,
                txt,
                ha=ha,
                va="center",
                fontsize=8.5,
                fontweight=r.get("weight", "normal"),
                style=r.get("style", "normal"),
            )

    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    print(f"saved -> {out}  +  {out.with_suffix('.pdf')}")


# ─────────────────────── Table 1 ───────────────────────
def table_main():
    rows = [
        {"kind": "rule", "weight": "top"},
        {"kind": "data", "weight": "bold", "cells": ["", "OFF", "ON", "$\\Delta$"]},
        {"kind": "rule"},
        {"kind": "section", "text": "qa\\_img  (image $\\rightarrow$ numeric answers)"},
        {"kind": "data", "cells": ["  full image", "0.578", "0.576", "$-0.002$"]},
        {
            "kind": "data",
            "cells": ["  blank image (control)", "0.558", "0.522", "$-0.036$"],
        },
        {
            "kind": "data",
            "weight": "bold",
            "cells": ["  visual contribution", "+0.020", "+0.054", "+0.034"],
        },
        {"kind": "rule"},
        {
            "kind": "section",
            "text": "img2cq  (image $\\rightarrow$ CadQuery $\\rightarrow$ IoU)",
        },
        {"kind": "data", "cells": ["  exec rate", "0.767", "0.800", "+0.033"]},
        {"kind": "data", "cells": ["  IoU", "0.202", "0.226", "+0.024"]},
        {"kind": "data", "cells": ["  IoU$_{24}$", "0.266", "0.310", "+0.044"]},
        {"kind": "data", "cells": ["  Feat-F1", "0.332", "0.373", "+0.041"]},
        {
            "kind": "data",
            "cells": ["  cross-stem IoU (control)", "0.148", "0.130", "—"],
        },
        {
            "kind": "data",
            "cells": ["  cross-stem IoU$_6$ (control)", "0.201", "0.197", "—"],
        },
        {
            "kind": "data",
            "weight": "bold",
            "cells": [
                "  program contribution (IoU$_{24}$ $-$ IoU$_6^{\\mathrm{ctrl}}$)",
                "+0.065",
                "+0.113",
                "+0.048",
            ],
        },
        {"kind": "rule", "weight": "bot"},
    ]
    render_table(
        rows=rows,
        column_widths=[3.4, 0.85, 0.85, 0.95],
        col_aligns=["l", "c", "c", "c"],
        caption=(
            "Perception–execution gap on BenchCAD (N=30, gpt-5.3, seed 42). "
            "QA scores include a blank-image control (image replaced with a black PNG); "
            "img2cq scores include a cross-stem control (target gt vs. same-model gen for "
            "a different stem). Reasoning = reasoning_effort=medium."
        ),
        label="1",
        out=OUT / "tab_main.png",
        fig_width=6.6,
    )


# ─────────────────────── Table 2 ───────────────────────
def table_failures():
    rows = [
        {"kind": "rule", "weight": "top"},
        {"kind": "data", "weight": "bold", "cells": ["Failure type", "OFF", "ON"]},
        {"kind": "rule"},
        {
            "kind": "data",
            "cells": ["Invented method (.cone, .torus, .helix)", "1", "2"],
        },
        {
            "kind": "data",
            "cells": ["Selector / fillet / chamfer edge mis-pick", "4", "2"],
        },
        {"kind": "data", "cells": ["Math-domain / no-wire / value error", "2", "2"]},
        {"kind": "rule"},
        {
            "kind": "data",
            "weight": "bold",
            "cells": ["Total exec failures (out of 30)", "7", "6"],
        },
        {"kind": "rule", "weight": "bot"},
    ]
    render_table(
        rows=rows,
        column_widths=[4.0, 0.7, 0.7],
        col_aligns=["l", "c", "c"],
        caption=(
            "Code-generation failure modes by reasoning regime. Reasoning halves selector "
            "errors but introduces a new failure: confident hallucination of "
            "plausible-but-non-existent CadQuery methods (.torus, .helix)."
        ),
        label="2",
        out=OUT / "tab_failures.png",
        fig_width=6.0,
    )


# ─────────────────────── Table 3 ───────────────────────
def table_mismatch():
    rows = [
        {"kind": "rule", "weight": "top"},
        {"kind": "section", "text": "Per-stem direction of mismatch"},
        {"kind": "rule"},
        {
            "kind": "data",
            "cells": [
                "QA $\\geq 0.5$  and  IoU$_{24} < 0.2$",
                "6",
                "e.g. mesh_panel, torsion_spring, eyebolt",
            ],
        },
        {
            "kind": "data",
            "cells": ["IoU$_{24} \\geq 0.5$  and  QA $< 0.3$", "1", "worm_screw"],
        },
        {"kind": "rule"},
        {"kind": "section", "text": "IoU$_{24}$ by difficulty"},
        {"kind": "rule"},
        {
            "kind": "data",
            "weight": "bold",
            "cells": ["Difficulty", "$N$", "OFF $\\rightarrow$ ON"],
        },
        {"kind": "data", "cells": ["easy", "10", "0.32 $\\rightarrow$ 0.39  (+0.07)"]},
        {
            "kind": "data",
            "cells": ["medium", " 8", "0.14 $\\rightarrow$ 0.12  ($-$0.02)"],
        },
        {
            "kind": "data",
            "cells": ["hard", "12", "0.32 $\\rightarrow$ 0.30  ($-$0.02)"],
        },
        {"kind": "rule", "weight": "bot"},
    ]
    render_table(
        rows=rows,
        column_widths=[2.6, 0.5, 3.4],
        col_aligns=["l", "c", "l"],
        caption=(
            "Per-stem mismatch and difficulty stratification. Top: 6 stems where QA is strong "
            "but program fails versus 1 stem in the opposite direction; the asymmetry "
            "suggests the program is the more reliable readout. Bottom: reasoning gains "
            "concentrate on easy geometries, not hard ones."
        ),
        label="3",
        out=OUT / "tab_mismatch.png",
        fig_width=6.5,
    )


def table_models():
    rows = [
        {"kind": "rule", "weight": "top"},
        {
            "kind": "data",
            "weight": "bold",
            "cells": [
                "Model",
                "QA$_{\\mathrm{full}}$",
                "QA$_{\\mathrm{blank}}$",
                "vis. $\\Delta$",
                "exec\\%",
                "IoU",
                "Feat-F1",
            ],
        },
        {"kind": "rule"},
        {
            "kind": "data",
            "cells": ["gpt-4o", "0.567", "0.521", "+0.046", "0.667", "0.137", "0.333"],
        },
        {
            "kind": "data",
            "cells": [
                "gpt-5.3 (no reasoning)",
                "0.578",
                "0.558",
                "+0.020",
                "0.767",
                "0.202",
                "0.332",
            ],
        },
        {
            "kind": "data",
            "cells": [
                "gpt-5.3 (reasoning=med)",
                "0.576",
                "0.522",
                "+0.054",
                "0.800",
                "0.226",
                "0.373",
            ],
        },
        {
            "kind": "data",
            "cells": [
                "gemini-2.5-flash",
                "0.502",
                "0.014",
                "+0.488",
                "0.167",
                "0.055",
                "0.097",
            ],
        },
        {"kind": "rule", "weight": "bot"},
    ]
    render_table(
        rows=rows,
        column_widths=[2.6, 0.85, 0.85, 0.85, 0.7, 0.7, 0.7],
        col_aligns=["l", "c", "c", "c", "c", "c", "c"],
        caption=(
            "Cross-model comparison on BenchCAD (N=30, seed 42). "
            "QA visual contribution (full $-$ blank-image) reveals which models actually "
            "use the rendered image versus relying on family-name prior: gemini-2.5-flash "
            "draws +0.488 from vision; gpt-5.3 only +0.020 to +0.054. "
            "img2cq IoU is over all 30 stems (failed-exec counted as 0); reasoning is "
            "reasoning_effort=medium. Pilot scale; scale-up to N$\\geq$500 with $\\geq$3 "
            "seeds and additional model families is left to follow-up work."
        ),
        label="4",
        out=OUT / "tab_models.png",
        fig_width=8.0,
    )


if __name__ == "__main__":
    table_main()
    table_failures()
    table_mismatch()
    table_models()
