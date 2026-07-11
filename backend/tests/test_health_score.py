"""
Unit tests for analysis/health_score.py
=========================================

Tests verify:
 1. Hand-computed weighted arithmetic (exact values).
 2. Perfect model (all zeros) → score 100.0.
 3. Clamp: all-max penalties → score exactly 0.0 (weights sum to 1.0).
 4. Clamp: super-max penalties (> 100) → score never goes negative.
 5. Grade mapping boundaries.
 6. Partial inputs (None) → graceful degradation with 0 penalties.
"""

import pytest
from analysis.health_score import compute_health_score, _compute_final_score


# ---------------------------------------------------------------------------
# 1. Hand-computed arithmetic using _compute_final_score directly
#    (avoids building full analysis dicts; tests the formula in isolation)
# ---------------------------------------------------------------------------

def test_hand_computed_example_1():
    """
    leakage=50, calibration=20, overfit=10, fairness=0, data_quality=30
    Expected:
      100 - (50×0.30) - (20×0.15) - (10×0.20) - (0×0.20) - (30×0.15)
      = 100 - 15 - 3 - 2 - 0 - 4.5
      = 75.5
    """
    score = _compute_final_score(
        leakage_p=50.0,
        calibration_p=20.0,
        overfit_p=10.0,
        fairness_p=0.0,
        dq_p=30.0,
    )
    assert score == 75.5


def test_hand_computed_example_2_perfect():
    """
    All penalties are 0 → score must be exactly 100.0.
    """
    score = _compute_final_score(
        leakage_p=0.0,
        calibration_p=0.0,
        overfit_p=0.0,
        fairness_p=0.0,
        dq_p=0.0,
    )
    assert score == 100.0


def test_hand_computed_example_3_all_max_clamp():
    """
    All penalties at 100 (weights sum to exactly 1.0):
      100 - (100×0.30) - (100×0.15) - (100×0.20) - (100×0.20) - (100×0.15)
      = 100 - 30 - 15 - 20 - 20 - 15
      = 0.0
    Result must be exactly 0.0, not negative.
    """
    score = _compute_final_score(
        leakage_p=100.0,
        calibration_p=100.0,
        overfit_p=100.0,
        fairness_p=100.0,
        dq_p=100.0,
    )
    assert score == 0.0


def test_clamp_prevents_negative_with_super_max_inputs():
    """
    If somehow a penalty exceeds 100 (e.g. normalisation edge case),
    the final score must still be clamped to 0.0, never negative.
    """
    score = _compute_final_score(
        leakage_p=200.0,
        calibration_p=200.0,
        overfit_p=200.0,
        fairness_p=200.0,
        dq_p=200.0,
    )
    assert score == 0.0
    assert score >= 0.0


def test_clamp_prevents_above_100():
    """
    Negative penalties must be clamped to 100.0, never above.
    """
    score = _compute_final_score(
        leakage_p=-50.0,
        calibration_p=-50.0,
        overfit_p=-50.0,
        fairness_p=-50.0,
        dq_p=-50.0,
    )
    assert score == 100.0


# ---------------------------------------------------------------------------
# 2. compute_health_score end-to-end with real analysis result structures
# ---------------------------------------------------------------------------

def test_full_pipeline_no_results():
    """
    Passing no results at all (all None) → score 100.0, grade A.
    Rationale: absent data means no detected risk, not maximum risk.
    """
    result = compute_health_score()
    assert result["score"] == 100.0
    assert result["grade"] == "A"
    assert result["components"]["leakage"]["penalty"] == 0.0
    assert result["components"]["fairness"]["penalty"] == 0.0


def test_leakage_only_high_risk():
    """
    Single high-risk leakage feature (risk_score=80) with no other results.
    leakage_penalty = 80, weighted = 80×0.30 = 24
    Expected score = 100 - 24 = 76.0 → grade B
    """
    leakage_results = [{"feature_name": "bad_feature", "risk_score": 80.0}]
    result = compute_health_score(leakage_results=leakage_results)
    assert result["score"] == 76.0
    assert result["grade"] == "B"


def test_fairness_zero_when_no_protected_attribute():
    """
    If no protected attribute or no fairness metrics exist, the fairness penalty must be 0.
    """
    result_without = compute_health_score(fairness_results=None)
    assert result_without["components"]["fairness"]["penalty"] == 0.0
    
    result_unsupported = compute_health_score(fairness_results={"supported": False, "message": "unsupported"})
    assert result_unsupported["components"]["fairness"]["penalty"] == 0.0


def test_fairness_with_protected_attribute():
    """
    Assert that a non-zero fairness penalty correctly affects the health score when provided.
    DP difference of 0.4 and EO difference of 0.3.
    Max difference = 0.4 -> penalty = 40.0.
    Weighted penalty = 40 * 0.20 = 8.0.
    If no other penalties, score = 100 - 8.0 = 92.0.
    """
    fairness_results = {
        "supported": True,
        "demographic_parity_difference": 0.4,
        "equalized_odds_difference": 0.3
    }
    result = compute_health_score(fairness_results=fairness_results)
    assert result["components"]["fairness"]["penalty"] == 40.0
    assert result["components"]["fairness"]["weighted_penalty"] == 8.0
    assert result["score"] == 92.0
    assert result["grade"] == "A"


def test_grade_boundaries():
    """Test grade letter assignment at boundary values."""
    assert _compute_final_score(15.0, 0, 0, 0, 0) == 95.5    # 100 - 4.5 = 95.5 → A
    # B boundary: score 70-84
    score_b = _compute_final_score(50.0, 20.0, 10.0, 0.0, 30.0)  # = 75.5 → B
    assert score_b == 75.5

    from analysis.health_score import _score_to_grade
    assert _score_to_grade(100.0) == "A"
    assert _score_to_grade(85.0)  == "A"
    assert _score_to_grade(84.9)  == "B"
    assert _score_to_grade(70.0)  == "B"
    assert _score_to_grade(69.9)  == "C"
    assert _score_to_grade(55.0)  == "C"
    assert _score_to_grade(54.9)  == "D"
    assert _score_to_grade(40.0)  == "D"
    assert _score_to_grade(39.9)  == "F"
    assert _score_to_grade(0.0)   == "F"


def test_result_structure_keys():
    """compute_health_score must always return the expected top-level keys."""
    result = compute_health_score()
    assert "score" in result
    assert "grade" in result
    assert "components" in result
    for key in ("leakage", "calibration", "overfitting", "fairness", "data_quality"):
        assert key in result["components"]
        comp = result["components"][key]
        assert "penalty" in comp
        assert "weight" in comp
        assert "weighted_penalty" in comp
