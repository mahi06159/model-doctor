import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

def analyze_fairness(
    model: Any,
    df: pd.DataFrame,
    target_column: str,
    protected_attribute: Optional[str],
) -> Dict[str, Any]:
    """
    Computes fairness metrics across groups defined by the protected attribute.
    Evaluates Demographic Parity Difference and Equalized Odds Difference.

    Args:
        model: Trained scikit-learn model or pipeline.
        df: Dataset containing features, target, and protected attribute.
        target_column: The name of the target column.
        protected_attribute: The name of the protected attribute column (optional).

    Returns:
        Dict containing demographic parity difference, equalized odds difference,
        group-level selection rates, and support/error details.
    """
    # 1. Gracefully handle case where no protected attribute is provided
    if not protected_attribute:
        return {
            "supported": True,
            "message": "No protected attribute selected. Fairness analysis skipped.",
            "demographic_parity_difference": 0.0,
            "equalized_odds_difference": 0.0,
            "group_metrics": {}
        }

    # 2. Check if protected attribute column exists in dataset
    if protected_attribute not in df.columns:
        return {
            "supported": False,
            "message": f"Protected attribute '{protected_attribute}' not found in the dataset features."
        }

    # 3. Explicit check: model must be a classifier
    is_classifier = hasattr(model, "predict_proba") or (
        hasattr(model, "_estimator_type") and model._estimator_type == "classifier"
    )
    if not is_classifier:
        logger.warning("Model does not support predict_proba or is not classified as a classifier; skipping fairness.")
        return {
            "supported": False,
            "message": "fairness metrics require a classification model"
        }

    try:
        # Extract features and targets
        X = df.drop(columns=[target_column])
        y = df[target_column]

        # Prepare X for prediction (exclude protected attribute)
        X_predict = X.copy()
        if protected_attribute in X_predict.columns:
            X_predict = X_predict.drop(columns=[protected_attribute])

        # Align with model features if feature_names_in_ is present
        if hasattr(model, "feature_names_in_"):
            if all(col in X_predict.columns for col in model.feature_names_in_):
                X_predict = X_predict[model.feature_names_in_]

        # Generate model predictions
        y_pred = model.predict(X_predict)

        # Convert protected attributes to string to standardise groups
        sensitive_features = df[protected_attribute].astype(str)
        groups = sensitive_features.unique()

        if len(groups) < 2:
            return {
                "supported": False,
                "message": f"Protected attribute '{protected_attribute}' has less than 2 groups: {list(groups)}. Cannot compute differences."
            }

        # Encode target and predictions into binary (0/1) for standardized metrics
        le = LabelEncoder()
        y_true_bin = le.fit_transform(y)
        
        # Handle predictions that might contain unseen classes or match y classes
        try:
            y_pred_bin = le.transform(y_pred)
        except ValueError:
            # Fallback if classes differ
            y_pred_bin = LabelEncoder().fit_transform(y_pred)

        # Ensure binary classes for standard TPR/FPR computations
        # If classes are multi-class, we map class 1 vs others (binary)
        if len(le.classes_) != 2:
            # Multi-class fallback: map the most frequent target class as 1, others as 0
            most_frequent = pd.Series(y_true_bin).mode()[0]
            y_true_bin = (y_true_bin == most_frequent).astype(int)
            y_pred_bin = (y_pred_bin == most_frequent).astype(int)

        # Compute group-level metrics
        # Selection rate = positive outcome rate (predict == 1)
        # TPR = TP / (TP + FN)
        # FPR = FP / (FP + TN)
        group_metrics = {}
        for group in groups:
            mask = (sensitive_features == group)
            y_true_g = y_true_bin[mask]
            y_pred_g = y_pred_bin[mask]

            total = len(y_true_g)
            if total == 0:
                continue

            selection_rate = np.mean(y_pred_g == 1)

            # True Positives, False Positives, True Negatives, False Negatives
            tp = np.sum((y_true_g == 1) & (y_pred_g == 1))
            fp = np.sum((y_true_g == 0) & (y_pred_g == 1))
            tn = np.sum((y_true_g == 0) & (y_pred_g == 0))
            fn = np.sum((y_true_g == 1) & (y_pred_g == 0))

            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

            group_metrics[group] = {
                "selection_rate": float(selection_rate),
                "tpr": float(tpr),
                "fpr": float(fpr),
                "count": int(total)
            }

        # Try to use Fairlearn if available for official verification
        try:
            from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference
            dp_diff = demographic_parity_difference(y_true_bin, y_pred_bin, sensitive_features=sensitive_features)
            eo_diff = equalized_odds_difference(y_true_bin, y_pred_bin, sensitive_features=sensitive_features)
        except ImportError:
            # Direct calculations fallback matching demographic_parity_difference and equalized_odds_difference
            selection_rates = [g["selection_rate"] for g in group_metrics.values()]
            dp_diff = max(selection_rates) - min(selection_rates) if selection_rates else 0.0

            tprs = [g["tpr"] for g in group_metrics.values()]
            fprs = [g["fpr"] for g in group_metrics.values()]
            tpr_diff = max(tprs) - min(tprs) if tprs else 0.0
            fpr_diff = max(fprs) - min(fprs) if fprs else 0.0
            eo_diff = max(tpr_diff, fpr_diff)

        # Clamping metric diffs to [0.0, 1.0]
        dp_diff = float(max(0.0, min(1.0, dp_diff)))
        eo_diff = float(max(0.0, min(1.0, eo_diff)))

        return {
            "supported": True,
            "demographic_parity_difference": dp_diff,
            "equalized_odds_difference": eo_diff,
            "group_metrics": group_metrics
        }

    except Exception as e:
        logger.error(f"Fairness analysis failed: {str(e)}", exc_info=True)
        return {
            "supported": False,
            "message": f"Fairness analysis failed: {str(e)}"
        }
