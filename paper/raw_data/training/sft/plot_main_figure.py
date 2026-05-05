"""Compose a 2x2 main-figure panel for the Op Vocabulary / Generalisation Gap section.

Reads `*_digitized.csv` (raw, with missing values) and produces figures/fig_7.png.
"""
from pathlib import Path
import csv

import matplotlib.pyplot as plt
import matplotlib as mpl

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent.parent / "figures" / "fig_7.png"

# Paper-friendly fonts
mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 11,
    "axes.linewidth": 0.9,
})

PANELS = [
    ("essential_pass_rate_digitized.csv",
     "(a) Essential-Op Pass Rate",
     "essential-op pass rate",
     1.0),
    ("ood_iou_vs_training_step_digitized.csv",
     "(b) OOD IoU vs Training Step",
     "OOD IoU",
     0.7),
    ("ood_exec_rate_digitized.csv",
     "(c) OOD Execution Rate",
     "OOD execution rate",
     1.0),
    ("iid_iou_control_digitized.csv",
     "(d) IID IoU (Control)",
     "IID IoU",
     0.7),
]

# Curves in legend order — colour palette tuned for B/W print legibility too
CURVES = [
    ("iid_v3_baseline",
     "(1) IID baseline (train+test in-distribution)",
     "#2c8a3f", "o"),
    ("ood_holdout_no_benchcad_easy",
     "(2) OOD test, no BenchCAD-easy in training",
     "#c92a2a", "D"),
    ("ood_enhance_v4",
     "(3) OOD test, with BenchCAD-easy in training",
     "#1f6fb4", "s"),
    ("baseline_hq_only",
     "(4) HQ-only baseline (no BenchCAD)",
     "#7c4baa", "^"),
]


def parse_float(x):
    if x is None or x == "":
        return float("nan")
    try:
        return float(x)
    except ValueError:
        return float("nan")


def read_csv(path):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    return {c: [parse_float(r[c]) for r in rows] for c in cols}


def plot_panel(ax, csv_path, title, ylabel, ymax):
    data = read_csv(csv_path)
    x = data["training_step"]
    for col, label, color, marker in CURVES:
        if col not in data:
            continue
        ys = data[col]
        # mask NaN by skipping consecutive NaN runs (matplotlib already
        # handles isolated NaNs, but explicit mask keeps line cleaner)
        xs_clean, ys_clean = [], []
        for xi, yi in zip(x, ys):
            if yi == yi:  # not NaN
                xs_clean.append(xi)
                ys_clean.append(yi)
        if not xs_clean:
            continue
        ax.plot(xs_clean, ys_clean, label=label, color=color,
                marker=marker, linewidth=2.0, markersize=5,
                markevery=3, alpha=0.95)
    ax.set_title(title, loc="left", pad=6, fontweight="bold")
    ax.set_xlabel("training step")
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, 25500)
    ax.set_ylim(0, ymax)
    ax.grid(True, alpha=0.3, linestyle=":", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def main():
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5))
    for ax, (fname, title, ylabel, ymax) in zip(axes.flatten(), PANELS):
        plot_panel(ax, HERE / fname, title, ylabel, ymax)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4,
               frameon=False, bbox_to_anchor=(0.5, 1.005),
               handletextpad=0.5, columnspacing=1.5)

    plt.tight_layout(rect=(0, 0, 1, 0.94))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
