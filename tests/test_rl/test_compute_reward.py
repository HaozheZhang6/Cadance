"""Tests for scripts/rl/compute_reward.py."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.rl.compute_reward import compute_reward, compute_rewards_batch


class TestComputeReward:
    def test_missing_gt_step_returns_zero(self):
        reward, reason = compute_reward("import cadquery as cq", "/nonexistent/part.step")
        assert reward == 0.0
        assert "gt_step not found" in reason

    def test_execute_failure_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            with patch(
                "scripts.rl.compute_reward._execute_cadquery_script",
                return_value=(False, "syntax error"),
            ):
                reward, reason = compute_reward("bad code", gt)
        assert reward == 0.0
        assert "execute_failed" in reason

    def test_iou_error_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            with patch(
                "scripts.rl.compute_reward._execute_cadquery_script",
                return_value=(True, None),
            ), patch(
                "scripts.rl.compute_reward._compute_iou",
                return_value=(0.0, "some occt error"),
            ):
                reward, reason = compute_reward("code", gt)
        assert reward == 0.0
        assert "iou_error" in reason

    def test_perfect_iou_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            with patch(
                "scripts.rl.compute_reward._execute_cadquery_script",
                return_value=(True, None),
            ), patch(
                "scripts.rl.compute_reward._compute_iou",
                return_value=(1.0, None),
            ):
                reward, reason = compute_reward("code", gt)
        assert reward == 1.0
        assert "iou=1.0000" in reason

    def test_partial_iou_returned_as_float(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            with patch(
                "scripts.rl.compute_reward._execute_cadquery_script",
                return_value=(True, None),
            ), patch(
                "scripts.rl.compute_reward._compute_iou",
                return_value=(0.73, None),
            ):
                reward, reason = compute_reward("code", gt)
        assert abs(reward - 0.73) < 1e-6
        assert isinstance(reward, float)

    def test_reward_clamped_to_zero_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            with patch(
                "scripts.rl.compute_reward._execute_cadquery_script",
                return_value=(True, None),
            ), patch(
                "scripts.rl.compute_reward._compute_iou",
                return_value=(0.0, None),
            ):
                reward, _ = compute_reward("code", gt)
        assert 0.0 <= reward <= 1.0


class TestComputeRewardsBatch:
    def test_batch_returns_same_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            items = [{"code": "x", "gt_step_path": str(gt)}] * 4
            with patch(
                "scripts.rl.compute_reward._execute_cadquery_script",
                return_value=(False, "err"),
            ):
                results = compute_rewards_batch(items)
        assert len(results) == 4
        assert all(r[0] == 0.0 for r in results)

    def test_batch_mixed_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            gt = Path(tmp) / "fake.step"
            gt.write_text("dummy")
            side_effects = [(True, None), (False, "err"), (True, None)]
            iou_effects = [(0.9, None), (0.5, None)]  # only 2 iou calls (item 1 fails early)

            call_count = [0]

            def fake_execute(code, path, timeout_sec=60):
                i = call_count[0]
                call_count[0] += 1
                return side_effects[i]

            iou_count = [0]

            def fake_iou(gt_p, gen_p):
                i = iou_count[0]
                iou_count[0] += 1
                return iou_effects[i]

            items = [{"code": "c", "gt_step_path": str(gt)} for _ in range(3)]
            with patch("scripts.rl.compute_reward._execute_cadquery_script", fake_execute), \
                 patch("scripts.rl.compute_reward._compute_iou", fake_iou):
                results = compute_rewards_batch(items)

        assert results[0][0] == pytest.approx(0.9)
        assert results[1][0] == 0.0
        assert results[2][0] == pytest.approx(0.5)
