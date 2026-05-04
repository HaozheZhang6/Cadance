"""Plot SFT training-curve panels from CSVs in this folder.

No markers — line-only, ready for the main figure.
All panels show 3 curves: ood, iid, baseline.

Outputs individual PNGs + a 4x3 composite into THIS folder.
"""
from pathlib import Path
import csv

import matplotlib.pyplot as plt
import matplotlib as mpl

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE  # write next to the CSVs

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.linewidth": 0.9,
})

# (column, label, colour) — order = legend order
CURVES = [
    ("ood",         "ood",      "#ab2424"),
    ("iid_v3",      "iid",      "#257536"),
    ("baseline",    "baseline", "#888888"),
]

# (csv, png_stem, title, ylabel, ymax, grid_pos)
PANELS = [
    # row 0: IoU
    ("v1_iid_iou.csv", "fig_sft_iid_iou", "BenchCAD val IID — IoU",   "IoU", 0.8, (0, 0)),
    ("v1_ood_iou.csv", "fig_sft_ood_iou", "BenchCAD val OOD — IoU",   "IoU", 0.8, (0, 1)),
    ("v1_dc_iou.csv",  "fig_sft_dc_iou",  "DeepCAD test — IoU",       "IoU", 0.8, (0, 2)),
    ("v1_fu_iou.csv",  "fig_sft_fu_iou",  "Fusion360 test — IoU",     "IoU", 0.8, (0, 3)),
    # row 1: Exec rate
    ("v1_iid_exec.csv", "fig_sft_iid_exec", "BenchCAD val IID — Exec", "exec rate", 1.05, (1, 0)),
    ("v1_ood_exec.csv", "fig_sft_ood_exec", "BenchCAD val OOD — Exec", "exec rate", 1.05, (1, 1)),
    ("v1_dc_exec.csv",  "fig_sft_dc_exec",  "DeepCAD test — Exec",     "exec rate", 1.05, (1, 2)),
    ("v1_fu_exec.csv",  "fig_sft_fu_exec",  "Fusion360 test — Exec",   "exec rate", 1.05, (1, 3)),
    # row 2: Essential-Op pass rate
    ("v1_iid_ess.csv", "fig_sft_iid_ess", "BenchCAD val IID — Essential-Op", "essential-op pass rate", 1.0, (2, 0)),
    ("v1_ood_ess.csv", "fig_sft_ood_ess", "BenchCAD val OOD — Essential-Op", "essential-op pass rate", 1.0, (2, 1)),
]

XMAX = 25000


def parse_float(x):
    if x is None or x == "":
        return float("nan")
    return float(x)


def read_csv(path):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    return {c: [parse_float(r[c]) for r in rows] for c in cols}


def draw_panel(ax, csv_path, title, ylabel, ymax, show_legend=False):
    data = read_csv(csv_path)
    x_all = data["step"]
    for col, label, color in CURVES:
        if col not in data:
            continue
        xs, ys = [], []
        for xi, yi in zip(x_all, data[col]):
            if yi == yi:
                xs.append(xi)
                ys.append(yi)
        if len(xs) < 2:
            continue
        ax.plot(xs, ys, label=label, color=color, linewidth=2.0, alpha=0.95)
    ax.set_title(title, loc="left", pad=6, fontweight="bold")
    ax.set_xlabel("training step")
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, XMAX)
    ax.set_ylim(-0.05, ymax)
    ax.grid(True, alpha=0.3, linestyle=":", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if show_legend:
        ax.legend(frameon=False, loc="lower right")


def render_individual(csv_name, png_stem, title, ylabel, ymax):
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    draw_panel(ax, HERE / csv_name, title, ylabel, ymax, show_legend=True)
    plt.tight_layout()
    out = OUT_DIR / f"{png_stem}.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.name} ({out.stat().st_size // 1024} KB)")


def render_composite():
    fig, axes = plt.subplots(3, 4, figsize=(18, 11))
    used = set()
    for csv_name, _stem, title, ylabel, ymax, (r, c) in PANELS:
        ax = axes[r, c]
        draw_panel(ax, HERE / csv_name, title, ylabel, ymax, show_legend=False)
        used.add((r, c))
    for r in range(3):
        for c in range(4):
            if (r, c) not in used:
                axes[r, c].axis("off")

    handles_lookup = {}
    for ax in axes.flatten():
        for h, l in zip(*ax.get_legend_handles_labels()):
            handles_lookup.setdefault(l, h)
    label_order = [l for _, l, _ in CURVES]
    ordered = [(l, handles_lookup[l]) for l in label_order if l in handles_lookup]
    fig.legend([h for _, h in ordered], [l for l, _ in ordered],
               loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.005), handletextpad=0.6, columnspacing=2.0)

    plt.tight_layout(rect=(0, 0, 1, 0.96))
    out = OUT_DIR / "fig_sft_main.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.name} ({out.stat().st_size // 1024} KB)")


def main():
    for csv_name, png_stem, title, ylabel, ymax, _pos in PANELS:
        render_individual(csv_name, png_stem, title, ylabel, ymax)
    render_composite()


if __name__ == "__main__":
    main()
