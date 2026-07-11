import pytest
import pandas as pd
import numpy as np
from analysis.leakage import analyze_leakage
from analysis.tests.fixtures.make_leaky_dataset import generate_leaky_data


def test_leakage_detection_algorithm():
    """
    Test that the leakage detection engine correctly identifies target leakage.
    - `leaky_feature` is a direct copy of target.
    - `normal_feature` has a moderate correlation.
    - `noise_feature` has zero real correlation.
    """
    df, model = generate_leaky_data(n_samples=200, random_state=42)
    known_map = {
        "leaky_feature": True,
        "normal_feature": True,
        "noise_feature": True
    }
    
    # Run the leakage check
    results = analyze_leakage(df, target_column="target", model=model, known_at_prediction_time_map=known_map)
    
    # Assertions
    # 1. 3 features should be evaluated
    assert len(results) == 3
    
    # Map results by feature name for easy querying
    res_map = {res["feature_name"]: res for res in results}
    
    # 2. leaky_feature must have the highest risk score
    assert results[0]["feature_name"] == "leaky_feature"
    assert res_map["leaky_feature"]["risk_score"] > res_map["normal_feature"]["risk_score"]
    assert res_map["leaky_feature"]["risk_score"] > res_map["noise_feature"]["risk_score"]
    
    # 3. leaky_feature must have a high performance drop when retrained without it (Signal 1)
    # Since it's the only real source of strong signals, dropping it causes the tree to collapse.
    assert res_map["leaky_feature"]["drop_pct"] > 15.0
    
    # 4. leaky_feature risk score should be extremely high (near 100%)
    assert res_map["leaky_feature"]["risk_score"] >= 90.0


def test_visibility_constraint_leakage():
    """
    Test Signal 3 where a feature is marked "unknown at prediction time" (visibility constraint).
    If it has non-trivial importance, it should get auto-flagged (known_flag = True).
    """
    # Generate synthetic dataset specifically for visibility constraint testing (no perfect leak)
    from sklearn.tree import DecisionTreeClassifier
    np.random.seed(42)
    n_samples = 200
    target = np.random.randint(0, 2, size=n_samples)
    normal_feature = target * 2.0 + np.random.normal(0, 0.5, size=n_samples)
    noise_feature = np.random.normal(0, 1.0, size=n_samples)
    
    df = pd.DataFrame({
        "normal_feature": normal_feature,
        "noise_feature": noise_feature,
        "target": target
    })
    X = df.drop(columns=["target"])
    y = df["target"]
    model = DecisionTreeClassifier(max_depth=3, random_state=42)
    model.fit(X, y)
    
    # Mark 'normal_feature' as unknown at prediction time
    known_map = {
        "normal_feature": False,
        "noise_feature": True
    }
    
    results = analyze_leakage(df, target_column="target", model=model, known_at_prediction_time_map=known_map)
    res_map = {res["feature_name"]: res for res in results}
    
    # normal_feature is unknown at prediction time and has non-trivial importance,
    # so its known_flag should be True, producing high risk score.
    assert res_map["normal_feature"]["known_flag"] is True
    assert res_map["normal_feature"]["risk_score"] >= 70.0
    
    # noise_feature is known at prediction time, so its known_flag should be False
    assert res_map["noise_feature"]["known_flag"] is False
