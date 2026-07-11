import pytest
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from analysis.feature_dominance import analyze_feature_dominance


def test_feature_dominance_ranking():
    """
    Test analyze_feature_dominance with a RandomForestClassifier.
    The dataset has a dominant feature (high correlation), a sub feature (moderate correlation),
    and a noise feature (zero correlation).
    """
    np.random.seed(42)
    n_samples = 200
    
    target = np.random.randint(0, 2, size=n_samples)
    # Dominant feature is extremely predictive (very low noise)
    dominant_feature = target * 2.0 + np.random.normal(0, 0.1, size=n_samples)
    # Sub feature is moderately predictive (medium noise)
    sub_feature = target * 2.0 + np.random.normal(0, 1.0, size=n_samples)
    # Noise feature is completely random
    noise_feature = np.random.normal(0, 1.0, size=n_samples)
    
    df = pd.DataFrame({
        "dominant_feature": dominant_feature,
        "sub_feature": sub_feature,
        "noise_feature": noise_feature,
        "target": target
    })
    
    X = df.drop(columns=["target"])
    y = df["target"]
    
    model = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
    model.fit(X, y)
    
    results = analyze_feature_dominance(model, X, y)
    
    assert results["supported"] is True
    assert "ranking" in results
    
    ranking = results["ranking"]
    assert len(ranking) == 3
    
    # Assert features are ranked correctly: dominant_feature first, sub_feature second, noise_feature last
    assert ranking[0]["feature_name"] == "dominant_feature"
    assert ranking[1]["feature_name"] == "sub_feature"
    assert ranking[2]["feature_name"] == "noise_feature"
    
    # Assert importances follow the correct hierarchy
    assert ranking[0]["importance"] > ranking[1]["importance"]
    assert ranking[1]["importance"] > ranking[2]["importance"]
