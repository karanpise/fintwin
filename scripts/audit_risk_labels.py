
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"

def main():
    df = pd.read_csv(DATA_PATH)

    required = {"financial_risk", "risk_score"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print("\n=== Risk score by risk category ===")
    print(
        df.groupby("financial_risk")["risk_score"]
        .agg(["count", "min", "max", "mean", "std"])
        .round(2)
    )

    print("\n=== Risk category distribution ===")
    print(df["financial_risk"].value_counts(dropna=False))

    print("\n=== Risk category by score intervals ===")
    bins = [-1, 25, 40, 50, 60, 75, 100, float("inf")]
    labels = [
        "0-25", "25-40", "40-50", "50-60",
        "60-75", "75-100", "Above 100"
    ]

    score_band = pd.cut(
        df["risk_score"],
        bins=bins,
        labels=labels,
        right=False
    )

    print(pd.crosstab(score_band, df["financial_risk"]))

    print("\n=== Potential leakage columns ===")
    for col in [
        "customer_id",
        "risk_score",
        "recommended_intervention",
    ]:
        if col in df.columns:
            print(f"- {col}: investigate before using as a feature")

    
    print("\n=== Recommended intervention by risk category ===")
    if "recommended_intervention" in df.columns:
        print(
            pd.crosstab(
                df["recommended_intervention"],
                df["financial_risk"],
                normalize="index",
            ).round(3)
        )

    print("\n=== Financial indicators by risk category ===")
    indicators = [
        "monthly_income",
        "monthly_expenses",
        "monthly_emi",
        "monthly_savings",
        "total_savings",
        "emergency_fund",
        "investments",
        "total_debt",
        "income_stability_score",
        "savings_rate_pct",
        "debt_to_income_pct",
        "emergency_fund_months",
    ]

    for col in indicators:
        if col in df.columns:
            print(f"\n--- {col} ---")
            print(
                df.groupby("financial_risk")[col]
                .agg(["mean", "median", "min", "max"])
                .round(2)
            )


    print("\nAudit complete. Interpret results before training.")

if __name__ == "__main__":
    main()
