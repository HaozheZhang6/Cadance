"""All-106-family essential-op table — v4 with AND-of-(OR-tuples) format.

Format displayed: spec written as `(a | b) AND c` where `|` means OR within
a tuple and `AND` means required-also across the outer list. Independent of
chamfer/fillet/hole feature class (those are separate score).
"""
from __future__ import annotations

import io
import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "bench/research/outputs/run_2026_04_27"
sys.path.insert(0, str(Path(__file__).parent))

from canonical_ops import (  # noqa: E402
    ESSENTIAL_BY_FAMILY, essential_pass, find_ops, fmt_spec,
)


def main(out: Path) -> None:
    from datasets import load_dataset

    print("loading cad_bench_722 ...")
    df = load_dataset("BenchCAD/cad_bench_722")["train"].to_pandas()

    fam_n = df["family"].value_counts().to_dict()
    rows = []
    for fam in sorted(fam_n):
        n = fam_n[fam]
        spec = ESSENTIAL_BY_FAMILY.get(fam)
        sub = df[df.family == fam]
        if not spec:
            rows.append((fam, None, "gray", "N/A", n))
            continue
        gt_pass = sum(
            1 for code in sub["gt_code"]
            if essential_pass(fam, find_ops(code or ""))
        )
        cov = gt_pass / n
        cls = "green" if cov >= 0.9 else "yellow" if cov >= 0.5 else "orange"
        rows.append((fam, cov, cls, fmt_spec(spec), n))

    cls_rank = {"green": 0, "yellow": 1, "orange": 2, "gray": 3}
    rows.sort(key=lambda r: (cls_rank[r[2]], r[0]))
    n_rows = len(rows)
    counts = Counter(r[2] for r in rows)
    print(f"families: green={counts['green']}  yellow={counts['yellow']}  "
          f"orange={counts.get('orange', 0)}  gray={counts['gray']}  total={n_rows}")

    # collect renders
    rec = {}
    for _, r in df.iterrows():
        if r["family"] in rec:
            continue
        cp = r["composite_png"]
        if isinstance(cp, dict) and "bytes" in cp:
            img = Image.open(io.BytesIO(cp["bytes"]))
        elif isinstance(cp, bytes):
            img = Image.open(io.BytesIO(cp))
        else:
            img = cp
        rec[r["family"]] = img

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "STIXGeneral"],
        "mathtext.fontset": "stix",
    })

    cols = 4
    rows_per_grid = (n_rows + cols - 1) // cols
    fig_w = 14.0
    panel_h = 1.55
    title_h = 1.1
    fig_h = rows_per_grid * panel_h + title_h + 0.4
    fig = plt.figure(figsize=(fig_w, fig_h))

    title_ax = fig.add_axes([0.02, 1 - title_h / fig_h, 0.96, title_h / fig_h])
    title_ax.axis("off")
    title_ax.text(
        0.0, 0.95, "Table 5 (v4). ", fontweight="bold", fontsize=10,
        va="top", ha="left", transform=title_ax.transAxes,
    )
    title_ax.text(
        0.085, 0.95,
        "Per-family essential ops on the 720-case BenchCAD — AND-of-(OR-tuples) "
        "format. Spec syntax: `(a | b) AND c` ⇒ gen must contain (a OR b) AND c. "
        "Match is binary: full score iff every outer element is satisfied. "
        "Alternatives encode geometric equivalence (revolve(360°) ≡ closed-path "
        "sweep; eye = makeTorus | revolved circle | swept ring; twistExtrude ≈ "
        "loft of N rotated cross-sections). "
        "Independent of FEATURE_CLASS = {chamfer, fillet, hole} which is scored "
        "separately as has_* F1. "
        "GREEN ✓ cov ≥ 0.9 (gt of every variant satisfies); "
        "YELLOW ? 0.5–0.9 (variants); "
        "GRAY — N/A (family has no essential — any valid construction works).",
        fontsize=8.5, va="top", ha="left", transform=title_ax.transAxes,
        wrap=True,
    )

    BG = {"green": "#e9f5e0", "yellow": "#fff3c4", "orange": "#fde0c8", "gray": "#e8e8e8"}
    EDGE = {"green": "#3a7a2c", "yellow": "#b5891b", "orange": "#a85b1a", "gray": "#999999"}
    SYM = {"green": "✓", "yellow": "?", "orange": "!", "gray": "—"}

    body_top = 1 - title_h / fig_h
    body_bot = 0.01
    body_h = body_top - body_bot
    cell_h = body_h / rows_per_grid
    cell_w = 1.0 / cols

    for i, (fam, cov, cls, spec_str, n) in enumerate(rows):
        r, c = divmod(i, cols)
        x0 = 0.005 + c * cell_w
        y0 = body_top - (r + 1) * cell_h

        bg_ax = fig.add_axes([x0 + 0.004, y0 + 0.005, cell_w - 0.012, cell_h - 0.01])
        bg_ax.set_xticks([]); bg_ax.set_yticks([])
        bg_ax.set_facecolor(BG[cls])
        for s in bg_ax.spines.values():
            s.set_edgecolor(EDGE[cls])
            s.set_linewidth(0.7)

        thumb_h_frac = cell_h * 0.85
        thumb_h_in = thumb_h_frac * fig_h
        thumb_w_frac = thumb_h_in / fig_w
        ax_img = fig.add_axes([x0 + 0.013, y0 + cell_h * 0.075, thumb_w_frac, thumb_h_frac])
        ax_img.axis("off")
        ax_img.imshow(rec[fam])

        text_x = x0 + thumb_w_frac + 0.018
        text_w = cell_w - thumb_w_frac - 0.024
        ax_txt = fig.add_axes([text_x, y0, text_w, cell_h])
        ax_txt.axis("off")
        ax_txt.text(
            0.0, 0.85, f"{SYM[cls]}  {fam.replace('_', ' ')}",
            fontsize=8.5, fontweight="bold", color=EDGE[cls],
            va="top", ha="left", transform=ax_txt.transAxes,
        )
        if cls == "gray":
            ax_txt.text(
                0.0, 0.55, "N/A — no essential",
                fontsize=7.4, color="#666",
                va="top", ha="left", transform=ax_txt.transAxes,
            )
        else:
            ax_txt.text(
                0.0, 0.58, f"essential:",
                fontsize=7.6, fontweight="bold", color="#222",
                va="top", ha="left", transform=ax_txt.transAxes,
            )
            ax_txt.text(
                0.0, 0.42, spec_str,
                fontsize=7.4, color="#222",
                va="top", ha="left", transform=ax_txt.transAxes,
            )
            ax_txt.text(
                0.0, 0.18, f"cov: {cov:.2f}  (N={n})",
                fontsize=7.0, color="#444",
                va="top", ha="left", transform=ax_txt.transAxes,
            )
        if cls == "gray":
            ax_txt.text(
                0.0, 0.18, f"N={n}",
                fontsize=7.0, color="#666",
                va="top", ha="left", transform=ax_txt.transAxes,
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}")
    print(f"saved -> {out.with_suffix('.pdf')}")


if __name__ == "__main__":
    main(OUT / "tab_canonical_ops_722_v4.png")
