"""
Health Score Computation Engine
================================

Weighting Rationale
-------------------
The composite health score captures five orthogonal risk dimensions, each
weighted to reflect the relative cost of the failure mode in a real ML
deployment:

  Leakage Risk (30%) — highest weight
      Target leakage fundamentally invalidates the model's evaluation metrics.
      A leaky model's reported accuracy is meaningless because it trained on
      information unavailable at real prediction time. No post-hoc fix can
      repair this without full retraining.

  Overfit Gap (20%)
      Overfitting means the model's measured performance won't generalise to
      unseen data, directly understating real-world error rates. High-stakes
      deployments are misled into thinking the model is more reliable than it is.

  Fairness Violation (20%) — Phase 5 placeholder
      Fairness violations create legal, ethical, and reputational risk. A
      model that discriminates is unsafe to deploy even if technically sound
      on aggregate metrics. Weight reserved and structurally present; currently
      contributes 0 penalty until Phase 5 implements fairness analysis.

  Data Quality (15%)
      Data issues are often detectable and fixable pre-training. Their impact
      is real but bounded: missing values, duplicates, and outliers degrade
      training signal but don't structurally invalidate the model's design.

  Calibration Error (15%) — lowest weight
      Miscalibration can be corrected post-hoc with a thin isotonic regression
      or Platt scaling layer without full retraining. It does not invalidate
      the model's rank ordering and is therefore the least critical failure mode.

Formula
-------
  Health Score = 100
    − (leakage_penalty    × 0.30)
    − (calibration_penalty × 0.15)
    − (overfit_penalty    × 0.20)
    − (fairness_penalty   × 0.20)   ← always 0 until Phase 5
    − (data_quality_penalty × 0.15)

All sub-metrics are normalised to [0, 100] before weighting.
The final score is clamped to [0.0, 100.0].

Grade mapping
-------------
  A  85–100  Model is healthy and deployment-ready.
  B  70–84   Minor issues; deployable with monitoring.
  C  55–69   Moderate risk; review before deployment.
  D  40–54   Significant risk; remediation required.
  F   0–39   Severe defects; do not deploy.
"""

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Internal normalisation helpers
# ---------------------------------------------------------------------------

def _normalize(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """
    Map `value` from [min_val, max_val] into [0, 100].
    Clamps the result so it never leaves [0, 100] even with out-of-range input.
    """
    if max_val <= min_val:
        return 0.0
    return max(0.0, min(100.0, (value - min_val) / (max_val - min_val) * 100.0))


def _compute_leakage_penalty(
    leakage_results: Optional[List[Dict[str, Any]]],
) -> float:
    """
    0–100 penalty derived from leakage analysis.

    Uses the *maximum* risk score across all features because a single leaky
    feature can invalidate the entire model — the worst-case feature is what
    matters for deployment safety.

    Returns 0 if leakage results are absent (not yet analysed).
    """
    if not leakage_results:
        return 0.0
    max_risk = max(r.get("risk_score", 0.0) for r in leakage_results)
    return _normalize(max_risk, 0.0, 100.0)


def _compute_calibration_penalty(
    calibration_results: Optional[Dict[str, Any]],
) -> float:
    """
    0–100 penalty derived from calibration analysis.

    Uses the Brier score: 0.0 is perfect, ~0.25 is the no-skill baseline for
    balanced binary classification. Scaled linearly so 0.25 → 100 penalty.

    Returns 0 if calibration is unsupported or not yet analysed.
    """
    if not calibration_results or not calibration_results.get("supported"):
        return 0.0
    brier = calibration_results.get("brier_score", 0.0)
    return _normalize(brier, 0.0, 0.25)


def _compute_overfit_penalty(
    overfitting_results: Optional[Dict[str, Any]],
) -> float:
    """
    0–100 penalty derived from overfitting analysis.

    Uses the performance gap (train_score − val_score at maximum training size).
    A gap of 0.50 (50 percentage points) is treated as the worst case → 100 penalty.

    Returns 0 if overfitting is unsupported or not yet analysed.
    """
    if not overfitting_results or not overfitting_results.get("supported"):
        return 0.0
    gap = overfitting_results.get("performance_gap", 0.0)
    return _normalize(gap, 0.0, 0.50)


def _compute_data_quality_penalty(
    data_quality_results: Optional[Dict[str, Any]],
) -> float:
    """
    0–100 penalty derived from data quality analysis.

    Combines three signals into a simple average:
      • Average missing-value rate across columns (%)
      • Duplicate row rate (%)
      • Average outlier rate across numerical columns (%)

    Returns 0 if data quality results are absent.
    """
    if not data_quality_results:
        return 0.0

    total_rows = data_quality_results.get("total_rows", 0)
    if total_rows == 0:
        return 0.0

    missing_data = data_quality_results.get("missing_data", {})
    avg_missing_pct = (
        sum(v.get("percentage", 0) for v in missing_data.values()) / len(missing_data)
        if missing_data else 0.0
    )

    duplicate_pct = data_quality_results.get("duplicates", {}).get("percentage", 0.0)

    outlier_data = data_quality_results.get("outliers", {})
    avg_outlier_pct = (
        sum(v.get("percentage", 0) for v in outlier_data.values()) / len(outlier_data)
        if outlier_data else 0.0
    )

    composite = (avg_missing_pct + duplicate_pct + avg_outlier_pct) / 3.0
    return _normalize(composite, 0.0, 100.0)


def _compute_fairness_penalty(
    fairness_results: Optional[Dict[str, Any]],
) -> float:
    """
    0–100 fairness penalty.
    Calculated as max(demographic_parity_difference, equalized_odds_difference) * 100.
    """
    if not fairness_results or not fairness_results.get("supported", True):
        return 0.0
    dp_diff = fairness_results.get("demographic_parity_difference", 0.0)
    eo_diff = fairness_results.get("equalized_odds_difference", 0.0)
    return max(0.0, min(100.0, max(dp_diff, eo_diff) * 100.0))


def _compute_final_score(
    leakage_p: float,
    calibration_p: float,
    overfit_p: float,
    fairness_p: float,
    dq_p: float,
) -> float:
    """
    Apply weights to pre-normalised [0, 100] penalty values and return the
    clamped final score.

    Exposed as a public-enough helper so unit tests can verify the arithmetic
    directly without constructing full analysis result structures.
    """
    raw = (
        100.0
        - (leakage_p     * 0.30)
        - (calibration_p * 0.15)
        - (overfit_p     * 0.20)
        - (fairness_p    * 0.20)
        - (dq_p          * 0.15)
    )
    return round(max(0.0, min(100.0, raw)), 2)


def _score_to_grade(score: float) -> str:
    """Map a numeric health score to a deployment-readiness letter grade."""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_health_score(
    leakage_results: Optional[List[Dict[str, Any]]] = None,
    calibration_results: Optional[Dict[str, Any]] = None,
    overfitting_results: Optional[Dict[str, Any]] = None,
    data_quality_results: Optional[Dict[str, Any]] = None,
    fairness_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute the ModelDoctor composite Health Score for a completed audit job.

    Each argument corresponds to the output of the matching analysis module.
    Pass ``None`` for any module that has not yet been run — it contributes
    0 penalty (interpreted as "no detected risk", not "perfect").

    Returns a dict with:
      score (float)   Final clamped score in [0.0, 100.0].
      grade (str)     Letter grade A/B/C/D/F.
      components (dict) Per-module raw penalties, weights, and weighted penalties.
    """
    leakage_p     = _compute_leakage_penalty(leakage_results)
    calibration_p = _compute_calibration_penalty(calibration_results)
    overfit_p     = _compute_overfit_penalty(overfitting_results)
    dq_p          = _compute_data_quality_penalty(data_quality_results)
    fairness_p    = _compute_fairness_penalty(fairness_results)

    final_score = _compute_final_score(
        leakage_p, calibration_p, overfit_p, fairness_p, dq_p
    )

    return {
        "score": final_score,
        "grade": _score_to_grade(final_score),
        "components": {
            "leakage": {
                "penalty": round(leakage_p, 2),
                "weight": 0.30,
                "weighted_penalty": round(leakage_p * 0.30, 2),
            },
            "calibration": {
                "penalty": round(calibration_p, 2),
                "weight": 0.15,
                "weighted_penalty": round(calibration_p * 0.15, 2),
            },
            "overfitting": {
                "penalty": round(overfit_p, 2),
                "weight": 0.20,
                "weighted_penalty": round(overfit_p * 0.20, 2),
            },
            "fairness": {
                "penalty": round(fairness_p, 2),
                "weight": 0.20,
                "weighted_penalty": round(fairness_p * 0.20, 2),
                "note": "Demographic parity and equalised odds violation penalty.",
            },
            "data_quality": {
                "penalty": round(dq_p, 2),
                "weight": 0.15,
                "weighted_penalty": round(dq_p * 0.15, 2),
            },
        },
    }
