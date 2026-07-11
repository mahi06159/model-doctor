import os
import pandas as pd
import numpy as np
import joblib
from sklearn.tree import DecisionTreeClassifier


def generate_leaky_data(n_samples: int = 200, random_state: int = 42):
    """
    Generates synthetic leaky dataset:
    - target: binary classification labels (0 or 1)
    - leaky_feature: derived directly from target (direct correlation/leakage)
    - normal_feature: standard feature with weaker relationship to target
    - random_noise: pure gaussian noise
    """
    np.random.seed(random_state)
    
    # 1. Target column
    target = np.random.randint(0, 2, size=n_samples)
    
    # 2. Leaky feature (direct copy of target, extremely high leak)
    leaky_feature = target.copy()
    
    # 3. Normal feature (moderate relationship to target)
    normal_feature = target * 2.0 + np.random.normal(0, 1.5, size=n_samples)
    
    # 4. Noise feature (random noise)
    noise_feature = np.random.normal(0, 1.0, size=n_samples)
    
    # Build DataFrame
    df = pd.DataFrame({
        "leaky_feature": leaky_feature,
        "normal_feature": normal_feature,
        "noise_feature": noise_feature,
        "target": target
    })
    
    # Train a DecisionTreeClassifier model on the dataset
    X = df.drop(columns=["target"])
    y = df["target"]
    
    model = DecisionTreeClassifier(max_depth=3, random_state=random_state)
    model.fit(X, y)
    
    return df, model


def write_fixtures(output_dir: str):
    """
    Generates data/model files and saves them to the specified directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    df, model = generate_leaky_data()
    
    csv_path = os.path.join(output_dir, "leaky_dataset.csv")
    model_path = os.path.join(output_dir, "leaky_model.joblib")
    
    df.to_csv(csv_path, index=False)
    joblib.dump(model, model_path)
    
    print(f"Fixtures written to {output_dir}")
    return csv_path, model_path


if __name__ == "__main__":
    # If run directly, write to a local fixtures directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    write_fixtures(base_dir)
