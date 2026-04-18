#!/usr/bin/env python
"""Download open-source CAD datasets for data pipeline.

This script keeps downloads in data/data_generation/open_source/downloads/<dataset>/.
It is intentionally explicit about licensing; you must pass --accept-license.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

DATASETS = {
    "fusion360_reconstruction": {
        "urls": [
            "https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1.zip",
            "https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1_extrude_tools.zip",
            "https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1_regraph_05.zip",
        ],
        "license": "https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md",
        "notes": "Fusion 360 Gallery Reconstruction dataset",
    },
    "fusion360_segmentation": {
        "urls": [
            "https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/segmentation/s2.0.1/s2.0.1.zip",
        ],
        "license": "https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md",
        "notes": "Fusion 360 Gallery Segmentation dataset",
    },
    "deepcad": {
        "urls": [
            "https://www.cs.columbia.edu/cg/deepcad/data.tar",
        ],
        "license": "https://github.com/rundiwu/DeepCAD/blob/master/LICENSE",
        "notes": "DeepCAD cad_json/cad_vec data tar",
    },
    "abc_step_list": {
        "urls": [
            "https://deep-geometry.github.io/abc-dataset/data/step_v00.txt",
        ],
        "license": "https://deep-geometry.github.io/abc-dataset/",
        "notes": "ABC dataset STEP file list; use --abc-limit to download a subset",
    },
    "sketchgraphs_shards": {
        "urls": [
            "https://sketchgraphs.cs.princeton.edu/shards/",
        ],
        "license": "https://github.com/PrincetonLIPS/SketchGraphs/blob/master/LICENSE",
        "notes": "SketchGraphs raw shards; use --sketchgraphs-count",
    },
}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "cad-data-downloader"})
    with urllib.request.urlopen(req) as response:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)


def _download_abc_steps(list_url: str, dest_dir: Path, limit: int | None) -> list[Path]:
    req = urllib.request.Request(list_url, headers={"User-Agent": "cad-data-downloader"})
    with urllib.request.urlopen(req) as response:
        text = response.read().decode("utf-8")
    urls = [u.strip() for u in text.split() if u.strip()]
    if limit is not None:
        urls = urls[:limit]

    outputs: list[Path] = []
    for url in urls:
        filename = url.split()[-1].split("/")[-1]
        dest = dest_dir / filename
        _download(url, dest)
        outputs.append(dest)
    return outputs


def _download_sketchgraphs_shards(base_url: str, dest_dir: Path, count: int) -> list[Path]:
    outputs: list[Path] = []
    for i in range(1, count + 1):
        name = f"shard_{i:03d}_of_128.tar.zst"
        url = f"{base_url}{name}"
        dest = dest_dir / name
        _download(url, dest)
        outputs.append(dest)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS.keys()),
        required=True,
        help="Dataset key to download",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/data_generation/open_source/downloads"),
        help="Base directory for downloads",
    )
    parser.add_argument(
        "--accept-license",
        action="store_true",
        help="Confirm you accept dataset license terms",
    )
    parser.add_argument(
        "--abc-limit",
        type=int,
        default=1,
        help="Number of ABC STEP chunks to download",
    )
    parser.add_argument(
        "--sketchgraphs-count",
        type=int,
        default=1,
        help="Number of SketchGraphs shards to download",
    )
    args = parser.parse_args()

    if not args.accept_license:
        print("Refusing to download without --accept-license")
        return 2

    spec = DATASETS[args.dataset]
    out_dir = args.out_dir / args.dataset
    _ensure_dir(out_dir)

    downloaded: list[str] = []

    if args.dataset == "abc_step_list":
        downloaded_paths = _download_abc_steps(
            spec["urls"][0], out_dir, args.abc_limit
        )
        downloaded = [str(p) for p in downloaded_paths]
    elif args.dataset == "sketchgraphs_shards":
        downloaded_paths = _download_sketchgraphs_shards(
            spec["urls"][0], out_dir, args.sketchgraphs_count
        )
        downloaded = [str(p) for p in downloaded_paths]
    else:
        for url in spec["urls"]:
            filename = url.split("/")[-1]
            dest = out_dir / filename
            _download(url, dest)
            downloaded.append(str(dest))

    summary = {
        "dataset": args.dataset,
        "out_dir": str(out_dir),
        "downloaded": downloaded,
        "license": spec["license"],
        "notes": spec["notes"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
