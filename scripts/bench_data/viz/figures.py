"""Sample-figure generators for BenchCAD — paper-quality styling."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd
import seaborn as sns
import squarify
from PIL import Image, ImageDraw, ImageFont

from .data import synth_parts

# ────────────────────── Style ──────────────────────
# Try Helvetica, fall back to Arial / DejaVu Sans.
def _pick_font() -> str:
    for f in ("Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"):
        try:
            FontProperties(family=f)
            return f
        except Exception:
            continue
    return "DejaVu Sans"


_FONT = _pick_font()
sns.set_theme(style="whitegrid", context="paper",
              rc={
                  "font.family": _FONT,
                  "font.size": 10,
                  "axes.titlesize": 12,
                  "axes.titleweight": "semibold",
                  "axes.labelsize": 10,
                  "axes.labelweight": "regular",
                  "axes.edgecolor": "#444",
                  "axes.linewidth": 0.8,
                  "axes.spines.top": False,
                  "axes.spines.right": False,
                  "xtick.color": "#444",
                  "ytick.color": "#444",
                  "xtick.labelsize": 9,
                  "ytick.labelsize": 9,
                  "grid.color": "#E5E5E5",
                  "grid.linewidth": 0.5,
                  "figure.dpi": 120,
                  "savefig.dpi": 180,
                  "savefig.bbox": "tight",
                  "savefig.facecolor": "white",
                  "legend.fontsize": 9,
                  "legend.frameon": False,
              })

# Curated palette — muted but distinct, paper-friendly.
PALETTE = {
    "rotational":      "#4C72B0",  # blue
    "block_assembly":  "#DD8452",  # warm orange
    "plate_panel":     "#55A868",  # green
    "section_channel": "#C44E52",  # red
    "fastener":        "#8172B2",  # purple
    "pipe_tube":       "#937860",  # tan
    "other":           "#999999",
}
DIFF_COLORS = {"easy": "#55A868", "medium": "#DD8452", "hard": "#C44E52"}
ACCENT = "#4C72B0"
ACCENT2 = "#C44E52"

# A nice bold title font (matplotlib uses default; we'll use suptitle weight)


# ────────────────────── helpers ──────────────────────
def _macro_order(df: pd.DataFrame) -> list[str]:
    return df.groupby("macro").size().sort_values(ascending=False).index.tolist()


def _annotate_total(ax, n: int):
    ax.text(0.99, 0.97, f"N = {n:,}", transform=ax.transAxes,
            ha="right", va="top", color="#666",
            fontsize=9, fontfamily=_FONT)


# ────────────────────── 1. Family distribution ──────────────────────
def fig_family_distribution(out: Path) -> None:
    df = synth_parts()
    fam_counts = df.groupby(["family", "macro"]).size().reset_index(name="n")
    fam_counts = fam_counts.sort_values("n", ascending=False).head(40)
    colors = [PALETTE[m] for m in fam_counts["macro"]]

    fig, ax = plt.subplots(figsize=(11, 4.6))
    bars = ax.bar(range(len(fam_counts)), fam_counts["n"], color=colors,
                  edgecolor="white", linewidth=0.4)
    ax.set_xticks(range(len(fam_counts)))
    ax.set_xticklabels(fam_counts["family"], rotation=55, ha="right",
                       fontsize=8.5)
    ax.set_ylabel("samples")
    ax.set_title("BenchCAD family distribution — top-40 of 112",
                 loc="left", fontweight="semibold")
    ax.set_xlim(-0.6, len(fam_counts) - 0.4)
    ax.margins(x=0.005)
    ax.grid(axis="x", visible=False)

    # legend on side, no frame
    macros_used = list(fam_counts["macro"].unique())
    handles = [mpatches.Patch(color=PALETTE[m], label=m) for m in macros_used]
    ax.legend(handles=handles, loc="upper right", title="Macro bucket",
              title_fontsize=9, fontsize=8.5, frameon=False)
    _annotate_total(ax, len(df))
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 2. Difficulty heatmap ──────────────────────
def fig_difficulty_heatmap(out: Path) -> None:
    df = synth_parts()
    top = df.groupby("family").size().sort_values(ascending=False).head(25).index
    sub = df[df["family"].isin(top)]
    pivot = (sub.groupby(["family", "difficulty"]).size()
             .unstack(fill_value=0)
             .reindex(index=top, columns=["easy", "medium", "hard"], fill_value=0))

    fig, ax = plt.subplots(figsize=(7, 7.5))
    sns.heatmap(pivot, annot=True, fmt="d", cmap="rocket_r", ax=ax,
                cbar_kws={"label": "samples", "shrink": 0.6}, linewidths=0.4,
                linecolor="white", annot_kws={"size": 8})
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=8.5, rotation=0)
    ax.set_xticklabels(ax.get_xticklabels(), fontsize=10)
    ax.set_title("Difficulty × family — top-25 families",
                 loc="left", fontweight="semibold", pad=10)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 3. Status breakdown ──────────────────────
def fig_status_breakdown(out: Path) -> None:
    df = synth_parts()
    status = df["status"].fillna("unknown").value_counts()

    rj = df[df["status"] == "rejected"]
    rr = rj["reject_reason"].fillna("(unspecified)").value_counts().head(8)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5),
                             gridspec_kw={"width_ratios": [1, 1.6]})

    # left: donut
    pie_colors = ["#55A868", "#C44E52", "#DD8452", "#4C72B0", "#999999"][:len(status)]
    wedges, _ = axes[0].pie(status.values, colors=pie_colors,
                             startangle=90, counterclock=False,
                             wedgeprops={"width": 0.36, "edgecolor": "white", "linewidth": 2})
    axes[0].text(0, 0.05, f"{len(df):,}", ha="center", va="center",
                 fontsize=20, fontweight="bold", color="#333", fontfamily=_FONT)
    axes[0].text(0, -0.18, "samples", ha="center", va="center",
                 fontsize=10, color="#666", fontfamily=_FONT)
    axes[0].set_title("Pipeline status", loc="left", fontweight="semibold")
    axes[0].legend(wedges, [f"{k}  ({v:,})" for k, v in status.items()],
                   loc="center left", bbox_to_anchor=(1.0, 0.5),
                   fontsize=9, frameon=False)

    # right: top reject reasons
    lbls = [s[:60] + "…" if len(s) > 60 else s for s in rr.index]
    axes[1].barh(range(len(rr)), rr.values, color="#C44E52",
                 edgecolor="white", linewidth=0.5)
    axes[1].set_yticks(range(len(rr)))
    axes[1].set_yticklabels(lbls, fontsize=9)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("count")
    axes[1].set_title(f"Top reject reasons  (rejected = {len(rj):,})",
                      loc="left", fontweight="semibold")
    axes[1].grid(axis="y", visible=False)
    for i, v in enumerate(rr.values):
        axes[1].text(v, i, f"  {v:,}", va="center", fontsize=8.5, color="#444")
    axes[1].set_xlim(0, rr.max() * 1.15)

    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 4. Macro taxonomy treemap ──────────────────────
def fig_macro_taxonomy(out: Path) -> None:
    df = synth_parts()
    macro_totals = df.groupby("macro").size().sort_values(ascending=False)
    fam_totals = df.groupby(["macro", "family"]).size().reset_index(name="n")

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Build hierarchical treemap: macro at top level, families inside.
    # Use squarify per macro region.
    rect = dict(x=0, y=0, dx=100, dy=60)
    macro_rects = squarify.padded_squarify(
        squarify.normalize_sizes(macro_totals.values, rect["dx"], rect["dy"]),
        rect["x"], rect["y"], rect["dx"], rect["dy"]
    )

    # darker shade per macro for the inner family fills
    def _darken(hexc: str, k: float = 0.78) -> tuple[float, float, float]:
        h = hexc.lstrip("#")
        r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
        return (r * k, g * k, b * k)

    PRETTY = {  # cleaner labels for narrow boxes
        "section_channel": "section / channel",
        "block_assembly":  "block / assembly",
        "plate_panel":     "plate / panel",
        "pipe_tube":       "pipe / tube",
    }

    for macro, mr in zip(macro_totals.index, macro_rects):
        # outer macro rectangle (lighter shade so inner family cells contrast)
        ax.add_patch(plt.Rectangle((mr["x"], mr["y"]), mr["dx"], mr["dy"],
                                    facecolor=PALETTE[macro], edgecolor="white",
                                    linewidth=2.5, alpha=0.30))
        # families inside — darker shade, no alpha so they look filled
        fams = fam_totals[fam_totals["macro"] == macro].sort_values("n", ascending=False)
        dark = _darken(PALETTE[macro], 1.0)
        if len(fams) > 0:
            inner = squarify.padded_squarify(
                squarify.normalize_sizes(fams["n"].values, mr["dx"] - 1.4, mr["dy"] - 1.4),
                mr["x"] + 0.7, mr["y"] + 0.7, mr["dx"] - 1.4, mr["dy"] - 1.4
            )
            for (_, frow), ir in zip(fams.iterrows(), inner):
                ax.add_patch(plt.Rectangle((ir["x"], ir["y"]), ir["dx"], ir["dy"],
                                            facecolor=PALETTE[macro], edgecolor="white",
                                            linewidth=0.6))
                if ir["dx"] > 7 and ir["dy"] > 2.6:
                    label = frow["family"].replace("simple_", "s.")[:24]
                    ax.text(ir["x"] + ir["dx"] / 2, ir["y"] + ir["dy"] / 2,
                            label, ha="center", va="center", fontsize=6.5,
                            color="white", fontfamily=_FONT)

        # macro label OVERLAY at top-left of macro region (above the family cells)
        # use a small white-ish bar so text is always legible
        pretty = PRETTY.get(macro, macro)
        bar_w = max(len(pretty) * 0.85 + 2.6, 12)
        bar_w = min(bar_w, mr["dx"] - 1)
        bar_h = 4.2
        ax.add_patch(plt.Rectangle((mr["x"] + 0.6, mr["y"] + 0.6), bar_w, bar_h,
                                    facecolor=_darken(PALETTE[macro], 0.85),
                                    edgecolor="none", zorder=10))
        ax.text(mr["x"] + 1.0, mr["y"] + 1.05,
                pretty, ha="left", va="top",
                color="white", fontsize=10.5, fontweight="bold",
                fontfamily=_FONT, zorder=11)
        ax.text(mr["x"] + 1.0, mr["y"] + 3.05,
                f"{macro_totals[macro]:,}", ha="left", va="top",
                color="white", fontsize=8.5, fontfamily=_FONT,
                alpha=0.9, zorder=11)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.invert_yaxis()
    ax.set_title("BenchCAD lexical tree — 6 macros × 112 families",
                 loc="left", fontweight="semibold", pad=12, fontsize=13)
    fig.text(0.99, 0.02, f"N = {len(df):,} samples", ha="right", va="bottom",
             color="#888", fontsize=9, fontfamily=_FONT)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 5. ISO standard pareto ──────────────────────
def fig_iso_pareto(out: Path) -> None:
    df = synth_parts()
    std = df["standard"].fillna("(none)").value_counts().head(15)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.bar(range(len(std)), std.values, color=ACCENT,
                  edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(std)))
    ax.set_xticklabels(std.index, rotation=55, ha="right", fontsize=9)
    ax.set_ylabel("samples")
    ax.set_title(f"ISO / DIN standard coverage — top 15 of {df['standard'].nunique()}",
                 loc="left", fontweight="semibold")
    ax.grid(axis="x", visible=False)

    # Pareto cumulative line on twin axis
    ax2 = ax.twinx()
    cum = std.values.cumsum() / len(df) * 100
    ax2.plot(range(len(std)), cum, color=ACCENT2, marker="o",
             linewidth=1.6, markersize=4)
    ax2.set_ylabel("cumulative % of samples", color=ACCENT2)
    ax2.tick_params(axis="y", labelcolor=ACCENT2)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(ACCENT2)
    ax2.grid(False)
    ax2.set_ylim(0, max(100, cum.max() * 1.05))
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 6. Scaling cliff ──────────────────────
def fig_scaling_cliff(out: Path) -> None:
    """MOCK — pending real eval."""
    sizes = np.array([0.5, 1.5, 3, 7, 14, 32, 72])
    iou = np.array([3, 8, 15, 22, 28, 31, 33])
    iou_h = np.array([0, 1, 2, 4, 6, 7, 8])
    human = 80

    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.fill_between(sizes, 0, iou, color=ACCENT, alpha=0.12)
    ax.plot(sizes, iou, "o-", color=ACCENT, markersize=6, linewidth=2,
            label="overall (1.4k Mini)")
    ax.plot(sizes, iou_h, "s-", color=ACCENT2, markersize=6, linewidth=2,
            label="hard column only")
    ax.axhline(human, ls=(0, (4, 4)), color="#333", linewidth=1.4, alpha=0.7)
    ax.text(sizes[0], human + 1.5, f"CAD-engineer human · {human}%",
            color="#333", fontsize=9, fontfamily=_FONT)
    ax.set_xscale("log")
    ax.set_xlabel("Qwen2.5-Coder size  (B parameters)")
    ax.set_ylabel("IoU≥0.99 pass-rate (%)")
    ax.set_title("Scaling cliff — projected (mock numbers)",
                 loc="left", fontweight="semibold")
    ax.set_ylim(-2, 90)
    ax.legend(loc="lower right")

    # annotate the cliff
    ax.annotate("scaling cliff:\n+1.5pp from 32B→72B",
                xy=(72, 33), xytext=(40, 50),
                arrowprops=dict(arrowstyle="->", color="#666", lw=1.2),
                fontsize=9, color="#444", fontfamily=_FONT)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 7. Mini-vs-Full correlation ──────────────────────
def fig_mini_full_correlation(out: Path) -> None:
    rng = np.random.default_rng(42)
    n_models = 30
    full = rng.uniform(5, 35, n_models)
    mini = full + rng.normal(0, 1.5, n_models)
    spearman = pd.Series(full).corr(pd.Series(mini), method="spearman")

    fig, ax = plt.subplots(figsize=(6, 6))
    lo, hi = 0, 40
    ax.plot([lo, hi], [lo, hi], ls=(0, (3, 3)), color="#888", linewidth=1)
    ax.scatter(full, mini, color=ACCENT, s=55, alpha=0.85,
               edgecolor="white", linewidth=0.8)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("BenchCAD-Full IoU≥0.99 pass-rate (%)")
    ax.set_ylabel("BenchCAD-Mini IoU≥0.99 pass-rate (%)")
    ax.set_title("Mini-vs-Full rank preservation (mock)",
                 loc="left", fontweight="semibold")
    ax.text(0.04, 0.96, f"Spearman ρ = {spearman:.2f}\n30 models",
            transform=ax.transAxes, va="top",
            fontsize=10, color="#333", fontfamily=_FONT,
            bbox=dict(facecolor="white", edgecolor="#DDD", boxstyle="round,pad=0.4"))
    ax.set_aspect("equal")
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 8. Pre-flight funnel ──────────────────────
def fig_preflight_funnel(out: Path) -> None:
    stages = ["Family registered\n(candidate)",
              "Build-test pass\n(easy / med / hard)",
              "Geometry valid\n(non-degenerate)",
              "Single-solid\n(no float / no overlap)",
              "Vis-text agreement"]
    counts = [124, 119, 110, 108, 106]
    drops = [0] + [counts[i - 1] - counts[i] for i in range(1, len(counts))]
    surv = np.array(counts) / counts[0]

    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(stages))
    bars = ax.barh(y, surv, color=ACCENT, edgecolor="white",
                   linewidth=0.6, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(stages, fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("survivors  (relative to family register)")
    ax.set_title("BenchCAD pre-flight rule — 124 → 106 families",
                 loc="left", fontweight="semibold")
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.grid(axis="y", visible=False)

    for i, (c, w, d) in enumerate(zip(counts, surv, drops)):
        ax.text(w + 0.012, i, f"{c} families", va="center",
                fontsize=9.5, color="#333", fontfamily=_FONT)
        if d:
            ax.text(w + 0.012, i + 0.30, f"−{d} dropped", va="center",
                    fontsize=8, color=ACCENT2, fontfamily=_FONT, alpha=0.8)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 9. Error taxonomy donut ──────────────────────
def fig_error_taxonomy(out: Path) -> None:
    cats = ["wrong-primitive", "wrong-topology", "wrong-dimension",
            "wrong-constraint", "wrong-axis"]
    pcts = [34, 27, 19, 13, 7]
    colors = ["#4C72B0", "#DD8452", "#55A868", "#8172B2", "#C44E52"]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    wedges, _ = ax.pie(pcts, colors=colors, startangle=90, counterclock=False,
                        wedgeprops={"width": 0.38, "edgecolor": "white", "linewidth": 2})
    ax.text(0, 0.06, "frontier\nLLMs", ha="center", va="center",
            fontsize=12, color="#444", fontweight="semibold", fontfamily=_FONT)
    ax.set_title("BenchCAD error taxonomy — projected (mock)",
                 loc="left", fontweight="semibold")
    # legend with percentages
    legend_lbls = [f"{c}  ·  {p}%" for c, p in zip(cats, pcts)]
    ax.legend(wedges, legend_lbls, loc="center left",
              bbox_to_anchor=(1.05, 0.5), fontsize=10, frameon=False)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 10. Hero composite ──────────────────────
def fig_hero_composite(out: Path) -> None:
    df = synth_parts()
    fig = plt.figure(figsize=(13.5, 8.2))
    gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.42,
                          width_ratios=[1.05, 1, 1], height_ratios=[1, 1.05])

    # (a) macro bar
    ax = fig.add_subplot(gs[0, 0])
    mc = df.groupby("macro").size().sort_values(ascending=False)
    ax.bar(range(len(mc)), mc.values,
           color=[PALETTE[m] for m in mc.index],
           edgecolor="white", linewidth=0.6)
    ax.set_xticks(range(len(mc)))
    ax.set_xticklabels(mc.index, rotation=25, ha="right", fontsize=8.5)
    ax.set_title("(a) 112 families → 6 macros",
                 loc="left", fontweight="semibold", fontsize=11)
    ax.set_ylabel("samples", fontsize=9.5)
    ax.grid(axis="x", visible=False)

    # (b) difficulty
    ax = fig.add_subplot(gs[0, 1])
    diff = df["difficulty"].value_counts().reindex(["easy", "medium", "hard"], fill_value=0)
    ax.bar(diff.index, diff.values, color=[DIFF_COLORS[d] for d in diff.index],
           edgecolor="white", linewidth=0.6, width=0.65)
    ax.set_title("(b) Difficulty stratification",
                 loc="left", fontweight="semibold", fontsize=11)
    ax.set_ylabel("samples", fontsize=9.5)
    ax.grid(axis="x", visible=False)
    for i, v in enumerate(diff.values):
        ax.text(i, v + max(diff.values) * 0.02, f"{v:,}",
                ha="center", va="bottom", fontsize=9, fontfamily=_FONT)
    ax.set_ylim(0, max(diff.values) * 1.15)

    # (c) scaling cliff
    ax = fig.add_subplot(gs[0, 2])
    sizes = np.array([0.5, 1.5, 3, 7, 14, 32, 72])
    iou = np.array([3, 8, 15, 22, 28, 31, 33])
    iou_h = np.array([0, 1, 2, 4, 6, 7, 8])
    ax.fill_between(sizes, 0, iou, color=ACCENT, alpha=0.12)
    ax.plot(sizes, iou, "o-", color=ACCENT, markersize=5, linewidth=1.8, label="overall")
    ax.plot(sizes, iou_h, "s-", color=ACCENT2, markersize=5, linewidth=1.8, label="hard")
    ax.axhline(80, ls=(0, (3, 3)), color="#333", linewidth=1, alpha=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("model size (B)", fontsize=9.5)
    ax.set_ylabel("IoU≥0.99 pass (%)", fontsize=9.5)
    ax.set_title("(c) Scaling cliff — Qwen2.5-Coder",
                 loc="left", fontweight="semibold", fontsize=11)
    ax.legend(fontsize=8.5, loc="lower right")

    # (d) headline gap bar
    ax = fig.add_subplot(gs[1, :])
    models = ["Qwen2.5-Coder-0.5B", "Qwen2.5-Coder-7B", "DeepSeek-V3", "Claude-4",
              "GPT-5", "CAD-Coder-7B", "cadrille-2B", "CADEvolve", "Human (CAD eng.)"]
    overall = [3, 22, 28, 31, 33, 24, 19, 26, 80]
    hard = [0, 4, 6, 7, 8, 5, 3, 6, 75]
    x = np.arange(len(models))
    ax.bar(x - 0.20, overall, width=0.38, label="overall", color=ACCENT,
           edgecolor="white", linewidth=0.6)
    ax.bar(x + 0.20, hard, width=0.38, label="hard column", color=ACCENT2,
           edgecolor="white", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=22, ha="right", fontsize=9.5)
    ax.set_ylabel("IoU≥0.99 pass-rate (%)")
    ax.set_title("(d) Headline — human-vs-model gap on BenchCAD-Mini (1.4k subset, mock)",
                 loc="left", fontweight="semibold", fontsize=11)
    ax.axvline(len(models) - 1.5, ls=(0, (4, 4)), color="#888",
               linewidth=1, alpha=0.7)
    ax.legend(loc="upper left", fontsize=9.5)
    ax.grid(axis="x", visible=False)
    # annotate human gap
    for i, (a, b) in enumerate(zip(overall, hard)):
        ax.text(x[i] - 0.20, a + 1, str(a), ha="center", va="bottom",
                fontsize=8, color="#333", fontfamily=_FONT)

    fig.suptitle("BenchCAD — Hero composite", x=0.005, ha="left",
                 fontsize=16, fontweight="bold", y=0.995, fontfamily=_FONT)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 11. Op-coverage gallery ──────────────────────
def fig_op_coverage_gallery(out: Path) -> None:
    candidates = [
        Path("data/data_generation/simple_ops_100k/png"),
        Path("data/data_generation/iso_106_codegen/png"),
        Path("data/data_generation/simple_ops_preview/png"),
    ]
    composites: list[Path] = []
    for src in candidates:
        if src.exists():
            composites.extend(sorted(src.rglob("*composite*.png")))
    if not composites:
        for src in candidates:
            if src.exists():
                composites.extend(sorted(src.rglob("*.png")))
    if not composites:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "No rendered PNGs found", ha="center", va="center")
        ax.set_axis_off()
        fig.savefig(out)
        plt.close(fig)
        return

    seen, picks = set(), []
    for p in composites:
        try:
            idx = p.parts.index("png")
            fam = p.parts[idx + 1]
        except (ValueError, IndexError):
            fam = p.stem
        if fam not in seen:
            seen.add(fam)
            picks.append((fam, p))
        if len(picks) == 9:
            break
    while len(picks) < 9 and composites:
        picks.append((composites[len(picks) % len(composites)].stem,
                      composites[len(picks) % len(composites)]))

    fig, axes = plt.subplots(3, 3, figsize=(10, 10), facecolor="white")
    fig.subplots_adjust(top=0.93, hspace=0.18, wspace=0.05)
    for ax, (fam, p) in zip(axes.flatten(), picks):
        try:
            img = Image.open(p)
            ax.imshow(img)
            ax.set_title(fam.replace("simple_", "s."), fontsize=10,
                         fontfamily=_FONT, pad=4)
        except Exception:
            ax.text(0.5, 0.5, "(no img)", ha="center", va="center")
        ax.set_axis_off()
    fig.suptitle("BenchCAD op-coverage gallery — 9 random families",
                 fontsize=14, fontweight="semibold", x=0.05, y=0.98, ha="left",
                 fontfamily=_FONT)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 12. Modality ablation ──────────────────────
def fig_modality_ablation(out: Path) -> None:
    models = ["GPT-5", "Claude-4", "DeepSeek-V3", "Gemini-2.5", "Qwen2.5-VL-72B"]
    img_only = [33, 31, 28, 26, 21]
    json_only = [38, 36, 34, 31, 25]
    both = [42, 40, 36, 34, 28]
    x = np.arange(len(models))
    w = 0.26

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.bar(x - w, img_only, width=w, label="image only", color="#4C72B0",
           edgecolor="white", linewidth=0.5)
    ax.bar(x, json_only, width=w, label="json only", color="#55A868",
           edgecolor="white", linewidth=0.5)
    ax.bar(x + w, both, width=w, label="image + json", color="#DD8452",
           edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15, ha="right", fontsize=9.5)
    ax.set_ylabel("IoU≥0.99 pass-rate (%)")
    ax.set_title("Triple-modality ablation — same item, three input formats (mock)",
                 loc="left", fontweight="semibold")
    ax.legend(loc="upper right", ncol=3)
    ax.grid(axis="x", visible=False)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 13. Gap-vs-prior table (PIL) ──────────────────────
def fig_gap_table(out: Path) -> None:
    rows = [
        ("DeepCAD",          "B-rep",       "?",     0, 0, 0, 0, 0, 0),
        ("Text2CAD",         "DSL",         "170k",  1, 0, 0, 0, 0, 0),
        ("CAD-Recode",       "CadQuery",    "1M",    1, 0, 0, 0, 0, 0),
        ("CADPrompt",        "CadQuery",    "200",   1, 0, 1, 0, 0, 0),
        ("BlenderLLM/Bench", "Blender-py",  "200",   1, 1, 0, 0, 0, 0),
        ("Text-to-CadQuery", "CadQuery",    "170k",  1, 0, 0, 0, 0, 0),
        ("HistCAD",          "B-rep + his", "?",     1, 0, 1, 0, 0, 0),
        ("BenchCAD (ours)",  "CadQuery",    "17.8k", 1, 1, 1, 1, 1, 1),
    ]
    cols = ["Bench", "Output", "N items",
            "Exec\ngrade", "ISO\nstd", "5-task\nsuite",
            "Mini/Full", "Held-out\nprivate", "Op\ndiversity"]

    # PIL render — full typographic control
    import matplotlib as mpl
    dejavu = Path(mpl.__file__).parent / "mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"
    dejavu_reg = Path(mpl.__file__).parent / "mpl-data/fonts/ttf/DejaVuSans.ttf"
    try:
        font_h = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        font_b = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_n = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font_h = ImageFont.truetype(str(dejavu), 26)
        font_b = ImageFont.truetype(str(dejavu), 18)
        font_n = ImageFont.truetype(str(dejavu_reg), 18)
    # checkmarks: DejaVu Sans definitely has ✓ ✗
    font_check = ImageFont.truetype(str(dejavu), 24)

    # column widths (px)
    cw = [200, 130, 90, 95, 80, 100, 100, 110, 105]
    h_title = 50
    h_header = 65
    h_row = 48
    pad = 28
    W = sum(cw) + pad * 2
    H = h_title + h_header + h_row * len(rows) + pad * 2

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Title
    d.text((pad, pad), "Gap vs prior CAD-code benchmarks",
           fill="#222", font=font_h)
    d.line([(pad, pad + h_title - 4), (W - pad, pad + h_title - 4)],
           fill="#222", width=2)

    # Header row
    y = pad + h_title + 4
    x = pad
    for c, w in zip(cols, cw):
        # multi-line header support
        lines = c.split("\n")
        for i, ln in enumerate(lines):
            tw = d.textlength(ln, font=font_b)
            d.text((x + (w - tw) / 2, y + 8 + i * 22), ln,
                   fill="#333", font=font_b)
        x += w
    d.line([(pad, y + h_header - 2), (W - pad, y + h_header - 2)],
           fill="#888", width=1)

    # Body rows
    for ri, row in enumerate(rows):
        y_row = y + h_header + ri * h_row
        is_ours = ri == len(rows) - 1
        if is_ours:
            d.rectangle([pad, y_row, W - pad, y_row + h_row],
                        fill="#EAF2FB")
        x = pad
        for ci, (val, w) in enumerate(zip(row, cw)):
            cell_y = y_row + (h_row - 24) // 2
            if ci < 3:
                # text columns
                fnt = font_b if is_ours else font_n
                col = "#1A3F70" if is_ours and ci == 0 else ("#222" if is_ours else "#333")
                tw = d.textlength(str(val), font=fnt)
                d.text((x + (w - tw) / 2, cell_y - 1), str(val),
                       fill=col, font=fnt)
            else:
                # ✓ / ✗ columns
                ch = "✓" if val == 1 else "✗"
                color = "#2A8A2A" if val == 1 else "#C03030"
                tw = d.textlength(ch, font=font_check)
                d.text((x + (w - tw) / 2, cell_y - 2), ch,
                       fill=color, font=font_check)
            x += w
        # row separator
        d.line([(pad, y_row + h_row), (W - pad, y_row + h_row)],
               fill="#EEE", width=1)

    img.save(out)


# ────────────────────── 14. Construction pipeline ──────────────────────
def fig_construction_pipeline(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4)
    ax.set_axis_off()

    boxes = [
        ("Family\nregistry\n(112)",                  PALETTE["fastener"]),
        ("builder.\nbuild_from_\nprogram",           PALETTE["plate_panel"]),
        ("IoU≥0.99 verify\n(rotation-inv\nmesh match)", PALETTE["block_assembly"]),
        ("4-view render\n(front · right ·\ntop · iso)", "#8172B2"),
        ("5-task pairs:\nimg2cq · json2cq\nedit · qa · repair", PALETTE["section_channel"]),
    ]
    bw, bh = 2.2, 1.55
    gap = 0.35
    x_start = 0.4

    for i, (label, color) in enumerate(boxes):
        x = x_start + i * (bw + gap)
        # rounded box (FancyBboxPatch)
        box = mpatches.FancyBboxPatch((x, 1.4), bw, bh,
                                        boxstyle="round,pad=0.04,rounding_size=0.18",
                                        linewidth=0, facecolor=color, alpha=0.95)
        ax.add_patch(box)
        ax.text(x + bw / 2, 1.4 + bh / 2, label,
                ha="center", va="center", color="white",
                fontsize=10, fontweight="semibold", fontfamily=_FONT,
                linespacing=1.3)
        if i < len(boxes) - 1:
            arrow_x = x + bw + 0.04
            ax.annotate("", xy=(arrow_x + gap - 0.08, 2.18),
                        xytext=(arrow_x, 2.18),
                        arrowprops=dict(arrowstyle="->", color="#666", lw=2))

    ax.text(6.5, 3.55, "BenchCAD construction pipeline", ha="center",
            fontsize=15, fontweight="bold", fontfamily=_FONT)
    ax.text(6.5, 0.55,
            "all stages auto-checked, fail-closed; pre-flight rule (CLAUDE.md) blocks bad families before they enter the registry",
            ha="center", fontsize=9.5, color="#666", style="italic", fontfamily=_FONT)
    fig.savefig(out)
    plt.close(fig)


# ────────────────────── 15. Difficulty per macro stacked ──────────────────────
def fig_difficulty_per_macro(out: Path) -> None:
    df = synth_parts()
    pivot = df.groupby(["macro", "difficulty"]).size().unstack(fill_value=0)
    pivot = pivot.reindex(columns=["easy", "medium", "hard"], fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(pivot))
    for d_lab in ["easy", "medium", "hard"]:
        ax.bar(pivot.index, pivot[d_lab], bottom=bottom, label=d_lab,
               color=DIFF_COLORS[d_lab], edgecolor="white", linewidth=0.5,
               width=0.62)
        bottom += pivot[d_lab].values
    ax.set_ylabel("samples")
    ax.set_title("Difficulty mix per macro bucket",
                 loc="left", fontweight="semibold")
    ax.legend(loc="upper right", title="difficulty", title_fontsize=9, frameon=False)
    ax.set_xticklabels([t.get_text() for t in ax.get_xticklabels()],
                       rotation=15, ha="right")
    ax.grid(axis="x", visible=False)
    # add totals on top
    totals = pivot.sum(axis=1)
    for i, (m, t) in enumerate(totals.items()):
        ax.text(i, t + max(totals) * 0.02, f"{t:,}",
                ha="center", va="bottom", fontsize=9, color="#444",
                fontfamily=_FONT)
    ax.set_ylim(0, max(totals) * 1.12)
    fig.savefig(out)
    plt.close(fig)
