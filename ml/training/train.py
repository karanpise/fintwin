
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"
ARTIFACT_DIR = ROOT / "ml" / "artifacts"
METRICS_DIR = ROOT / "ml" / "metrics"

TARGET = "financial_risk"

# Exclude identifiers, target-derived outputs, and derived ratios
# to reduce circular learning from the synthetic label-generation rules.
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
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)

    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' is missing.")

    df = df.dropna(subset=[TARGET]).copy()

    X = df.drop(
        columns=[c for c in EXCLUDED_COLUMNS if c in df.columns]
    )
    y = df[TARGET].astype(str)

    if y.nunique() < 2:
        raise ValueError("At least two target classes are required.")

    numeric_features = X.select_dtypes(
        include=["number"]
    ).columns.tolist()

    categorical_features = X.select_dtypes(
        exclude=["number"]
    ).columns.tolist()

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessing = ColumnTransformer([
        ("numeric", numeric_pipeline, numeric_features),
        ("categorical", categorical_pipeline, categorical_features),
    ])

    models = {
        "logistic_regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    }

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    results = {}
    trained_pipelines = {}

    for name, model in models.items():
        pipeline = Pipeline([
            ("preprocessing", preprocessing),
            ("model", model),
        ])

        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        results[name] = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "macro_f1": float(
                f1_score(y_test, predictions, average="macro")
            ),
            "classification_report": classification_report(
                y_test,
                predictions,
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix": confusion_matrix(
                y_test,
                predictions,
                labels=sorted(y.unique()),
            ).tolist(),
        }

        trained_pipelines[name] = pipeline

        print(f"\n===== {name.upper()} =====")
        print(f"Accuracy: {results[name]['accuracy']:.4f}")
        print(f"Macro F1: {results[name]['macro_f1']:.4f}")
        print(classification_report(
            y_test,
            predictions,
            zero_division=0,
        ))

    best_name = max(
        results,
        key=lambda name: results[name]["macro_f1"],
    )

    best_model = trained_pipelines[best_name]

    joblib.dump(
        best_model,
        ARTIFACT_DIR / "risk_model.joblib",
    )

    evaluation = {
        "dataset": DATA_PATH.name,
        "rows_used": int(len(df)),
        "feature_columns": X.columns.tolist(),
        "excluded_columns": [
            c for c in EXCLUDED_COLUMNS if c in df.columns
        ],
        "target_distribution": {
            str(k): int(v)
            for k, v in y.value_counts().items()
        },
        "test_size": 0.20,
        "random_state": 42,
        "selection_metric": "macro_f1",
        "best_model": best_name,
        "models": results,
        "limitations": [
            "The target labels are synthetic.",
            "Held-out performance does not establish real-world predictive validity.",
            "Audit the label-generation rules and feature availability before deployment.",
        ],
    }

    with open(
        METRICS_DIR / "evaluation.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(evaluation, file, indent=2)

    print(f"\nBest model: {best_name}")
    print(f"Saved model: {ARTIFACT_DIR / 'risk_model.joblib'}")
    print(f"Saved metrics: {METRICS_DIR / 'evaluation.json'}")


if __name__ == "__main__":
    main()
