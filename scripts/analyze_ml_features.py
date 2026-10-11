
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"
MODEL_PATH = ROOT / "ml" / "artifacts" / "risk_model.joblib"

TARGET = "financial_risk"
EXCLUDED_COLUMNS = [
    "customer_id",
    "risk_score",
    "recommended_intervention",
    "savings_rate_pct",
    "debt_to_income_pct",
    "emergency_fund_months",
    TARGET,
]


def main():
    df = pd.read_csv(DATA_PATH).dropna(subset=[TARGET]).copy()

    X = df.drop(
        columns=[c for c in EXCLUDED_COLUMNS if c in df.columns]
    )
    y = df[TARGET].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = joblib.load(MODEL_PATH)
    predictions = model.predict(X_test)

    print(f"Test accuracy: {accuracy_score(y_test, predictions):.4f}")

    result = permutation_importance(
        model,
        X_test,
        y_test,
        scoring="f1_macro",
        n_repeats=5,
        random_state=42,
        n_jobs=-1,
    )

    importance = pd.DataFrame({
        "feature": X_test.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    print("\n=== Top 15 features by permutation importance ===")
    print(importance.head(15).round(4).to_string(index=False))

    print("\nPositive importance means shuffling the feature")
    print("reduced macro F1 on this test set.")
    print("This measures predictive dependence, not causation.")


if __name__ == "__main__":
    main()
