import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List
from sklearn.base import clone, is_classifier
from sklearn.metrics import accuracy_score, r2_score

logger = logging.getLogger(__name__)

"""
Leakage Detection Engine
========================

This module implements the 3-signal leakage algorithm to identify features that leak the target variable.

Why Correlation Alone Is Not Used for Leakage Detection:
---------------------------------------------------------
1. Linear Assumption Limitations:
   Standard correlation measures (like Pearson correlation) only capture linear relationships. Target leakage
   can occur through highly non-linear transformations (e.g. logarithmic, polynomial, binning, or conditional hashes).
   A feature could be a direct deterministic leak of the target (e.g. `leaked = (target ** 2) % 3`) but have a 
   Pearson correlation near zero.
   
2. Multi-Feature Interactions:
   A single feature might not correlate with the target on its own. However, when combined with other features 
   in a non-linear model (e.g. tree splits or neural activations), it may reconstruct the target with high precision.
   Single-feature correlation entirely misses these multi-feature leakage interactions.
   
3. Model-in-the-Loop context:
   Correlation doesn't tell us how the model actually uses the feature. A feature can have high correlation with the target
   but be completely ignored by the model's regularisation (e.g. Ridge penalty, high tree depth, or dropout). 
   Conversely, a feature with moderate correlation might be heavily exploited by the model, creating high prediction-time risk. 
   Using model-in-the-loop metrics (SHAP and retraining performance drop) ensures we measure how the model actually 
   harnesses the feature.
"""


def compute_shap_values(model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
    """
    Computes global feature importances using SHAP values.
    Includes a robust fallback to Permutation Importance if the `shap` package
    is not installed, throws errors, or is too computationally expensive.
    
    Args:
        model: Fitted scikit-learn estimator or pipeline.
        X: Feature matrix.
        y: Target values.
        
    Returns:
        A dictionary mapping feature names to their mean absolute SHAP / permutation importance.
    """
    feature_names = list(X.columns)
    
    try:
        import shap
        
        # Sample down to speed up SHAP calculation (KernelExplainer is O(N * M))
        if len(X) > 100:
            X_sample = X.sample(n=100, random_state=42)
            y_sample = y.loc[X_sample.index]
        else:
            X_sample = X
            y_sample = y
            
        logger.info("Attempting to compute SHAP values...")
        
        # Try TreeExplainer (fastest for trees)
        try:
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_sample)
        except Exception:
            # Try general Explainer
            try:
                explainer = shap.Explainer(model, X_sample)
                shap_values = explainer(X_sample)
                if hasattr(shap_values, "values"):
                    shap_values = shap_values.values
            except Exception:
                # Fall back to KernelExplainer
                # KernelExplainer needs a predict/predict_proba function
                pred_fn = model.predict_proba if hasattr(model, "predict_proba") else model.predict
                explainer = shap.KernelExplainer(pred_fn, X_sample)
                shap_values = explainer.shap_values(X_sample)
                
        # Handle multi-class classification or multi-output cases
        # shap_values could be a list (one array per class) or a 3D array (samples, features, classes)
        if isinstance(shap_values, list):
            # Take the mean of absolute values across classes
            abs_vals = np.mean([np.abs(cls_shap) for cls_shap in shap_values], axis=0)
        elif len(shap_values.shape) == 3:
            # Multiclass Explanation object shape: (samples, features, classes)
            abs_vals = np.mean(np.abs(shap_values), axis=2)
        else:
            abs_vals = np.abs(shap_values)
            
        mean_abs_shap = np.mean(abs_vals, axis=0)
        
        # Ensure we return a dictionary of Python floats
        return {name: float(val) for name, val in zip(feature_names, mean_abs_shap)}
        
    except Exception as e:
        logger.warning(f"SHAP calculation failed or shap not installed: {str(e)}. Falling back to Permutation Importance.")
        # Robust fallback: permutation importance
        from sklearn.inspection import permutation_importance
        try:
            # We use a fast permutation importance to serve as a reliable fallback
            # We sample if dataset is large to keep it responsive
            if len(X) > 500:
                X_sample = X.sample(n=500, random_state=42)
                y_sample = y.loc[X_sample.index]
            else:
                X_sample = X
                y_sample = y
                
            r = permutation_importance(model, X_sample, y_sample, n_repeats=3, random_state=42)
            # Ensure values are non-negative
            importances = np.maximum(0.0, r.importances_mean)
            return {name: float(val) for name, val in zip(feature_names, importances)}
        except Exception as fallback_err:
            logger.error(f"Permutation importance fallback also failed: {str(fallback_err)}")
            # Ultimate safety net: return 0.0 for all features
            return {name: 0.0 for name in feature_names}


def analyze_leakage(
    df: pd.DataFrame,
    target_column: str,
    model: Any,
    known_at_prediction_time_map: Dict[str, bool],
    sample_threshold: int = 5000
) -> List[Dict[str, Any]]:
    """
    Main leakage assessment executing:
    - Signal 1: Retraining Drop
    - Signal 2: SHAP Dominance
    - Signal 3: Visibility Constraint Check
    - Fuzzy-OR Score Aggregation
    
    Args:
        df: Pandas DataFrame containing features and target.
        target_column: Name of the target variable.
        model: Trained scikit-learn estimator or pipeline.
        known_at_prediction_time_map: Dict mapping features to boolean visibility at prediction time.
        sample_threshold: Rows threshold above which data is sampled for the retraining step.
        
    Returns:
        List of dictionaries with leakage metrics and risk scores for each feature.
    """
    X = df.drop(columns=[target_column])
    y = df[target_column]
    features = list(X.columns)
    
    # Calculate baseline performance
    is_classification_task = is_classifier(model)
    
    # Pre-split predictions to compute baseline score
    y_pred_baseline = model.predict(X)
    if is_classification_task:
        baseline_score = accuracy_score(y, y_pred_baseline)
    else:
        baseline_score = r2_score(y, y_pred_baseline)
        
    logger.info(f"Baseline model score ({'Accuracy' if is_classification_task else 'R2'}): {baseline_score:.4f}")
    
    # Handle retraining dataset sampling for performance
    if len(df) > sample_threshold:
        logger.info(f"Dataset has {len(df)} rows (exceeds threshold {sample_threshold}). Sampling 2000 rows for retraining.")
        df_sample = df.sample(n=2000, random_state=42)
        X_retrain_base = df_sample.drop(columns=[target_column])
        y_retrain = df_sample[target_column]
    else:
        X_retrain_base = X.copy()
        y_retrain = y.copy()
        
    # SIGNAL 1: Retrain without each feature one at a time
    drop_pcts = {}
    for feat in features:
        # Clone the model architecture to fit from scratch
        cloned_model = clone(model)
        
        # Exclude feature
        X_retrain_no_feat = X_retrain_base.drop(columns=[feat])
        X_eval_no_feat = X.drop(columns=[feat])
        
        try:
            # Retrain model on shape (M-1)
            cloned_model.fit(X_retrain_no_feat, y_retrain)
            y_pred_no_feat = cloned_model.predict(X_eval_no_feat)
            
            if is_classification_task:
                score_no_feat = accuracy_score(y, y_pred_no_feat)
            else:
                score_no_feat = r2_score(y, y_pred_no_feat)
        except Exception as e:
            # Fallback in case dropping column breaks Pipeline or ColumnTransformer feature name alignments:
            # We retrain on the same columns but overwrite the specific feature with its mean / mode value (zeroing variance)
            logger.warning(f"Drop retraining failed for {feat}: {str(e)}. Falling back to zero-variance retraining.")
            cloned_model = clone(model)
            X_retrain_fallback = X_retrain_base.copy()
            X_eval_fallback = X.copy()
            
            if X_retrain_fallback[feat].dtype in [np.float64, np.float32, np.int64, np.int32]:
                fill_val = X_retrain_fallback[feat].mean()
            else:
                fill_val = X_retrain_fallback[feat].mode()[0] if not X_retrain_fallback[feat].mode().empty else 0
                
            X_retrain_fallback[feat] = fill_val
            X_eval_fallback[feat] = fill_val
            
            cloned_model.fit(X_retrain_fallback, y_retrain)
            y_pred_fallback = cloned_model.predict(X_eval_fallback)
            
            if is_classification_task:
                score_no_feat = accuracy_score(y, y_pred_fallback)
            else:
                score_no_feat = r2_score(y, y_pred_fallback)
                
        # Calculate relative drop pct: (Baseline - ScoreWithoutFeature) / Baseline * 100
        if abs(baseline_score) > 1e-6:
            drop_pct = ((baseline_score - score_no_feat) / baseline_score) * 100
        else:
            drop_pct = 0.0
            
        drop_pcts[feat] = max(0.0, drop_pct)
        
    # SIGNAL 2: Compute SHAP Global Importance & Dominance Ratio
    shap_importances = compute_shap_values(model, X, y)
    
    # Sort features by SHAP importance to compute dominance ratio
    sorted_shaps = sorted(shap_importances.items(), key=lambda item: item[1], reverse=True)
    
    # Global ratio of top feature vs second-highest
    top_to_second_ratio = 1.0
    top_feature_name = None
    if len(sorted_shaps) >= 2:
        top_feature_name, top_val = sorted_shaps[0]
        second_feature_name, second_val = sorted_shaps[1]
        if second_val > 1e-8:
            top_to_second_ratio = top_val / second_val
        else:
            top_to_second_ratio = 999.0 if top_val > 0 else 1.0
            
    # SIGNAL 3: Cross-check prediction visibility limits
    # Total sum of importances to evaluate relative share
    total_shap_sum = sum(shap_importances.values())
    
    results = []
    for feat in features:
        # Fetch configurations (defaults to True if not specified)
        known = known_at_prediction_time_map.get(feat, True)
        
        # 1. Signal 1 Score (Retraining Drop)
        # Flag threshold is 15%. We map 15% drop to a score of 70, scaling up to 100
        drop_val = drop_pcts[feat]
        if drop_val <= 0:
            s1_score = 0.0
        elif drop_val <= 15.0:
            s1_score = (drop_val / 15.0) * 70.0
        else:
            s1_score = 70.0 + min(30.0, ((drop_val - 15.0) / 35.0) * 30.0)
            
        # 2. Signal 2 Score (SHAP Dominance)
        # Only the absolute highest feature gets flagged if ratio > 3
        # Flag threshold is ratio > 3. We map ratio = 3 to a score of 70
        is_top = (feat == top_feature_name)
        if is_top and len(features) >= 2:
            feat_ratio = top_to_second_ratio
            if feat_ratio <= 1.0:
                s2_score = 0.0
            elif feat_ratio <= 3.0:
                s2_score = ((feat_ratio - 1.0) / 2.0) * 70.0
            else:
                s2_score = 70.0 + min(30.0, ((feat_ratio - 3.0) / 7.0) * 30.0)
        else:
            s2_score = 0.0
            feat_ratio = 1.0
            
        # 3. Signal 3 Score (Visibility Cross-check)
        # Triggered if a feature is marked "unknown at prediction time" AND has non-trivial importance.
        # "Non-trivial" is defined as:
        #   - contributing > 5% of total SHAP global importance, OR
        #   - causing a retrain performance drop > 1%
        importance_share = (shap_importances[feat] / total_shap_sum) if total_shap_sum > 1e-8 else 0.0
        has_nontrivial_importance = (importance_share > 0.05) or (drop_val > 1.0)
        
        # Log feature importance details
        logger.info(f"Feature '{feat}': SHAP share = {importance_share * 100:.2f}%, Retrain drop = {drop_val:.2f}%")
        
        known_flag = False
        s3_score = 0.0
        if not known:
            # If not known at prediction time, we score its severity based on importance share
            if has_nontrivial_importance:
                known_flag = True
                s3_score = 70.0 + min(30.0, (importance_share / 0.20) * 30.0)
            else:
                s3_score = (importance_share / 0.05) * 50.0
                
        # Fuzzy-OR Score Aggregation:
        # Combining independent signals using probability-like addition:
        # R = 1 - (1 - S1) * (1 - S2) * (1 - S3)
        # This keeps the final risk score scaled [0, 100], and compounds multiple mild threats.
        risk_score = 100.0 * (1.0 - (1.0 - s1_score / 100.0) * (1.0 - s2_score / 100.0) * (1.0 - s3_score / 100.0))
        
        results.append({
            "feature_name": feat,
            "drop_pct": float(drop_val),
            "shap_ratio": float(feat_ratio) if is_top else 0.0,
            "known_flag": known_flag,
            "risk_score": round(float(risk_score), 2),
            "s1_score": round(float(s1_score), 2),
            "s2_score": round(float(s2_score), 2),
            "s3_score": round(float(s3_score), 2),
            "shap_value": float(shap_importances[feat])
        })
        
    # Sort results with highest risk scores first
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results
