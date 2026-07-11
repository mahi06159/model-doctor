import pandas as pd
import numpy as np
from typing import Dict, Any

"""
Data Quality Diagnostics Module
================================

This module performs statistical checks on uploaded datasets.

Tool Tradeoffs and Evaluation:
------------------------------
1. Great Expectations (GE):
   - Pros: Highly robust, declarative assertions, integrates with pipelines, generates beautiful data docs.
   - Cons: Huge config overhead (JSON suites, data contexts), steep learning curve, high performance overhead,
     and complex output JSON structure which is painful to parse programmatically for custom dashboard UI widgets.
2. Pandera:
   - Pros: Lightweight, elegant integration with type hints, fast runtime check, schema enforcement.
   - Cons: Primarily designed for binary validation assertions (raise errors if invalid) rather than extracting
     rich statistical telemetry (outlier indexes, duplicate counts, detailed missing percentages) for visual plotting.
3. Custom Pandas Validation (Chosen):
   - Pros: Maximum speed, zero extra configuration overhead, runs completely in-memory, and yields precise JSON
     structures specifically tailored for modern React dashboards (like Recharts visual mappings).
"""


def analyze_data_quality(df: pd.DataFrame, target_column: str = None) -> Dict[str, Any]:
    """
    Analyze dataset quality including missing values, duplicate rows, inferred data types,
    and outliers (using Interquartile Range - IQR) for numerical columns.
    
    Args:
        df: pandas DataFrame to audit.
        target_column: Optional name of the target variable.
        
    Returns:
        A dictionary containing formatted data quality diagnostics.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    
    if total_rows == 0:
        return {
            "total_rows": 0,
            "total_columns": total_cols,
            "missing_data": {},
            "duplicates": {"count": 0, "percentage": 0.0},
            "outliers": {},
            "column_types": {}
        }

    # 1. Duplicate rows check
    duplicate_count = int(df.duplicated().sum())
    duplicate_percentage = float((duplicate_count / total_rows) * 100)

    # 2. Missing data check
    missing_info = {}
    missing_by_col = df.isnull().sum()
    for col in df.columns:
        m_count = int(missing_by_col[col])
        m_pct = float((m_count / total_rows) * 100)
        missing_info[col] = {
            "count": m_count,
            "percentage": round(m_pct, 2)
        }

    # 3. Column Data Types and Basic Statistics
    column_types = {}
    for col in df.columns:
        col_dtype = str(df[col].dtype)
        # Simplify data types for UI consumption
        if "int" in col_dtype:
            inferred_type = "Integer"
        elif "float" in col_dtype:
            series_clean = df[col].dropna()
            if not series_clean.empty and series_clean.apply(float.is_integer).all():
                inferred_type = "Integer"
            else:
                inferred_type = "Float"
        elif "bool" in col_dtype:
            inferred_type = "Boolean"
        elif "datetime" in col_dtype:
            inferred_type = "Datetime"
        else:
            inferred_type = "Categorical/Text"
            
        column_types[col] = inferred_type

    # 4. Numerical Outliers using IQR
    outlier_info = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        # Skip if column is entirely missing
        if df[col].isnull().all():
            continue
            
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Count values outside bounds
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col]
        outlier_count = int(outliers.count())
        outlier_pct = float((outlier_count / total_rows) * 100)
        
        outlier_info[col] = {
            "count": outlier_count,
            "percentage": round(outlier_pct, 2),
            "lower_bound": float(lower_bound) if not np.isnan(lower_bound) else None,
            "upper_bound": float(upper_bound) if not np.isnan(upper_bound) else None,
            "q1": float(q1) if not np.isnan(q1) else None,
            "q3": float(q3) if not np.isnan(q3) else None,
        }

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "target_column": target_column,
        "duplicates": {
            "count": duplicate_count,
            "percentage": round(duplicate_percentage, 2)
        },
        "missing_data": missing_info,
        "column_types": column_types,
        "outliers": outlier_info
    }
