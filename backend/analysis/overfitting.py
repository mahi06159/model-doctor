import numpy as np
import pandas as pd
import logging
from typing import Dict, Any
from sklearn.model_selection import learning_curve
from sklearn.base import is_classifier

logger = logging.getLogger(__name__)


def analyze_overfitting(model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    """
    Evaluates learning curve metrics to detect overfitting:
    - Train scores vs Test scores across increasing training sample sizes.
    - Performance gap at maximum training size.
    - Validation score cross-validation variance.
    
    Args:
        model: Fitted scikit-learn estimator or pipeline.
        X: Feature matrix.
        y: Target series.
        
    Returns:
        Dict with learning curve data points and overfitting diagnostic summaries.
    """
    # Select scoring metric: accuracy for classification, R2 for regression
    is_clf = is_classifier(model)
    scoring = "accuracy" if is_clf else "r2"
    
    # Configure cross-validation folds: 3 folds for small datasets, 5 folds for larger
    cv_folds = 3 if len(X) < 100 else 5
    
    # Check minimum required samples to do CV learning curve (at least 10 rows)
    if len(X) < 10:
        return {
            "supported": False,
            "message": "Dataset too small to compute overfitting learning curves (requires >= 10 rows)."
        }
        
    # Generate 5 sizes of training sizes: from 20% to 100%
    train_sizes = np.linspace(0.2, 1.0, 5)
    
    try:
        train_sizes_out, train_scores, test_scores = learning_curve(
            model,
            X,
            y,
            cv=cv_folds,
            train_sizes=train_sizes,
            scoring=scoring,
            n_jobs=1,  # Set to 1 inside Celery/Docker to prevent nested multiprocess conflicts
            random_state=42
        )
        
        # Calculate mean and standard deviation across cross-validation folds
        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        test_mean = np.mean(test_scores, axis=1)
        test_std = np.std(test_scores, axis=1)
        
        # Structure points for graphing
        learning_curve_data = [
            {
                "train_size": int(size),
                "train_score": round(float(t_mean), 4),
                "test_score": round(float(v_mean), 4),
                "train_std": round(float(t_std), 4),
                "test_std": round(float(v_std), 4)
            }
            for size, t_mean, v_mean, t_std, v_std in zip(train_sizes_out, train_mean, test_mean, train_std, test_std)
        ]
        
        # Performance gap is (training score - validation score) at max data size
        performance_gap = train_mean[-1] - test_mean[-1]
        
        # Cross-validation variance is variance of the test scores at max data size
        cv_variance = np.var(test_scores[-1])
        
        return {
            "supported": True,
            "metric": scoring,
            "learning_curve": learning_curve_data,
            "performance_gap": round(float(performance_gap), 4),
            "cv_variance": round(float(cv_variance), 6)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate learning curves: {str(e)}", exc_info=True)
        return {
            "supported": False,
            "message": f"Overfitting calculation error: {str(e)}"
        }
