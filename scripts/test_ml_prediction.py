
import pandas as pd

from ml.inference.predict import load_model, predict_financial_risk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"


def main():
    df = pd.read_csv(DATA_PATH)

    model = load_model()
    features = list(model.feature_names_in_)

    sample = df[features].iloc[0].to_dict()
    result = predict_financial_risk(sample)

    print("Prediction service test")
    print("=======================")
    print(result)

    assert result["predicted_risk"] in {"Low", "Medium", "High"}
    assert "class_probabilities" in result

    probabilities = result["class_probabilities"]
    assert abs(sum(probabilities.values()) - 1.0) < 0.001

    print("\nPrediction test passed.")


if __name__ == "__main__":
    main()
