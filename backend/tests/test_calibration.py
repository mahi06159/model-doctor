import pytest
import pandas as pd
import numpy as np
from analysis.calibration import analyze_calibration


class MockModel:
    def __init__(self, probabilities):
        self.probabilities = np.array(probabilities)
        self.classes_ = np.array([0, 1])

    def predict_proba(self, X):
        return self.probabilities


def test_calibration_supported_classification():
    """
    Test analyze_calibration for a binary classifier with badly calibrated probabilities.
    """
    # 10 samples
    X = pd.DataFrame({"feature": np.random.normal(size=10)})
    y = pd.Series([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    
    # Predefined probabilities where positive class predicted probability is always 0.9
    # but actual targets are balanced, indicating poor calibration (predicted = 0.9, actual = 0.5)
    probs = np.column_stack([np.ones(10) * 0.1, np.ones(10) * 0.9])
    
    model = MockModel(probs)
    results = analyze_calibration(model, X, y)
    
    assert results["supported"] is True
    # Brier score = mean((y - prob)^2)
    # y = [0,0,0,0,0,1,1,1,1,1], prob = 0.9
    # (y - prob)^2 for y=0: (0 - 0.9)^2 = 0.81 (5 times)
    # (y - prob)^2 for y=1: (1 - 0.9)^2 = 0.01 (5 times)
    # Mean = (5 * 0.81 + 5 * 0.01) / 10 = (4.05 + 0.05) / 10 = 0.41
    assert abs(results["brier_score"] - 0.41) < 1e-4
    assert len(results["reliability_data"]) == 1
    # The predicted probability in the bin should be 0.9, actual should be 0.5
    assert results["reliability_data"][0]["pred_prob"] == 0.9
    assert results["reliability_data"][0]["actual_prob"] == 0.5


def test_calibration_unsupported_model():
    """
    Test analyze_calibration for a model without predict_proba.
    """
    class NoProbaModel:
        pass
    
    X = pd.DataFrame({"feature": [1, 2]})
    y = pd.Series([0, 1])
    model = NoProbaModel()
    
    results = analyze_calibration(model, X, y)
    assert results["supported"] is False
    assert "supported" in results
