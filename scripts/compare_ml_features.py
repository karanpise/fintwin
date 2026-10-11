
import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"
OUTPUT_PATH = ROOT / "ml" / "metrics" / "feature_comparison.json"

TARGET = "financial_risk"
RANDOM_STATE = 42
TEST_SIZE = 0.20

# Diagnostic baseline only. Do not use this model for deployment.
SCORE_ONLY_FEATURES = ["risk_score"]

# Core financial inputs, excluding score-derived indicators and outputs.
CORE_FEATURES = [
    "age",
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
    "monthly_savings",
    "total_savings",
    "emergency_fund",
    "investments",
    "total_debt",
    "dependents",
    "income_stability_score",
]

EXCLUDED_FROM_FULL_MODEL = {
    "customer_id",
    "risk_score",
    "recommended_intervention",
    "savings_rate_pct",
    "debt_to_income_pct",
    "emergency_fund_months",
    TARGET,
}


def build_pipeline(X):
    numeric_features = X.select_dtypes(
        include=["number"]
    ).columns.tolist()

    categorical_features = X.select_dtypes(
        exclude=["number"]
    ).columns.tolist()

    transformers = []

    if numeric_features:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])

        transformers.append(
            ("numeric", numeric_pipeline, numeric_features)
        )

    if categorical_features:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ])

        transformers.append(
            ("categorical", categorical_pipeline, categorical_features)
        )

    preprocessing = ColumnTransformer(transformers)

    return Pipeline([
        ("preprocessing", preprocessing),
        (
            "model",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            ),
        ),
    ])


def evaluate_model(name, X, y, X_train_index, X_test_index,
                   y_train, y_test, diagnostic=False):
    X_train = X.loc[X_train_index]
    X_test = X.loc[X_test_index]

    pipeline = build_pipeline(X_train)
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)

    result = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y_test, predictions)
        ),
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
        "features": X.columns.tolist(),
        "diagnostic_only": diagnostic,
    }

    print(f"\n===== {name} =====")
    print(f"Feature count: {len(X.columns)}")
    print(f"Accuracy: {result['accuracy']:.4f}")
    print(f"Balanced accuracy: {result['balanced_accuracy']:.4f}")
    print(f"Macro F1: {result['macro_f1']:.4f}")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    return result


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH.resolve()}"
        )

    df = pd.read_csv(DATA_PATH)

    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET}")

    df = df.dropna(subset=[TARGET]).copy()
    y = df[TARGET].astype(str)

    if y.nunique() < 2:
        raise ValueError("At least two target classes are required.")

    full_features = [
        col for col in df.columns
        if col not in EXCLUDED_FROM_FULL_MODEL
    ]

    for feature in SCORE_ONLY_FEATURES + CORE_FEATURES:
        if feature not in df.columns:
            raise ValueError(f"Required feature is missing: {feature}")

    # Use one identical split for all three experiments.
    all_indices = df.index

    train_indices, test_indices = train_test_split(
        all_indices,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    y_train = y.loc[train_indices]
    y_test = y.loc[test_indices]

    experiments = {
        "risk_score_only_diagnostic": (
            df[SCORE_ONLY_FEATURES],
            True,
        ),
        "core_financial_features": (
            df[CORE_FEATURES],
            False,
        ),
        "full_feature_model": (
            df[full_features],
            False,
        ),
    }

    results = {}

    print("=" * 65)
    print("FINTWIN — CONTROLLED FEATURE COMPARISON")
    print("=" * 65)
    print(f"Dataset rows: {len(df)}")
    print(f"Training rows: {len(train_indices)}")
    print(f"Test rows: {len(test_indices)}")
    print(f"Random state: {RANDOM_STATE}")
    print("\nTarget distribution:")
    print(y.value_counts().to_dict())

    for name, (X, diagnostic) in experiments.items():
        results[name] = evaluate_model(
            name=name,
            X=X,
            y=y,
            X_train_index=train_indices,
            X_test_index=test_indices,
            y_train=y_train,
            y_test=y_test,
            diagnostic=diagnostic,
        )

    report = {
        "dataset": DATA_PATH.name,
        "rows_used": int(len(df)),
        "train_rows": int(len(train_indices)),
        "test_rows": int(len(test_indices)),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "target_distribution": {
            str(k): int(v) for k, v in y.value_counts().items()
        },
        "experiments": results,
        "interpretation_notes": [
            "All experiments use the same stratified train/test split.",
            "The risk-score-only experiment is diagnostic, not deployable.",
            "All metrics measure prediction of synthetic labels.",
            "Feature comparisons do not establish real-world validity.",
            "Core and full feature models use the same LogisticRegression setup.",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\n===== COMPARISON SUMMARY =====")

    for name, result in results.items():
        print(
            f"{name}: "
            f"accuracy={result['accuracy']:.4f}, "
            f"macro_f1={result['macro_f1']:.4f}, "
            f"balanced_accuracy={result['balanced_accuracy']:.4f}"
        )

    print(f"\nReport saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
