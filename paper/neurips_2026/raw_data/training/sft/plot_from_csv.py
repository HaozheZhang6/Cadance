from pathlib import Path
import csv

import matplotlib.pyplot as plt


CONFIG = {
    "data_dir": Path("/mnt/data/smoothed_csv_curves"),
    "files": {
        "ood_iou_vs_training_step.csv": {
            "title": "§7.b OOD IoU vs training step (smoothed, 0-25k)",
            "ylabel": "IoU (mean over OOD samples)",
        },
        "ood_exec_rate.csv": {
            "title": "Appendix — OOD exec rate (smoothed, 0-25k)",
            "ylabel": "exec rate",
        },
        "iid_iou_control.csv": {
            "title": "Appendix — IID IoU control (smoothed, 0-25k)",
            "ylabel": "IoU (mean over IID samples)",
        },
    },
    "labels": {
        "iid_v3_baseline": "(1) iid — v3 baseline",
        "ood_enhance_v4": "(3) ood_enhance — holdout + benchcad-easy (v4)",
        "baseline_hq_only": "(4) baseline — HQ only",
        "ood_holdout_no_benchcad_easy": "(2) ood — holdout, no benchcad-easy",
    },
    "colors": {
        "iid_v3_baseline": "#3da44a",
        "ood_enhance_v4": "#2f80bd",
        "baseline_hq_only": "#9467bd",
        "ood_holdout_no_benchcad_easy": "#d9343a",
    },
    "markers": {
        "iid_v3_baseline": None,
        "ood_enhance_v4": "s",
        "baseline_hq_only": "^",
        "ood_holdout_no_benchcad_easy": "D",
    },
}


def read_curve_csv(csv_path):
    """Read a curve CSV into a dictionary of numeric columns."""
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = reader.fieldnames

    data = {col: [] for col in columns}
    for row in rows:
        for col in columns:
            data[col].append(float(row[col]))
    return data


def plot_curve_csv(csv_path, output_path, title, ylabel, config):
    """Plot all metric columns in one CSV file."""
    data = read_curve_csv(csv_path)
    x_values = data["training_step"]

    plt.figure(figsize=(10, 6))
    for col in data:
        if col == "training_step":
            continue
        plt.plot(
            x_values,
            data[col],
            label=config["labels"][col],
            color=config["colors"][col],
            marker=config["markers"][col],
            linewidth=2.0,
            markersize=5,
        )

    plt.title(title)
    plt.xlabel("training step")
    plt.ylabel(ylabel)
    plt.xlim(0, 25000)
    plt.ylim(0, 1.02)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, loc="best")
    plt.tight_layout()
    plt.savefig(output_path, dpi=240)
    plt.close()


def main(config):
    """Read each CSV in the config and write one PNG per CSV."""
    data_dir = config["data_dir"]
    for filename, meta in config["files"].items():
        csv_path = data_dir / filename
        output_path = data_dir / filename.replace(".csv", "_from_csv.png")
        plot_curve_csv(
            csv_path=csv_path,
            output_path=output_path,
            title=meta["title"],
            ylabel=meta["ylabel"],
            config=config,
        )
        print(f"saved: {output_path}")


if __name__ == "__main__":
    main(CONFIG)
