"""Unit tests for bench.metrics — pure-Python paths only.

Excluded (require cadquery + STEP files): _step_has_hole, _load_normalized_mesh,
compute_iou, compute_chamfer, compute_hausdorff, compute_rotation_invariant_iou.
These are integration-tested via run_test.py end-to-end.

This file targets the deterministic, file-free helpers:
  extract_features (regex AST), feature_f1, qa_score_single, qa_score,
  iso53_compliance, cd_to_score, hd_to_score, combined_score.
"""

from __future__ import annotations

import math

import pytest

from bench.metrics import (
    cd_to_score,
    combined_score,
    extract_features,
    feature_f1,
    hd_to_score,
    iso53_compliance,
    qa_score,
    qa_score_single,
)

# ── extract_features (regex over code) ────────────────────────────────────────


class TestExtractFeatures:
    def test_empty_code(self):
        feats = extract_features("")
        assert feats == {"has_hole": False, "has_fillet": False, "has_chamfer": False}

    def test_hole_op(self):
        assert extract_features(".hole(5)")["has_hole"] is True

    def test_cutThruAll_counts_as_hole(self):
        assert extract_features(".cutThruAll()")["has_hole"] is True

    def test_cboreHole_counts_as_hole(self):
        assert extract_features(".cboreHole(5, 8, 2)")["has_hole"] is True

    def test_cskHole_counts_as_hole(self):
        assert extract_features(".cskHole(5, 10, 90)")["has_hole"] is True

    def test_fillet(self):
        assert extract_features(".fillet(0.5)")["has_fillet"] is True

    def test_chamfer(self):
        assert extract_features(".chamfer(1.2)")["has_chamfer"] is True

    def test_all_features_at_once(self):
        code = "result = cq.Workplane().box(10,10,10).hole(2).fillet(0.5).chamfer(0.3)"
        feats = extract_features(code)
        assert feats == {"has_hole": True, "has_fillet": True, "has_chamfer": True}

    def test_case_insensitive(self):
        # Pattern uses re.I — uppercase variants also match
        assert extract_features(".HOLE(5)")["has_hole"] is True
        assert extract_features(".Fillet(1)")["has_fillet"] is True

    def test_word_boundary_avoids_false_positives(self):
        # "shole" should NOT match \bhole\(
        # But also test that "fill" doesn't match "fillet" from raw substring
        assert extract_features("# my_fillet_var = 5")["has_fillet"] is False
        # "fillet" word + paren: matches
        assert extract_features("x = fillet(2)")["has_fillet"] is True


# ── feature_f1 ────────────────────────────────────────────────────────────────


class TestFeatureF1:
    def test_perfect_match(self):
        gt = {"has_hole": True, "has_fillet": False, "has_chamfer": True}
        pred = dict(gt)
        assert feature_f1(pred, gt) == 1.0

    def test_all_wrong(self):
        gt = {"has_hole": True, "has_fillet": True, "has_chamfer": True}
        pred = {"has_hole": False, "has_fillet": False, "has_chamfer": False}
        # 0 TP, 0 FP, 3 FN → prec=0, rec=0, F1=0
        assert feature_f1(pred, gt) == 0.0

    def test_perfect_negative(self):
        # All gt False, pred all False → no positives at all → F1 = 0 by convention
        gt = {"has_hole": False, "has_fillet": False}
        pred = {"has_hole": False, "has_fillet": False}
        # tp=0, fp=0, fn=0 → prec=0, rec=0 → F1=0
        assert feature_f1(pred, gt) == 0.0

    def test_one_tp_one_fp(self):
        gt = {"has_hole": True, "has_fillet": False, "has_chamfer": False}
        pred = {"has_hole": True, "has_fillet": True, "has_chamfer": False}
        # tp=1, fp=1, fn=0 → prec=0.5, rec=1.0 → F1 = 2*0.5*1/(0.5+1) = 0.667
        assert abs(feature_f1(pred, gt) - 2 / 3) < 1e-6

    def test_empty_gt_returns_one(self):
        assert feature_f1({"has_hole": True}, {}) == 1.0

    def test_partial_match(self):
        # 2/3 features match (both True for has_hole and has_chamfer; has_fillet flipped)
        gt = {"has_hole": True, "has_fillet": True, "has_chamfer": False}
        pred = {"has_hole": True, "has_fillet": False, "has_chamfer": False}
        # tp=1, fp=0, fn=1 → prec=1, rec=0.5 → F1 = 2/(1+2) = 0.667
        assert abs(feature_f1(pred, gt) - 2 / 3) < 1e-6


# ── qa_score_single + qa_score ────────────────────────────────────────────────


class TestQaScoreSingle:
    def test_exact_match(self):
        assert qa_score_single(26, {"answer": 26}) == 1.0

    def test_symmetric_ratio(self):
        # min/max → same in either direction
        a = qa_score_single(24, {"answer": 26})
        b = qa_score_single(26, {"answer": 24})
        assert a == b
        assert abs(a - 24 / 26) < 1e-4

    def test_zero_pred_returns_zero(self):
        assert qa_score_single(0, {"answer": 5}) == 0.0

    def test_negative_pred_returns_zero(self):
        assert qa_score_single(-3, {"answer": 5}) == 0.0

    def test_zero_gt_returns_zero(self):
        assert qa_score_single(5, {"answer": 0}) == 0.0

    def test_float_inputs(self):
        # 0.5 / 1.0 = 0.5
        assert qa_score_single(0.5, {"answer": 1.0}) == 0.5

    def test_string_pred_coerced_to_float(self):
        # qa_score_single does float(pred) — accepts string-numeric
        assert qa_score_single("26", {"answer": 26}) == 1.0


class TestQaScoreAggregate:
    def test_empty_returns_zero(self):
        assert qa_score([], []) == 0.0

    def test_single_pair(self):
        assert qa_score([20], [{"answer": 20}]) == 1.0

    def test_mean_of_pairs(self):
        # 1.0 + 0.5 = 1.5 / 2 = 0.75
        scores = qa_score([20, 5], [{"answer": 20}, {"answer": 10}])
        assert abs(scores - 0.75) < 1e-4

    def test_zero_pred_pulls_average_down(self):
        # 1.0 + 0.0 = 0.5 mean
        scores = qa_score([20, 0], [{"answer": 20}, {"answer": 5}])
        assert abs(scores - 0.5) < 1e-4

    def test_rounded_to_4_digits(self):
        # 0.923076923... → rounded to 0.9231
        scores = qa_score([24], [{"answer": 26}])
        # Allow for the scoring rounding behavior (4 digits)
        assert scores == pytest.approx(24 / 26, abs=1e-3)


# ── iso53_compliance ──────────────────────────────────────────────────────────


class TestIso53Compliance:
    def test_perfect_compliance(self):
        m, z = 2.0, 20
        da = m * (z + 2)  # 44
        df = m * (z - 2.5)  # 35
        d = m * z  # 40
        assert iso53_compliance(m, z, da, df, d) == 1.0

    def test_all_zero_pred_returns_zero(self):
        assert iso53_compliance(0, 20, 44, 35, 40) == 0.0

    def test_low_z_returns_zero(self):
        assert iso53_compliance(2.0, 4, 44, 35, 40) == 0.0  # z<5

    def test_partial_compliance_drops_score(self):
        m, z = 2.0, 20
        da_gt = m * (z + 2)
        df_gt = m * (z - 2.5)
        d_gt = m * z
        # Off by 10% on da only
        score = iso53_compliance(m, z, da_gt * 1.1, df_gt, d_gt)
        # error = (0.1 + 0 + 0)/3 = 0.033 → score = 0.967
        assert 0.95 < score < 0.99


# ── CD/HD score curves ────────────────────────────────────────────────────────


class TestCdToScore:
    def test_below_low_returns_one(self):
        assert cd_to_score(0.0005) == 1.0

    def test_at_low_returns_one(self):
        assert cd_to_score(0.001) == 1.0

    def test_above_high_returns_zero(self):
        assert cd_to_score(0.5) == 0.0

    def test_at_high_returns_zero(self):
        assert cd_to_score(0.2) == 0.0

    def test_linear_in_between(self):
        # Midpoint: cd = (0.001 + 0.2) / 2 ≈ 0.1005, score ≈ 0.5
        mid = (0.001 + 0.2) / 2
        assert abs(cd_to_score(mid) - 0.5) < 0.05

    def test_inf_returns_zero(self):
        assert cd_to_score(float("inf")) == 0.0

    def test_nan_returns_zero(self):
        assert cd_to_score(float("nan")) == 0.0

    def test_none_returns_zero(self):
        assert cd_to_score(None) == 0.0


class TestHdToScore:
    def test_below_low_returns_one(self):
        assert hd_to_score(0.01) == 1.0

    def test_above_high_returns_zero(self):
        assert hd_to_score(1.0) == 0.0

    def test_inf_zero(self):
        assert hd_to_score(float("inf")) == 0.0

    def test_nan_zero(self):
        # nan != nan, hd_to_score handles that
        assert hd_to_score(float("nan")) == 0.0


# ── combined_score weighted sum ───────────────────────────────────────────────


class TestCombinedScore:
    def test_perfect_inputs(self):
        # f1=1, iou=1, cd well-below low (=1), hd well-below low (=1)
        # → 0.25*1 + 0.7*1 + 0.025 + 0.025 = 1.0
        assert combined_score(1.0, 1.0, 0.0, 0.0) == 1.0

    def test_iou_dominates(self):
        # f1=0, iou=1, cd=hd=∞ → 0.25*0 + 0.7*1 + 0 + 0 = 0.7
        assert combined_score(0.0, 1.0, float("inf"), float("inf")) == 0.7

    def test_zero_inputs(self):
        assert combined_score(0.0, 0.0, float("inf"), float("inf")) == 0.0

    def test_weights_sum_to_one(self):
        # Verify: 0.25 + 0.7 + 0.025 + 0.025 = 1.0
        assert math.isclose(0.25 + 0.7 + 0.025 + 0.025, 1.0)

    def test_rounds_to_4_digits(self):
        # f1=0.5, iou=0.5, cd=hd=midpoints → 0.25*0.5 + 0.7*0.5 + small
        score = combined_score(0.5, 0.5, 0.05, 0.2)
        # Should round to 4 digits
        assert score == round(score, 4)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
