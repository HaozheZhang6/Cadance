from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from bench.build_test_manifest import _sample_rows, _to_manifest_row
from bench.score_benchmark import score_predictions


def test_build_test_manifest_sampling():
    rows = [
        {"sample_id": "a1", "family": "gear", "status": "accepted", "step_path": "x/gear/a1/gen.step", "render_dir": "x/gear/a1/views", "code_path": "x/gear/a1/code.py", "meta_path": "x/gear/a1/meta.json", "difficulty": "hard", "stem": "a1", "pipeline_run": "run"},
        {"sample_id": "a2", "family": "gear", "status": "accepted", "step_path": "x/gear/a2/gen.step", "render_dir": "x/gear/a2/views", "code_path": "x/gear/a2/code.py", "meta_path": "x/gear/a2/meta.json", "difficulty": "hard", "stem": "a2", "pipeline_run": "run"},
        {"sample_id": "b1", "family": "plate", "status": "accepted", "step_path": "x/plate/b1/gen.step", "render_dir": "x/plate/b1/views", "code_path": "x/plate/b1/code.py", "meta_path": "x/plate/b1/meta.json", "difficulty": "easy", "stem": "b1", "pipeline_run": "run"},
        {"sample_id": "b2", "family": "plate", "status": "accepted", "step_path": "x/plate/b2/gen.step", "render_dir": "x/plate/b2/views", "code_path": "x/plate/b2/code.py", "meta_path": "x/plate/b2/meta.json", "difficulty": "easy", "stem": "b2", "pipeline_run": "run"},
        {"sample_id": "b3", "family": "plate", "status": "accepted", "step_path": "x/plate/b3/gen.step", "render_dir": "x/plate/b3/views", "code_path": "x/plate/b3/code.py", "meta_path": "x/plate/b3/meta.json", "difficulty": "easy", "stem": "b3", "pipeline_run": "run"},
    ]
    selected = _sample_rows(rows, test_ratio=0.2, seed=42)

    assert len(selected) == 2
    assert {row["family"] for row in selected} == {"gear", "plate"}


def test_to_manifest_row_builds_expected_paths():
    row = {
        "sample_id": "sample_1",
        "stem": "stem_1",
        "family": "gear",
        "difficulty": "hard",
        "render_dir": "foo/bar/views",
        "step_path": "foo/bar/gen.step",
        "code_path": "foo/bar/code.py",
        "meta_path": "foo/bar/meta.json",
        "pipeline_run": "run_a",
    }
    manifest_row = _to_manifest_row(row)

    assert manifest_row["gt_mesh"] == "foo/bar/mesh.stl"
    assert manifest_row["input_views"][0] == "foo/bar/views/view_0.png"


def test_score_predictions_computes_overall_and_per_family():
    manifest = {
        "sample_1": {"sample_id": "sample_1", "family": "gear", "difficulty": "hard", "gt_code": "gt1.py", "gt_mesh": "gt1.stl"},
        "sample_2": {"sample_id": "sample_2", "family": "plate", "difficulty": "easy", "gt_code": "gt2.py", "gt_mesh": "gt2.stl"},
        "sample_3": {"sample_id": "sample_3", "family": "plate", "difficulty": "easy", "gt_code": "gt3.py", "gt_mesh": "gt3.stl"},
    }
    predictions = [
        {"sample_id": "sample_1", "valid": True, "iou": 0.5, "cd": 0.2},
        {"sample_id": "sample_2", "valid": True, "iou": 0.9, "cd": 0.1},
        {"sample_id": "sample_3", "valid": False, "iou": 0.0, "cd": None},
    ]

    summary = score_predictions(predictions, manifest)

    assert summary["overall"]["count"] == 3
    assert summary["overall"]["valid_rate"] == 0.6667
    assert summary["overall"]["mean_iou"] == 0.4667
    assert len(summary["per_family"]) == 2
    assert summary["weakest_families"][0]["family"] == "plate"
