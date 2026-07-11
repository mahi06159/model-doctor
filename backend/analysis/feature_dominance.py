import pandas as pd
import logging
from typing import Dict, Any, List
from .leakage import compute_shap_values

logger = logging.getLogger(__name__)


def analyze_feature_dominance(model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    """
    Computes global importance ranking using SHAP / Permutation values.
    Reuses the `compute_shap_values` function from backend.analysis.leakage.
    
    Args:
        model: Trained scikit-learn model.
        X: Feature matrix.
        y: Target series.
        
    Returns:
        Dict containing list of features and their global SHAP importances, sorted descending.
    """
    try:
        # Compute global shap importances
        shap_importances = compute_shap_values(model, X, y)
        
        # Sort features by importance in descending order
        sorted_shaps = sorted(shap_importances.items(), key=lambda item: item[1], reverse=True)
        
        ranking = [
            {
                "feature_name": name,
                "importance": round(float(val), 6)
            }
            for name, val in sorted_shaps
        ]
        
        return {
            "supported": True,
            "ranking": ranking
        }
    except Exception as e:
        logger.error(f"Failed to analyze feature dominance: {str(e)}", exc_info=True)
        return {
            "supported": False,
            "message": f"Feature dominance calculation error: {str(e)}"
        }
