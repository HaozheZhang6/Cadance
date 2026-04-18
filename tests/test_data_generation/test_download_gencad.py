"""Tests for download_gencad.py (offline, no HF network calls)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.data_generation.download_gencad import (
    SYSTEM_PROMPT,
    _SPLIT_MAP,
    download_and_convert,
)


def _make_fake_image():
    """Return a tiny PIL image without requiring a real image."""
    try:
        from PIL import Image

        img = Image.new("RGB", (8, 8), color=(128, 0, 255))
        return img
    except ImportError:
        return None


def _fake_dataset(n: int = 5):
    """Build a minimal fake HF dataset dict."""
    img = _make_fake_image()
    rows = [
        {
            "deepcad_id": f"abc{i:010d}",
            "cadquery": f"import cadquery as cq\nresult = cq.Workplane().box({i+1}, 1, 1)",
            "image": img,
            "split": "train",
            "token_count": 20,
        }
        for i in range(n)
    ]

    class FakeSplit:
        def __init__(self, data):
            self._data = data

        def __len__(self):
            return len(self._data)

        def __iter__(self):
            return iter(self._data)

    return {"train": FakeSplit(rows)}


_hf_datasets = pytest.importorskip("datasets", reason="HF datasets not installed")


@pytest.mark.skipif(_make_fake_image() is None, reason="Pillow not available")
class TestDownloadAndConvert:
    def test_writes_jsonl(self):
        """JSONL file is created and contains expected number of rows."""
        hf_datasets = pytest.importorskip("datasets")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            fake_ds = _fake_dataset(3)

            import datasets as hf_datasets  # noqa: F811
            import scripts.data_generation.download_gencad as gencad_mod

            real_load = hf_datasets.load_dataset
            try:
                hf_datasets.load_dataset = lambda *a, **kw: fake_ds
                result = gencad_mod.download_and_convert(out_dir=out, limit=3)
            finally:
                hf_datasets.load_dataset = real_load

            jsonl = out / "sft_gencad_img2cq.jsonl"
            assert jsonl.exists()
            rows = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
            assert len(rows) == 3

    def test_output_schema(self):
        """Each written row must have the expected keys and message structure."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            fake_ds = _fake_dataset(2)

            import datasets as hf_datasets
            import scripts.data_generation.download_gencad as gencad_mod

            real_load = hf_datasets.load_dataset
            try:
                hf_datasets.load_dataset = lambda *a, **kw: fake_ds
                gencad_mod.download_and_convert(out_dir=out, limit=2)
            finally:
                hf_datasets.load_dataset = real_load

            rows = [
                json.loads(l)
                for l in (out / "sft_gencad_img2cq.jsonl").read_text().splitlines()
                if l.strip()
            ]
            row = rows[0]
            assert row["task"] == "IMG2CQ"
            assert row["source"] == "gencad"
            assert row["split"] == "train"
            assert "id" in row
            msgs = row["messages"]
            assert msgs[0]["role"] == "system"
            assert msgs[0]["content"] == SYSTEM_PROMPT
            assert msgs[1]["role"] == "user"
            assert isinstance(msgs[1]["content"], list)
            assert msgs[1]["content"][0]["type"] == "image"
            assert msgs[2]["role"] == "assistant"
            assert "cadquery" in msgs[2]["content"].lower() or "cq" in msgs[2]["content"]

    def test_summary_counts(self):
        """Summary dict reports correct written/error/split counts."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            fake_ds = _fake_dataset(6)

            import datasets as hf_datasets
            import scripts.data_generation.download_gencad as gencad_mod

            real_load = hf_datasets.load_dataset
            try:
                hf_datasets.load_dataset = lambda *a, **kw: fake_ds
                result = gencad_mod.download_and_convert(out_dir=out, limit=6)
            finally:
                hf_datasets.load_dataset = real_load

            assert result["written"] == 6
            assert result["error"] == 0
            assert result["splits"]["train"] == 6

    def test_limit_respected(self):
        """--limit caps rows written."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            fake_ds = _fake_dataset(10)

            import datasets as hf_datasets
            import scripts.data_generation.download_gencad as gencad_mod

            real_load = hf_datasets.load_dataset
            try:
                hf_datasets.load_dataset = lambda *a, **kw: fake_ds
                result = gencad_mod.download_and_convert(out_dir=out, limit=3)
            finally:
                hf_datasets.load_dataset = real_load

            assert result["written"] == 3

    def test_images_saved(self):
        """Image files are written under images/<split>/."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            fake_ds = _fake_dataset(2)

            import datasets as hf_datasets
            import scripts.data_generation.download_gencad as gencad_mod

            real_load = hf_datasets.load_dataset
            try:
                hf_datasets.load_dataset = lambda *a, **kw: fake_ds
                gencad_mod.download_and_convert(out_dir=out, limit=2)
            finally:
                hf_datasets.load_dataset = real_load

            imgs = list((out / "images" / "train").glob("*.jpg"))
            assert len(imgs) == 2

    def test_split_map_covers_all_hf_splits(self):
        assert "train" in _SPLIT_MAP
        assert "validation" in _SPLIT_MAP
        assert "test" in _SPLIT_MAP
        assert _SPLIT_MAP["validation"] == "val"
