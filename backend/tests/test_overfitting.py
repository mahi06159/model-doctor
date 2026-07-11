import pytest
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from analysis.overfitting import analyze_overfitting


def test_overfitting_analysis_detected():
    """
    Test analyze_overfitting with a DecisionTreeClassifier on random noise features.
    This should result in high training accuracy (near 1.0) and poor validation accuracy (near 0.5),
    yielding a high performance gap (overfitting).
    """
    np.random.seed(42)
    # 50 samples, 10 random features
    X = pd.DataFrame(np.random.normal(size=(50, 10)), columns=[f"feat_{i}" for i in range(10)])
    # Target target unrelated to features (random binary targets)
    y = pd.Series(np.random.randint(0, 2, size=50))
    
    # Train a deep decision tree that memorizes the training data
    model = DecisionTreeClassifier(max_depth=15, random_state=42)
    model.fit(X, y)
    
    results = analyze_overfitting(model, X, y)
    
    assert results["supported"] is True
    assert results["metric"] == "accuracy"
    assert len(results["learning_curve"]) == 5
    
    # The performance gap (train_score - test_score at max size) should be high
    # since the model memorized the training subset but performs randomly on CV test sets.
    assert results["performance_gap"] > 0.20
    assert "cv_variance" in results


def test_overfitting_unsupported_small_dataset():
    """
    Test analyze_overfitting with a dataset that is too small (fewer than 10 rows).
    """
    X = pd.DataFrame({"feat": [1, 2, 3, 4, 5]})
    y = pd.Series([0, 1, 0, 1, 0])
    model = DecisionTreeClassifier(max_depth=2, random_state=42)
    
    results = analyze_overfitting(model, X, y)
    
    assert results["supported"] is False
    assert "too small" in results["message"].lower()
