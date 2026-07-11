"""
Tests for analysis/report_generator.py
=========================================

Verifies:
 1. Partial/missing results → "Not Yet Analyzed" text, no exception raised.
 2. Valid PDF bytes are returned even with partial data.
 3. Full data → HTML contains health score and module headers.
 4. LLM summary fallback (no API key) returns non-empty string.
"""

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Minimal mock job objects for testing without Django DB access
# ---------------------------------------------------------------------------

class MockLeakageResult:
    def __init__(self, feature_name, risk_score, drop_pct, known_flag):
        self.feature_name = feature_name
        self.risk_score = risk_score
        self.drop_pct = drop_pct
        self.known_flag = known_flag


class MockJob:
    """Mimics the interface expected by generate_html_report / generate_pdf_report."""

    def __init__(self, results=None, leakage_results=None, target_column="target", job_id="test-id-123"):
        self.id = job_id
        self.target_column = target_column
        self.results = results
        # Plain list (not a queryset) to bypass .values() call
        self._leakage_list = leakage_results or []

    @property
    def leakage_results(self):
        """Return a list-like object that doesn't have .values() so the generator falls back."""
        return self._leakage_list


# ---------------------------------------------------------------------------
# 1. Partial / missing results — must not raise, must contain "Not Yet Analyzed"
# ---------------------------------------------------------------------------

def test_html_report_partial_results_no_exception():
    """
    generate_html_report with empty results and no leakage data must:
    - Not raise any exception
    - Return a non-empty HTML string
    - Contain "Not Yet Analyzed" for modules that haven't run
    """
    from analysis.report_generator import generate_html_report

    job = MockJob(results={}, leakage_results=[])
    health_score_result = None  # health score also not computed yet

    html = generate_html_report(job, health_score_result)

    assert isinstance(html, str)
    assert len(html) > 100
    # At least one "Not Yet Analyzed" section should appear for missing modules
    assert "Not Yet Analyzed" in html


def test_html_report_all_modules_missing():
    """
    Job with no results at all — every module section should read "Not Yet Analyzed".
    """
    from analysis.report_generator import generate_html_report

    job = MockJob(results=None, leakage_results=None)
    html = generate_html_report(job, health_score_result=None)

    assert "Not Yet Analyzed" in html
    # Should not contain an actual score value
    assert "— / 100" in html or "N/A" in html or "—" in html


def test_pdf_report_partial_results_no_exception():
    """
    generate_pdf_report with empty/partial data must:
    - Not raise any exception
    - Return non-empty bytes
    """
    from analysis.report_generator import generate_pdf_report

    job = MockJob(results={}, leakage_results=[])
    pdf_bytes = generate_pdf_report(job, health_score_result=None)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_pdf_report_returns_bytes_for_null_health():
    """Even with null health score, the PDF generator produces valid bytes."""
    from analysis.report_generator import generate_pdf_report

    job = MockJob(results=None, leakage_results=None)
    pdf_bytes = generate_pdf_report(job, health_score_result=None)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


# ---------------------------------------------------------------------------
# 2. Full data — HTML contains key content
# ---------------------------------------------------------------------------

def test_html_report_full_data_contains_score():
    """
    With a complete health_score_result, the HTML must contain the score value
    and module section headers.
    """
    from analysis.report_generator import generate_html_report

    job = MockJob(
        results={
            "total_rows": 200,
            "duplicates": {"count": 2, "percentage": 1.0},
            "missing_data": {"feature_a": {"count": 5, "percentage": 2.5}},
            "calibration": {"supported": True, "brier_score": 0.12},
            "overfitting": {"supported": True, "performance_gap": 0.05},
        },
        leakage_results=[
            {"feature_name": "leaky_feat", "risk_score": 85.0, "drop_pct": 20.0, "known_flag": True},
            {"feature_name": "normal_feat", "risk_score": 10.0, "drop_pct": 2.0, "known_flag": False},
        ],
    )
    health_score_result = {
        "score": 72.5,
        "grade": "B",
        "components": {
            "leakage":     {"penalty": 85.0, "weight": 0.30, "weighted_penalty": 25.5},
            "calibration": {"penalty": 48.0, "weight": 0.15, "weighted_penalty": 7.2},
            "overfitting": {"penalty": 10.0, "weight": 0.20, "weighted_penalty": 2.0},
            "fairness":    {"penalty": 0.0,  "weight": 0.20, "weighted_penalty": 0.0},
            "data_quality":{"penalty": 5.0,  "weight": 0.15, "weighted_penalty": 0.75},
        },
    }

    html = generate_html_report(job, health_score_result)

    assert "72.5" in html
    assert "Target Leakage" in html
    assert "Calibration" in html
    assert "Overfitting" in html
    assert "Data Quality" in html
    assert "leaky_feat" in html


# ---------------------------------------------------------------------------
# 3. LLM fallback
# ---------------------------------------------------------------------------

def test_llm_fallback_no_api_key(settings):
    """
    When LLM_API_KEY is not set, get_llm_summary must return a non-empty
    string without making any network calls.
    """
    from analysis.report_generator import get_llm_summary

    # Ensure LLM_API_KEY is absent
    if hasattr(settings, "LLM_API_KEY"):
        delattr(settings, "LLM_API_KEY")

    findings = {
        "health_score": {"score": 75.5, "grade": "B", "components": {
            "leakage": {"weighted_penalty": 15.0},
        }},
    }

    summary = get_llm_summary(findings)

    assert isinstance(summary, str)
    assert len(summary) > 10  # Not empty


def test_llm_fallback_on_request_error(settings):
    """
    Even when LLM_API_KEY is set, a network failure must not propagate —
    get_llm_summary must fall back to the template summary.
    """
    pytest.importorskip("requests", reason="requests not installed in this env")

    from analysis.report_generator import get_llm_summary

    settings.LLM_API_KEY = "fake-key-for-test"

    findings = {"health_score": {"score": 60.0, "grade": "C", "components": {}}}

    # Patch the lazy alias used inside get_llm_summary
    with patch("analysis.report_generator._requests.post", side_effect=ConnectionError("network down")):
        summary = get_llm_summary(findings)

    assert isinstance(summary, str)
    assert len(summary) > 10


def test_docx_report_partial_results_no_exception():
    """
    generate_docx_report with empty/partial data must:
    - Not raise any exception
    - Return non-empty bytes
    """
    from analysis.report_generator import generate_docx_report

    job = MockJob(results={}, leakage_results=[])
    docx_bytes = generate_docx_report(job, health_score_result=None)

    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0


def test_docx_report_full_data():
    """
    generate_docx_report with complete results must:
    - Not raise any exception
    - Return non-empty bytes
    """
    from analysis.report_generator import generate_docx_report

    job = MockJob(
        results={
            "total_rows": 200,
            "duplicates": {"count": 2, "percentage": 1.0},
            "missing_data": {"feature_a": {"count": 5, "percentage": 2.5}},
            "calibration": {"supported": True, "brier_score": 0.12, "reliability_curve": []},
            "overfitting": {"supported": True, "performance_gap": 0.05, "learning_curve": []},
            "fairness": {"supported": True, "demographic_parity_difference": 0.0, "equalized_odds_difference": 0.0},
        },
        leakage_results=[
            {"feature_name": "leaky_feat", "risk_score": 85.0, "drop_pct": 20.0, "known_flag": True},
            {"feature_name": "normal_feat", "risk_score": 10.0, "drop_pct": 2.0, "known_flag": False},
        ],
    )
    health_score_result = {
        "score": 72.5,
        "grade": "B",
        "components": {
            "leakage":     {"penalty": 85.0, "weight": 0.30, "weighted_penalty": 25.5},
            "calibration": {"penalty": 48.0, "weight": 0.15, "weighted_penalty": 7.2},
            "overfitting": {"penalty": 10.0, "weight": 0.20, "weighted_penalty": 2.0},
            "fairness":    {"penalty": 0.0,  "weight": 0.20, "weighted_penalty": 0.0},
            "data_quality":{"penalty": 5.0,  "weight": 0.15, "weighted_penalty": 0.75},
        },
    }

    docx_bytes = generate_docx_report(job, health_score_result)

    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0
