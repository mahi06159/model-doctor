import pytest
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from analysis.fairness import analyze_fairness

def test_fairness_biased_dataset():
    """
    Test analyze_fairness with a synthetic biased dataset.
    Group 'A' gets positive prediction rate of 1.0, while Group 'B' gets 0.0.
    """
    np.random.seed(42)
    # Create 100 samples
    n_samples = 100
    
    # Protected attribute: 'group' with values 'A' or 'B'
    group = np.random.choice(['A', 'B'], size=n_samples)
    
    # Make a feature that correlates strongly with group
    # Feature is 1 for group A, 0 for group B
    feat = np.where(group == 'A', 1.0, 0.0)
    
    # Target target matches the feature (perfect correlation/bias)
    y = pd.Series(np.where(group == 'A', 1, 0))
    X = pd.DataFrame({"feat": feat, "group": group})
    
    # Fit a simple DecisionTree
    model = DecisionTreeClassifier(max_depth=2, random_state=42)
    # Exclude group from training features, but keep in df for analysis
    X_train = X.drop(columns=["group"])
    model.fit(X_train, y)
    
    # We pass the full df including group and target
    df = X.copy()
    df["target"] = y
    
    results = analyze_fairness(
        model=model,
        df=df,
        target_column="target",
        protected_attribute="group"
    )
    
    assert results["supported"] is True
    # Group A selection rate is 1.0, Group B selection rate is 0.0
    # Demographic Parity Difference = 1.0 - 0.0 = 1.0
    assert results["demographic_parity_difference"] > 0.8
    assert results["equalized_odds_difference"] > 0.8
    
    # Check group metrics
    assert "A" in results["group_metrics"]
    assert "B" in results["group_metrics"]
    assert results["group_metrics"]["A"]["selection_rate"] > 0.9
    assert results["group_metrics"]["B"]["selection_rate"] < 0.1


def test_fairness_regression_model_graceful_failure():
    """
    Assert that a regression model uploaded with a protected attribute selected 
    fails gracefully with a clear message ("fairness metrics require a classification model") 
    in results, rather than crashing.
    """
    X = pd.DataFrame({"feat": [1.0, 2.0, 3.0, 4.0], "group": ["A", "A", "B", "B"]})
    y = pd.Series([10.0, 20.0, 30.0, 40.0])
    df = X.copy()
    df["target"] = y
    
    # Use Regressor
    model = DecisionTreeRegressor(random_state=42)
    model.fit(X.drop(columns=["group"]), y)
    
    results = analyze_fairness(
        model=model,
        df=df,
        target_column="target",
        protected_attribute="group"
    )
    
    assert results["supported"] is False
    assert "fairness metrics require a classification model" in results["message"]


def test_fairness_no_protected_attribute_completes():
    """
    Assert that a job with no protected_attribute selected completes 
    without crashing and metrics are 0.0.
    """
    X = pd.DataFrame({"feat": [1, 0, 1, 0]})
    y = pd.Series([1, 0, 1, 0])
    df = X.copy()
    df["target"] = y
    
    model = DecisionTreeClassifier(random_state=42)
    model.fit(X, y)
    
    results = analyze_fairness(
        model=model,
        df=df,
        target_column="target",
        protected_attribute=None
    )
    
    assert results["supported"] is True
    assert results["demographic_parity_difference"] == 0.0
    assert results["equalized_odds_difference"] == 0.0
    assert results["group_metrics"] == {}
