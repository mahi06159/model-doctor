from typing import Any, Dict, List

# 1. Titanic Target Leakage Job Results
TITANIC_LEAKAGE_RESULTS: Dict[str, Any] = {
    "total_rows": 891,
    "total_columns": 12,
    "column_types": {
        "PassengerId": "Integer",
        "Survived": "Integer",
        "Pclass": "Integer",
        "Name": "Categorical",
        "Sex": "Categorical",
        "Age": "Float",
        "SibSp": "Integer",
        "Parch": "Integer",
        "Ticket": "Categorical",
        "Fare": "Float",
        "Cabin": "Categorical",
        "Embarked": "Categorical",
        "PassengerId_plus_Survived": "Integer"
    },
    "missing_data": {
        "PassengerId": {"count": 0, "percentage": 0.0},
        "Pclass": {"count": 0, "percentage": 0.0},
        "Name": {"count": 0, "percentage": 0.0},
        "Sex": {"count": 0, "percentage": 0.0},
        "Age": {"count": 177, "percentage": 19.87},
        "SibSp": {"count": 0, "percentage": 0.0},
        "Parch": {"count": 0, "percentage": 0.0},
        "Ticket": {"count": 0, "percentage": 0.0},
        "Fare": {"count": 0, "percentage": 0.0},
        "Cabin": {"count": 687, "percentage": 77.1},
        "Embarked": {"count": 2, "percentage": 0.22},
        "PassengerId_plus_Survived": {"count": 0, "percentage": 0.0}
    },
    "duplicates": {
        "count": 0,
        "percentage": 0.0
    },
    "outliers": {
        "Age": {"count": 11, "percentage": 1.24},
        "Fare": {"count": 116, "percentage": 13.02}
    },
    "calibration": {
        "supported": True,
        "brier_score": 0.184,
        "reliability_curve": [
            {"bin": 1, "pred_prob": 0.05, "actual_prob": 0.08},
            {"bin": 2, "pred_prob": 0.15, "actual_prob": 0.22},
            {"bin": 3, "pred_prob": 0.25, "actual_prob": 0.29},
            {"bin": 4, "pred_prob": 0.35, "actual_prob": 0.42},
            {"bin": 5, "pred_prob": 0.45, "actual_prob": 0.51},
            {"bin": 6, "pred_prob": 0.55, "actual_prob": 0.58},
            {"bin": 7, "pred_prob": 0.65, "actual_prob": 0.72},
            {"bin": 8, "pred_prob": 0.75, "actual_prob": 0.79},
            {"bin": 9, "pred_prob": 0.85, "actual_prob": 0.82},
            {"bin": 10, "pred_prob": 0.95, "actual_prob": 0.88}
        ]
    },
    "overfitting": {
        "supported": True,
        "metric": "accuracy",
        "performance_gap": 0.142,
        "cv_variance": 0.018,
        "learning_curve": [
            {"train_size": 100, "train_score": 0.98, "test_score": 0.72},
            {"train_size": 200, "train_score": 0.97, "test_score": 0.76},
            {"train_size": 400, "train_score": 0.96, "test_score": 0.79},
            {"train_size": 600, "train_score": 0.95, "test_score": 0.80},
            {"train_size": 800, "train_score": 0.94, "test_score": 0.81}
        ]
    },
    "feature_dominance": {
        "supported": True,
        "ranking": [
            {"feature_name": "PassengerId_plus_Survived", "importance": 0.742},
            {"feature_name": "Sex", "importance": 0.185},
            {"feature_name": "Pclass", "importance": 0.042},
            {"feature_name": "Fare", "importance": 0.021},
            {"feature_name": "Age", "importance": 0.010}
        ]
    },
    "fairness": {
        "supported": True,
        "demographic_parity_difference": 0.0,
        "equalized_odds_difference": 0.0,
        "group_metrics": {}
    },
    "health_score": {
        "score": 38.5,
        "grade": "F",
        "components": {
            "leakage": {"penalty": 100.0, "weight": 0.30, "weighted_penalty": 30.0},
            "calibration": {"penalty": 73.6, "weight": 0.15, "weighted_penalty": 11.04},
            "overfitting": {"penalty": 28.4, "weight": 0.20, "weighted_penalty": 5.68},
            "fairness": {"penalty": 0.0, "weight": 0.20, "weighted_penalty": 0.0, "note": "No protected attribute provided."},
            "data_quality": {"penalty": 32.2, "weight": 0.15, "weighted_penalty": 4.83}
        }
    }
}

# 2. Well-Calibrated Classifier Job Results
CALIBRATED_CLASSIFIER_RESULTS: Dict[str, Any] = {
    "total_rows": 10000,
    "total_columns": 21,
    "column_types": {f"feat_{i}": "Float" for i in range(20)},
    "missing_data": {f"feat_{i}": {"count": 0, "percentage": 0.0} for i in range(20)},
    "duplicates": {"count": 0, "percentage": 0.0},
    "outliers": {},
    "calibration": {
        "supported": True,
        "brier_score": 0.012,
        "reliability_curve": [
            {"bin": 1, "pred_prob": 0.05, "actual_prob": 0.05},
            {"bin": 2, "pred_prob": 0.15, "actual_prob": 0.14},
            {"bin": 3, "pred_prob": 0.25, "actual_prob": 0.25},
            {"bin": 4, "pred_prob": 0.35, "actual_prob": 0.36},
            {"bin": 5, "pred_prob": 0.45, "actual_prob": 0.44},
            {"bin": 6, "pred_prob": 0.55, "actual_prob": 0.55},
            {"bin": 7, "pred_prob": 0.65, "actual_prob": 0.66},
            {"bin": 8, "pred_prob": 0.75, "actual_prob": 0.74},
            {"bin": 9, "pred_prob": 0.85, "actual_prob": 0.85},
            {"bin": 10, "pred_prob": 0.95, "actual_prob": 0.96}
        ]
    },
    "overfitting": {
        "supported": True,
        "metric": "accuracy",
        "performance_gap": 0.008,
        "cv_variance": 0.002,
        "learning_curve": [
            {"train_size": 1000, "train_score": 0.932, "test_score": 0.921},
            {"train_size": 3000, "train_score": 0.930, "test_score": 0.923},
            {"train_size": 5000, "train_score": 0.929, "test_score": 0.925},
            {"train_size": 8000, "train_score": 0.928, "test_score": 0.926},
            {"train_size": 10000, "train_score": 0.927, "test_score": 0.926}
        ]
    },
    "feature_dominance": {
        "supported": True,
        "ranking": [
            {"feature_name": "feat_4", "importance": 0.185},
            {"feature_name": "feat_12", "importance": 0.142},
            {"feature_name": "feat_7", "importance": 0.111},
            {"feature_name": "feat_18", "importance": 0.095},
            {"feature_name": "feat_1", "importance": 0.082}
        ]
    },
    "fairness": {
        "supported": True,
        "demographic_parity_difference": 0.0,
        "equalized_odds_difference": 0.0,
        "group_metrics": {}
    },
    "health_score": {
        "score": 97.2,
        "grade": "A",
        "components": {
            "leakage": {"penalty": 4.5, "weight": 0.30, "weighted_penalty": 1.35},
            "calibration": {"penalty": 4.8, "weight": 0.15, "weighted_penalty": 0.72},
            "overfitting": {"penalty": 1.6, "weight": 0.20, "weighted_penalty": 0.32},
            "fairness": {"penalty": 0.0, "weight": 0.20, "weighted_penalty": 0.0},
            "data_quality": {"penalty": 2.7, "weight": 0.15, "weighted_penalty": 0.41}
        }
    }
}

# 3. Biased Credit Loan Approval Job Results
BIASED_CREDIT_RESULTS: Dict[str, Any] = {
    "total_rows": 5000,
    "total_columns": 15,
    "column_types": {
        "Age": "Integer",
        "Income": "Float",
        "CreditScore": "Integer",
        "Gender": "Categorical",
        "LoanAmount": "Float",
        "Approved": "Integer"
    },
    "missing_data": {
        "Age": {"count": 0, "percentage": 0.0},
        "Income": {"count": 0, "percentage": 0.0},
        "CreditScore": {"count": 0, "percentage": 0.0},
        "Gender": {"count": 0, "percentage": 0.0},
        "LoanAmount": {"count": 25, "percentage": 0.5},
        "Approved": {"count": 0, "percentage": 0.0}
    },
    "duplicates": {"count": 0, "percentage": 0.0},
    "outliers": {
        "Income": {"count": 12, "percentage": 0.24}
    },
    "calibration": {
        "supported": True,
        "brier_score": 0.082,
        "reliability_curve": [
            {"bin": 1, "pred_prob": 0.05, "actual_prob": 0.06},
            {"bin": 2, "pred_prob": 0.15, "actual_prob": 0.13},
            {"bin": 3, "pred_prob": 0.25, "actual_prob": 0.28},
            {"bin": 4, "pred_prob": 0.35, "actual_prob": 0.32},
            {"bin": 5, "pred_prob": 0.45, "actual_prob": 0.49},
            {"bin": 6, "pred_prob": 0.55, "actual_prob": 0.53},
            {"bin": 7, "pred_prob": 0.65, "actual_prob": 0.68},
            {"bin": 8, "pred_prob": 0.75, "actual_prob": 0.72},
            {"bin": 9, "pred_prob": 0.85, "actual_prob": 0.89},
            {"bin": 10, "pred_prob": 0.95, "actual_prob": 0.94}
        ]
    },
    "overfitting": {
        "supported": True,
        "metric": "accuracy",
        "performance_gap": 0.035,
        "cv_variance": 0.005,
        "learning_curve": [
            {"train_size": 500, "train_score": 0.89, "test_score": 0.82},
            {"train_size": 1500, "train_score": 0.88, "test_score": 0.84},
            {"train_size": 3000, "train_score": 0.87, "test_score": 0.85},
            {"train_size": 5000, "train_score": 0.86, "test_score": 0.85}
        ]
    },
    "feature_dominance": {
        "supported": True,
        "ranking": [
            {"feature_name": "CreditScore", "importance": 0.421},
            {"feature_name": "Income", "importance": 0.295},
            {"feature_name": "Gender", "importance": 0.185},
            {"feature_name": "Age", "importance": 0.072},
            {"feature_name": "LoanAmount", "importance": 0.027}
        ]
    },
    "fairness": {
        "supported": True,
        "demographic_parity_difference": 0.450,
        "equalized_odds_difference": 0.380,
        "group_metrics": {
            "Male": {
                "selection_rate": 0.800,
                "tpr": 0.850,
                "fpr": 0.420,
                "count": 2600
            },
            "Female": {
                "selection_rate": 0.350,
                "tpr": 0.470,
                "fpr": 0.120,
                "count": 2400
            }
        }
    },
    "health_score": {
        "score": 75.8,
        "grade": "B",
        "components": {
            "leakage": {"penalty": 12.0, "weight": 0.30, "weighted_penalty": 3.6},
            "calibration": {"penalty": 32.8, "weight": 0.15, "weighted_penalty": 4.92},
            "overfitting": {"penalty": 7.0, "weight": 0.20, "weighted_penalty": 1.4},
            "fairness": {"penalty": 45.0, "weight": 0.20, "weighted_penalty": 9.0, "note": "Gender bias penalty."},
            "data_quality": {"penalty": 3.5, "weight": 0.15, "weighted_penalty": 0.525}
        }
    }
}

DEMO_JOBS: Dict[str, Dict[str, Any]] = {
    "demo-titanic-leakage": {
        "id": "demo-titanic-leakage",
        "username": "System Demo",
        "target_column": "Survived",
        "protected_attribute": None,
        "status": "COMPLETED",
        "created_at": "2026-07-10T12:00:00Z",
        "results": TITANIC_LEAKAGE_RESULTS,
        "leakage_results": [
            {"feature_name": "PassengerId_plus_Survived", "risk_score": 100.0, "drop_pct": 52.4, "known_flag": True},
            {"feature_name": "Sex", "risk_score": 25.0, "drop_pct": 8.5, "known_flag": False},
            {"feature_name": "Pclass", "risk_score": 10.0, "drop_pct": 2.1, "known_flag": False}
        ]
    },
    "demo-calibrated-classifier": {
        "id": "demo-calibrated-classifier",
        "username": "System Demo",
        "target_column": "Class",
        "protected_attribute": None,
        "status": "COMPLETED",
        "created_at": "2026-07-10T12:05:00Z",
        "results": CALIBRATED_CLASSIFIER_RESULTS,
        "leakage_results": [
            {"feature_name": "feat_4", "risk_score": 4.5, "drop_pct": 0.5, "known_flag": False},
            {"feature_name": "feat_12", "risk_score": 3.0, "drop_pct": 0.2, "known_flag": False}
        ]
    },
    "demo-biased-credit": {
        "id": "demo-biased-credit",
        "username": "System Demo",
        "target_column": "Approved",
        "protected_attribute": "Gender",
        "status": "COMPLETED",
        "created_at": "2026-07-10T12:10:00Z",
        "results": BIASED_CREDIT_RESULTS,
        "leakage_results": [
            {"feature_name": "CreditScore", "risk_score": 12.0, "drop_pct": 3.4, "known_flag": False},
            {"feature_name": "Income", "risk_score": 8.0, "drop_pct": 1.2, "known_flag": False}
        ]
    }
}
