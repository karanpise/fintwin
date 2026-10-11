
from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
import joblib

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

    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    model = joblib.load(MODEL_PATH)
    baseline = DummyClassifier(strategy="most_frequent")

    scoring = {
        "accuracy": "accuracy",
        "macro_f1": "f1_macro",
    }

    for name, estimator in [
        ("Logistic Regression pipeline", model),
        ("Most-frequent baseline", baseline),
    ]:
        results = cross_validate(
            estimator,
            X,
            y,
            cv=cv,
            scoring=scoring,
            n_jobs=-1,
            return_train_score=False,
        )

        print(f"\n=== {name} ===")
        for metric in scoring:
            scores = results[f"test_{metric}"]
            print(
                f"{metric}: "
                f"mean={scores.mean():.4f}, "
                f"std={scores.std():.4f}, "
                f"folds={[round(float(s), 4) for s in scores]}"
            )


if __name__ == "__main__":
    main()

