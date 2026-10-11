
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"
)


def main():
    df = pd.read_csv(DATA_PATH).dropna(
        subset=["risk_score", "financial_risk"]
    )

    X = df[["risk_score"]]
    y = df["financial_risk"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = DecisionTreeClassifier(
        max_depth=5,
        min_samples_leaf=20,
        random_state=42,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("=== Risk score-only experiment ===")
    print(f"Test accuracy: {accuracy_score(y_test, predictions):.4f}")

    print("\nPredictions by score band:")
    result = pd.DataFrame({
        "risk_score": X_test["risk_score"],
        "actual": y_test,
        "predicted": predictions,
    })

    result["score_band"] = pd.cut(
        result["risk_score"],
        bins=[-float("inf"), 25, 40, 50, 60, 75, float("inf")],
        labels=["Below 25", "25–40", "40–50", "50–60", "60–75", "75+"],
        right=False,
    )

    print(pd.crosstab(
        result["score_band"],
        result["actual"],
        normalize="index",
    ).round(3))

    print(
        "\nInterpretation: high score-only accuracy suggests that "
        "risk_score captures much of the label structure. It does not "
        "by itself prove target leakage or real-world validity."
    )


if __name__ == "__main__":
    main()
