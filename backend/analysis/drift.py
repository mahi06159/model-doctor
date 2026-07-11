import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_bins: int = 10) -> float:
    """
    Computes the Population Stability Index (PSI) between two distributions.
    
    PSI = sum((actual_pct - expected_pct) * ln(actual_pct / expected_pct))
    """
    # Exclude nulls
    expected = expected[~pd.isna(expected)]
    actual = actual[~pd.isna(actual)]
    
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Determine if categorical or numerical
    is_numeric = np.issubdtype(expected.dtype, np.number) and len(np.unique(expected)) > 5
    
    if is_numeric:
        # Numeric: define bin boundaries using percentiles of expected (train) data
        percentiles = np.linspace(0, 100, num_bins + 1)
        bin_edges = np.percentile(expected, percentiles)
        # Ensure unique bin edges
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            # If all values are identical, treat as categorical
            bin_edges = None
            
    if not is_numeric or bin_edges is None:
        # Categorical: bin by unique categories
        categories = np.unique(np.concatenate([expected, actual]))
        expected_counts = []
        actual_counts = []
        for cat in categories:
            expected_counts.append(np.sum(expected == cat))
            actual_counts.append(np.sum(actual == cat))
    else:
        # Numeric binning
        # Adjust outer edges slightly to include min/max values
        bin_edges[0] -= 1e-5
        bin_edges[-1] += 1e-5
        expected_counts, _ = np.histogram(expected, bins=bin_edges)
        actual_counts, _ = np.histogram(actual, bins=bin_edges)

    expected_counts = np.array(expected_counts, dtype=float)
    actual_counts = np.array(actual_counts, dtype=float)

    # Normalize to percentages
    expected_pct = expected_counts / len(expected)
    actual_pct = actual_counts / len(actual)

    # Handle zero division/log(0) by adding a small constant and normalizing
    eps = 1e-4
    expected_pct = np.where(expected_pct == 0, eps, expected_pct)
    actual_pct = np.where(actual_pct == 0, eps, actual_pct)
    
    expected_pct /= np.sum(expected_pct)
    actual_pct /= np.sum(actual_pct)

    # Calculate PSI
    psi_value = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi_value)


def analyze_drift(train_df: pd.DataFrame, prod_df: pd.DataFrame, target_column: str) -> Dict[str, Any]:
    """
    Compares train_df against prod_df to measure data drift per feature.
    Uses Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) test.

    Args:
        train_df: Training dataset features (can include target_column).
        prod_df: Production dataset features (can include target_column).
        target_column: Column name of target to exclude from features check.

    Returns:
        Dict containing drift results per feature, overall summary, and flags.
    """
    try:
        # Exclude target column from features list
        features = [col for col in train_df.columns if col != target_column]

        # Check that production features align with train features
        missing_features = [col for col in features if col not in prod_df.columns]
        if missing_features:
            return {
                "supported": False,
                "message": f"Production dataset is missing features present in training data: {missing_features}"
            }

        # Imports for statistics
        from scipy.stats import ks_2samp

        drift_results = {}
        drifted_features_count = 0

        for col in features:
            train_vals = train_df[col].values
            prod_vals = prod_df[col].values

            # Calculate PSI
            psi_val = calculate_psi(train_vals, prod_vals)

            # Calculate KS Test (only for numeric columns)
            is_numeric = np.issubdtype(train_vals.dtype, np.number)
            ks_stat = None
            ks_p_val = None
            if is_numeric and len(np.unique(train_vals)) > 1:
                # Filter NaNs for KS-test
                t_clean = train_vals[~pd.isna(train_vals)]
                p_clean = prod_vals[~pd.isna(prod_vals)]
                if len(t_clean) > 0 and len(p_clean) > 0:
                    ks_res = ks_2samp(t_clean, p_clean)
                    ks_stat = float(ks_res.statistic)
                    ks_p_val = float(ks_res.pvalue)

            # PSI threshold > 0.2 indicates significant drift
            drift_flag = psi_val > 0.2
            if drift_flag:
                drifted_features_count += 1

            drift_results[col] = {
                "psi": round(psi_val, 4),
                "ks_statistic": round(ks_stat, 4) if ks_stat is not None else None,
                "ks_p_value": round(ks_p_val, 4) if ks_p_val is not None else None,
                "drift_detected": bool(drift_flag)
            }

        return {
            "supported": True,
            "drift_by_feature": drift_results,
            "drifted_features_count": drifted_features_count,
            "total_features": len(features),
            "drift_percentage": round((drifted_features_count / len(features) * 100) if features else 0.0, 2)
        }

    except Exception as e:
        logger.error(f"Drift analysis failed: {str(e)}", exc_info=True)
        return {
            "supported": False,
            "message": f"Drift analysis failed: {str(e)}"
        }
