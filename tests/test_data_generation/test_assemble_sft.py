"""Tests for scripts/data_generation/assemble_sft.py"""

import json
import os
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts/data_generation"))
import assemble_sft


@pytest.fixture()
def tmp_workspace(tmp_path):
    """Create minimal workspace: views dir, cq file, ops json, csv."""
    views_dir = tmp_path / "views" / "stem_a"
    views_dir.mkdir(parents=True)
    for v in ("front", "right", "top", "iso"):
        (views_dir / f"raw_{v}.png").write_bytes(b"\x89PNG")
        (views_dir / f"gen_{v}.png").write_bytes(b"\x89PNG")

    cq_path = tmp_path / "stem_a.py"
    cq_path.write_text(
        "import cadquery as cq\nresult = cq.Workplane('XY').box(1,1,1)\n"
        "result.val().exportStep('output.step')\n"
    )

    ops_path = tmp_path / "stem_a.json"
    ops_path.write_text(json.dumps({"metadata": {}, "timeline": [], "entities": {}}))

    csv_path = tmp_path / "verified_parts.csv"
    pd.DataFrame(
        [
            {
                "stem": "stem_a",
                "raw_step_path": "data/raw.step",
                "ops_json_path": str(ops_path),
                "gen_step_path": "data/gen.step",
                "cq_code_path": str(cq_path),
                "iou": 1.0,
                "verified": True,
                "views_raw_dir": str(views_dir),
                "views_gen_dir": str(views_dir),
                "source": "run_test",
                "timestamp": "2026-01-01T00:00:00Z",
                "visual_verdict": "",
                "visual_reason": "",
                "complexity_class": "",
                "note": "",
            },
            {
                "stem": "stem_b_copy_gt",
                "raw_step_path": "data/raw.step",
                "ops_json_path": str(ops_path),
                "gen_step_path": "data/gen.step",
                "cq_code_path": str(cq_path),
                "iou": 1.0,
                "verified": True,
                "views_raw_dir": str(views_dir),
                "views_gen_dir": str(views_dir),
                "source": "run_test",
                "timestamp": "2026-01-01T00:00:00Z",
                "visual_verdict": "",
                "visual_reason": "",
                "complexity_class": "",
                "note": "copy_gt",
            },
        ]
    ).to_csv(csv_path, index=False)
    return tmp_path, csv_path


def test_build_img2cq_excludes_copy_gt(tmp_workspace):
    tmp_path, csv_path = tmp_workspace
    out = str(tmp_path / "sft_img2cq.jsonl")
    df = pd.read_csv(csv_path)
    written = assemble_sft.build_img2cq(df, out)
    assert written == 1  # only stem_a, not copy_gt


def test_build_img2cq_output_format(tmp_workspace):
    tmp_path, csv_path = tmp_workspace
    out = str(tmp_path / "sft_img2cq.jsonl")
    df = pd.read_csv(csv_path)
    assemble_sft.build_img2cq(df, out)
    with open(out) as f:
        rec = json.loads(f.readline())
    assert rec["task"] == "IMG2CQ"
    assert rec["id"] == "stem_a"
    msgs = rec["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert isinstance(msgs[1]["content"], list)
    assert len(msgs[1]["content"]) == 4  # front, right, top, iso
    assert msgs[2]["role"] == "assistant"
    assert "cadquery" in msgs[2]["content"]


def test_build_img2cq_strips_export_line(tmp_workspace):
    tmp_path, csv_path = tmp_workspace
    out = str(tmp_path / "sft_img2cq.jsonl")
    df = pd.read_csv(csv_path)
    assemble_sft.build_img2cq(df, out)
    with open(out) as f:
        rec = json.loads(f.readline())
    code = rec["messages"][2]["content"]
    assert "exportStep" not in code
    assert "output.step" not in code


def test_build_json2cq_excludes_copy_gt(tmp_workspace):
    tmp_path, csv_path = tmp_workspace
    out = str(tmp_path / "sft_json2cq.jsonl")
    df = pd.read_csv(csv_path)
    written = assemble_sft.build_json2cq(df, out)
    assert written == 1


def test_build_json2cq_output_format(tmp_workspace):
    tmp_path, csv_path = tmp_workspace
    out = str(tmp_path / "sft_json2cq.jsonl")
    df = pd.read_csv(csv_path)
    assemble_sft.build_json2cq(df, out)
    with open(out) as f:
        rec = json.loads(f.readline())
    assert rec["task"] == "JSON2CQ"
    msgs = rec["messages"]
    assert msgs[1]["role"] == "user"
    assert "metadata" in msgs[1]["content"]  # ops JSON content
    assert "cadquery" in msgs[2]["content"]


def test_build_img2cq_fallback_to_gen_views(tmp_workspace):
    """If raw views missing, falls back to gen_ prefix."""
    tmp_path, csv_path = tmp_workspace
    # Remove raw views
    views_dir = tmp_path / "views" / "stem_a"
    for v in ("front", "right", "top", "iso"):
        (views_dir / f"raw_{v}.png").unlink()

    df = pd.read_csv(csv_path)
    out = str(tmp_path / "sft_img2cq.jsonl")
    written = assemble_sft.build_img2cq(df, out)
    assert written == 1
    with open(out) as f:
        rec = json.loads(f.readline())
    paths = [c["path"] for c in rec["messages"][1]["content"]]
    assert all("gen_" in p for p in paths)


def test_build_img2cq_skips_missing_views(tmp_workspace):
    """Skips stem if neither raw nor gen views present."""
    tmp_path, csv_path = tmp_workspace
    views_dir = tmp_path / "views" / "stem_a"
    for v in ("front", "right", "top", "iso"):
        (views_dir / f"raw_{v}.png").unlink()
        (views_dir / f"gen_{v}.png").unlink()

    df = pd.read_csv(csv_path)
    out = str(tmp_path / "sft_img2cq.jsonl")
    written = assemble_sft.build_img2cq(df, out)
    assert written == 0
