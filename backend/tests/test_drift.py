import pytest
import pandas as pd
import numpy as np
from analysis.drift import analyze_drift

def test_data_drift_detected():
    """
    Test analyze_drift with a synthetic dataset containing a deliberately shifted distribution.
    Feature 1 has no shift (mean 0.0 vs 0.0).
    Feature 2 has a strong shift (mean 0.0 vs 2.5).
    """
    np.random.seed(42)
    n_samples = 200
    
    # Train set (baseline)
    train_df = pd.DataFrame({
        "feat_stable": np.random.normal(loc=0.0, scale=1.0, size=n_samples),
        "feat_shifted": np.random.normal(loc=0.0, scale=1.0, size=n_samples),
        "target": np.random.randint(0, 2, size=n_samples)
    })
    
    # Prod set (shifted)
    prod_df = pd.DataFrame({
        "feat_stable": np.random.normal(loc=0.0, scale=1.0, size=n_samples),
        # Shift the mean from 0.0 to 2.5
        "feat_shifted": np.random.normal(loc=2.5, scale=1.0, size=n_samples),
        "target": np.random.randint(0, 2, size=n_samples)
    })
    
    results = analyze_drift(train_df, prod_df, target_column="target")
    
    assert results["supported"] is True
    assert "feat_stable" in results["drift_by_feature"]
    assert "feat_shifted" in results["drift_by_feature"]
    
    # Stable feature should have very low PSI (typically < 0.1)
    assert results["drift_by_feature"]["feat_stable"]["psi"] < 0.1
    # Shifted feature should have a high PSI (typically > 0.2, often > 1.0 for a shift of 2.5 std devs)
    assert results["drift_by_feature"]["feat_shifted"]["psi"] > 0.2
    assert results["drift_by_feature"]["feat_shifted"]["drift_detected"] is True
    
    # KS-test p-value should detect shift for feat_shifted (p-value should be near 0.0)
    assert results["drift_by_feature"]["feat_shifted"]["ks_p_value"] < 0.01
    # Stable feature p-value should not reject the null hypothesis (typically > 0.05)
    assert results["drift_by_feature"]["feat_stable"]["ks_p_value"] > 0.05
    
    # Summary assertions
    assert results["drifted_features_count"] == 1
    assert results["total_features"] == 2
    assert results["drift_percentage"] == 50.0
