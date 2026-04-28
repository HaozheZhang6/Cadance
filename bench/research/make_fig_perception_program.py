"""Plot perception (QA) vs execution (IoU24) — paper figure draft."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def load(p: Path):
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()][
        -30:
    ]


def main(out: Path) -> None:
    cg_off = {
        r["stem"]: r
        for r in load(ROOT / "results/img2cq/gpt-5.3-chat-latest/results.jsonl")
    }
    cg_on = {
        r["stem"]: r
        for r in load(ROOT / "results/img2cq/gpt-5.3-thinking/results.jsonl")
    }
    qa_off = {
        r["stem"]: r
        for r in load(ROOT / "results/qa_img/gpt-5.3-chat-latest/results.jsonl")
    }
    qa_on = {
        r["stem"]: r
        for r in load(ROOT / "results/qa_img/gpt-5.3-thinking/results.jsonl")
    }

    stems = sorted(cg_off.keys() & cg_on.keys() & qa_off.keys() & qa_on.keys())

    rows = []
    for s in stems:
        rows.append(
            {
                "stem": s,
                "qa_off": qa_off[s].get("qa_score", 0.0),
                "qa_on": qa_on[s].get("qa_score", 0.0),
                "iou_off": cg_off[s].get("iou_rot") or cg_off[s].get("iou", 0.0),
                "iou_on": cg_on[s].get("iou_rot") or cg_on[s].get("iou", 0.0),
            }
        )

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 9.5,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.linewidth": 0.7,
            "axes.grid": True,
            "grid.linewidth": 0.35,
            "grid.alpha": 0.4,
        }
    )

    fig, (ax, ax2) = plt.subplots(
        1,
        2,
        figsize=(11.5, 4.6),
        gridspec_kw={"width_ratios": [1.55, 1.0]},
        constrained_layout=True,
    )

    # ===================== panel (a): scatter =====================
    # quadrant shading
    ax.add_patch(
        plt.Rectangle((0.5, 0.0), 0.5, 0.2, color="#ffe7e7", zorder=0, alpha=0.7)
    )
    ax.add_patch(
        plt.Rectangle((0.0, 0.5), 0.3, 0.5, color="#e7eeff", zorder=0, alpha=0.7)
    )

    ax.text(
        0.985,
        0.20,
        "QA strong / program weak",
        ha="right",
        va="bottom",
        fontsize=8,
        color="#a02525",
        style="italic",
    )
    ax.text(
        0.015,
        0.50,
        "program strong / QA weak",
        ha="left",
        va="top",
        fontsize=8,
        color="#1f3da0",
        style="italic",
    )

    # diagonal reference (where qa = iou24)
    ax.plot([0, 1], [0, 1], color="#bbb", lw=0.5, ls="--", zorder=1)

    # baseline guide lines (no labels in plot — explained in panel b)
    ax.axhline(0.20, color="#cc8800", lw=0.45, ls=":", zorder=1, alpha=0.8)
    ax.axvline(0.54, color="#7a3d99", lw=0.45, ls=":", zorder=1, alpha=0.8)

    # faint connectors for all stems
    for r in rows:
        ax.plot(
            [r["qa_off"], r["qa_on"]],
            [r["iou_off"], r["iou_on"]],
            color="#bbb",
            lw=0.4,
            zorder=2,
            alpha=0.6,
        )

    qa_offs = np.array([r["qa_off"] for r in rows])
    qa_ons = np.array([r["qa_on"] for r in rows])
    iou_offs = np.array([r["iou_off"] for r in rows])
    iou_ons = np.array([r["iou_on"] for r in rows])

    ax.scatter(
        qa_offs,
        iou_offs,
        marker="o",
        s=34,
        facecolors="white",
        edgecolors="#234080",
        linewidths=0.9,
        label="reasoning OFF",
        zorder=4,
    )
    ax.scatter(
        qa_ons,
        iou_ons,
        marker="^",
        s=38,
        color="#a83232",
        edgecolors="white",
        linewidths=0.5,
        label="reasoning ON",
        zorder=5,
    )

    # Manual annotations: pick most informative cases, position labels by hand
    annots = [
        ("synth_mesh_panel_007522_s4420", "mesh_panel", (0.79, 0.14), (0.92, 0.30)),
        (
            "synth_torsion_spring_003047_s4252",
            "torsion_spring",
            (0.77, 0.04),
            (0.90, 0.05),
        ),
        ("synth_eyebolt_002831_s4252", "eyebolt", (0.79, 0.09), (0.95, 0.20)),
        (
            "synth_capsule_005340_s4252",
            "capsule (rescued by ON)",
            (0.24, 0.45),
            (0.04, 0.62),
        ),
        ("synth_worm_screw_005727_s4252", "worm\\_screw", (0.11, 0.57), (0.04, 0.84)),
        (
            "synth_capsule_003550_s4252",
            "capsule (.torus on ON)",
            (0.86, 0.31),
            (0.78, 0.55),
        ),
    ]
    for _stem, label, anchor, txt_pos in annots:
        ax.annotate(
            label,
            xy=anchor,
            xytext=txt_pos,
            fontsize=7.8,
            ha="left",
            color="#222",
            arrowprops={
                "arrowstyle": "-",
                "color": "#444",
                "lw": 0.5,
                "alpha": 0.7,
                "connectionstyle": "arc3,rad=0.15",
            },
        )

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("qa\\_img score (perception)")
    ax.set_ylabel("img2cq IoU$_{24}$ (execution)")
    ax.set_title("(a)  Per-stem perception vs.\\ execution", fontsize=10, loc="left")
    ax.legend(
        loc="lower left",
        frameon=True,
        framealpha=0.95,
        edgecolor="#bbb",
        borderpad=0.4,
        handlelength=1.5,
    )

    # ===================== panel (b): contribution decomposition =====================
    qa_full_off, qa_full_on = qa_offs.mean(), qa_ons.mean()
    qa_blank_off, qa_blank_on = 0.558, 0.522
    iou24_off, iou24_on = iou_offs.mean(), iou_ons.mean()
    base_off, base_on = 0.201, 0.197

    cats = ["qa\\_img", "img2cq IoU$_{24}$"]
    x = np.arange(len(cats))
    width = 0.34

    # OFF bars
    off_priors = np.array([qa_blank_off, base_off])
    off_signal = np.array([qa_full_off - qa_blank_off, iou24_off - base_off])
    off_total = off_priors + off_signal

    on_priors = np.array([qa_blank_on, base_on])
    on_signal = np.array([qa_full_on - qa_blank_on, iou24_on - base_on])
    on_total = on_priors + on_signal

    # bars: prior at bottom, signal stacked on top
    ax2.bar(
        x - width / 2,
        off_priors,
        width,
        color="#bcc6e0",
        edgecolor="#234080",
        lw=0.6,
        label="control (prior / baseline)",
    )
    ax2.bar(
        x - width / 2,
        off_signal,
        width,
        bottom=off_priors,
        color="#234080",
        edgecolor="#234080",
        lw=0.6,
        label="signal (full $-$ control)",
    )
    ax2.bar(
        x + width / 2, on_priors, width, color="#e8c2c2", edgecolor="#a83232", lw=0.6
    )
    ax2.bar(
        x + width / 2,
        on_signal,
        width,
        bottom=on_priors,
        color="#a83232",
        edgecolor="#a83232",
        lw=0.6,
    )

    # OFF / ON labels under each pair
    for i in range(len(cats)):
        ax2.text(
            i - width / 2,
            -0.04,
            "OFF",
            ha="center",
            va="top",
            fontsize=7.5,
            color="#234080",
        )
        ax2.text(
            i + width / 2,
            -0.04,
            "ON",
            ha="center",
            va="top",
            fontsize=7.5,
            color="#a83232",
        )
        # signal value above each bar
        ax2.text(
            i - width / 2,
            off_total[i] + 0.013,
            f"+{off_signal[i]:.3f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="#234080",
        )
        ax2.text(
            i + width / 2,
            on_total[i] + 0.013,
            f"+{on_signal[i]:.3f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="#a83232",
        )

    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, fontsize=9)
    ax2.tick_params(axis="x", which="both", pad=14)
    ax2.set_ylim(0, 1.0)
    ax2.set_ylabel("score")
    ax2.set_title(
        "(b)  Decomposition: prior vs.\\ task-conditional signal",
        fontsize=10,
        loc="left",
    )

    # custom legend
    from matplotlib.patches import Patch

    legend_handles = [
        Patch(facecolor="#bcc6e0", edgecolor="#234080", label="qa: blank-image"),
        Patch(facecolor="#234080", label="qa: visual contribution"),
        Patch(
            facecolor="#e8c2c2",
            edgecolor="#a83232",
            label="img2cq: cross-stem baseline",
        ),
        Patch(facecolor="#a83232", label="img2cq: program contribution"),
    ]
    ax2.legend(
        handles=legend_handles,
        loc="upper right",
        fontsize=7.2,
        frameon=True,
        framealpha=0.95,
        edgecolor="#bbb",
        handlelength=1.2,
        handleheight=0.9,
        borderpad=0.4,
    )

    fig.suptitle(
        "Perception--execution gap on BenchCAD ($N{=}30$, gpt-5.3, seed 42)",
        fontsize=11,
        y=1.02,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    print(f"saved -> {out}")
    print(f"saved -> {out.with_suffix('.pdf')}")


if __name__ == "__main__":
    main(ROOT / "bench/research/outputs/run_2026_04_27/fig_perception_program.png")
