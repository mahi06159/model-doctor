import numpy as np
import pandas as pd
import logging
from typing import Dict, Any
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

logger = logging.getLogger(__name__)


def analyze_calibration(model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    """
    Computes model calibration metrics including:
    - Brier score loss
    - Predicted vs actual probability bins (Reliability diagram data)
    
    Args:
        model: Fitted scikit-learn estimator or pipeline.
        X: Feature matrix.
        y: Target series.
        
    Returns:
        Dict containing reliability diagram bins, Brier score, and support status.
    """
    # Calibration is standard for classification models with predict_proba
    if not hasattr(model, "predict_proba"):
        logger.warning("Model does not support predict_proba; skipping calibration check.")
        return {
            "supported": False,
            "message": "Calibration analysis is only supported for classification models with probability output (predict_proba)."
        }
        
    try:
        # Predict class probabilities
        y_prob = model.predict_proba(X)
        
        # Format labels as binary 0 and 1
        le = LabelEncoder()
        y_binary = le.fit_transform(y)
        
        # If binary classification
        if len(le.classes_) == 2:
            # Predict probabilities of positive class (index 1)
            y_prob_pos = y_prob[:, 1]
            
            # Compute Brier score loss
            brier_score = brier_score_loss(y_binary, y_prob_pos)
            
            # Compute reliability curve data using uniform strategy (10 bins)
            prob_true, prob_pred = calibration_curve(y_binary, y_prob_pos, n_bins=10, strategy='uniform')
            
            reliability_data = [
                {
                    "bin": i + 1,
                    "pred_prob": round(float(p_pred), 4),
                    "actual_prob": round(float(p_true), 4)
                }
                for i, (p_pred, p_true) in enumerate(zip(prob_pred, prob_true))
            ]
            
            return {
                "supported": True,
                "brier_score": round(float(brier_score), 4),
                "reliability_data": reliability_data
            }
        else:
            # For multi-class, compute calibration for the positive target class or top predicted class.
            # To remain simple and robust in multi-class, we focus calibration on the most frequent class vs rest.
            most_frequent_class_idx = int(np.argmax(np.bincount(y_binary)))
            y_binary_multiclass = (y_binary == most_frequent_class_idx).astype(int)
            y_prob_multiclass = y_prob[:, most_frequent_class_idx]
            
            brier_score = brier_score_loss(y_binary_multiclass, y_prob_multiclass)
            prob_true, prob_pred = calibration_curve(y_binary_multiclass, y_prob_multiclass, n_bins=10, strategy='uniform')
            
            reliability_data = [
                {
                    "bin": i + 1,
                    "pred_prob": round(float(p_pred), 4),
                    "actual_prob": round(float(p_true), 4)
                }
                for i, (p_pred, p_true) in enumerate(zip(prob_pred, prob_true))
            ]
            
            return {
                "supported": True,
                "brier_score": round(float(brier_score), 4),
                "reliability_data": reliability_data,
                "multiclass_target": str(le.classes_[most_frequent_class_idx])
            }
            
    except Exception as e:
        logger.error(f"Failed to analyze model calibration: {str(e)}", exc_info=True)
        return {
            "supported": False,
            "message": f"Calibration calculation error: {str(e)}"
        }
