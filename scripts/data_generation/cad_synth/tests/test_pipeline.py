"""Tests for pipeline modules — sampler, registry, reporter, config."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import yaml

from ..pipeline.registry import get_family, list_families
from ..pipeline.sampler import sample_family, sample_difficulty
from ..pipeline.reporter import build_report, write_report
from ..pipeline.builder import Op, Program, render_program_to_code


class TestRegistry:
    """Test family registry."""

    def test_list_families(self):
        """At least 2 families registered."""
        fams = list_families()
        assert len(fams) >= 2
        assert "mounting_plate" in fams
        assert "round_flange" in fams

    def test_get_family(self):
        """get_family returns correct instance."""
        f = get_family("mounting_plate")
        assert f.name == "mounting_plate"

    def test_get_unknown_raises(self):
        """Unknown family raises KeyError."""
        with pytest.raises(KeyError):
            get_family("nonexistent_family")


class TestSampler:
    """Test family/difficulty sampling."""

    def test_sample_family_distribution(self):
        """Sampled families roughly follow mix weights."""
        rng = np.random.default_rng(99)
        mix = {"mounting_plate": 0.7, "round_flange": 0.3}
        counts = {"mounting_plate": 0, "round_flange": 0}
        n = 1000
        for _ in range(n):
            f = sample_family(mix, rng)
            counts[f] += 1
        # 70% ± 5%
        assert 0.6 < counts["mounting_plate"] / n < 0.8

    def test_sample_difficulty_distribution(self):
        """Sampled difficulties roughly follow mix weights."""
        rng = np.random.default_rng(99)
        mix = {"easy": 0.5, "medium": 0.3, "hard": 0.2}
        counts = {"easy": 0, "medium": 0, "hard": 0}
        n = 1000
        for _ in range(n):
            d = sample_difficulty(mix, rng)
            counts[d] += 1
        assert 0.4 < counts["easy"] / n < 0.6


class TestReporter:
    """Test report generation."""

    def test_build_report(self):
        """build_report produces correct summary."""
        results = [
            {
                "status": "accepted",
                "family": "mounting_plate",
                "difficulty": "easy",
                "ops_used": ["box"],
                "feature_tags": {"has_hole": False},
                "reject_stage": "",
                "reject_reason": "",
            },
            {
                "status": "rejected",
                "family": "round_flange",
                "difficulty": "hard",
                "ops_used": [],
                "feature_tags": {},
                "reject_stage": "build_failed",
                "reject_reason": "some error",
            },
        ]
        report = build_report(results)
        assert report["requested"] == 2
        assert report["accepted"] == 1
        assert report["rejected"] == 1
        assert "build_failed" in report["reject_stages"]

    def test_write_report(self):
        """write_report writes valid JSON."""
        report = {"accepted": 10, "rejected": 2}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "report.json"
            write_report(report, p)
            loaded = json.loads(p.read_text())
            assert loaded["accepted"] == 10


class TestBuilder:
    """Test Op/Program code rendering."""

    def test_render_simple_program(self):
        """render_program_to_code produces valid Python."""
        prog = Program(
            family="test",
            difficulty="easy",
            params={"length": 50, "width": 30, "height": 10},
            ops=[Op("box", {"length": 50, "width": 30, "height": 10})],
            feature_tags={},
        )
        code = render_program_to_code(prog)
        assert "import cadquery" in code
        assert ".box(50, 30, 10)" in code
        compile(code, "<test>", "exec")

    def test_render_hole_program(self):
        """Program with hole renders correct code."""
        prog = Program(
            family="test",
            difficulty="medium",
            params={},
            ops=[
                Op("box", {"length": 50, "width": 30, "height": 10}),
                Op("faces", {"selector": ">Z"}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": 5}),
            ],
            feature_tags={"has_hole": True},
        )
        code = render_program_to_code(prog)
        assert ".hole(5)" in code
        compile(code, "<test>", "exec")


class TestConfig:
    """Test config loading."""

    def test_smoke_config_exists(self):
        """smoke.yaml exists and is valid."""
        cfg_path = Path(__file__).parent.parent / "configs" / "smoke.yaml"
        assert cfg_path.exists()
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        assert cfg["num_samples"] == 100
        assert "family_mix" in cfg
        assert "difficulty_mix" in cfg
