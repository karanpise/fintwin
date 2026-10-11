
from pathlib import Path
import json

import pandas as pd
from ml.inference.predict import load_model

# Go up from scripts/ to the project root.
root = Path(__file__).resolve().parents[1]

dataset_path = (
    root / "ml" / "data" / "raw" / "financial_risk_dataset.csv"
)

if not dataset_path.exists():
    raise FileNotFoundError(f"Dataset not found: {dataset_path}")

df = pd.read_csv(dataset_path)

model = load_model()
features = list(model.feature_names_in_)

# Select only the model's expected input features.
row = df[features].iloc[0]
sample = {
    key: value if pd.notna(value) else None
    for key, value in row.to_dict().items()
}

print(json.dumps({"features": sample}, indent=2, default=str))
