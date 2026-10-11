
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "ml" / "data" / "raw" / "financial_risk_dataset.csv"

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    print("\n--- DATASET OVERVIEW ---")
    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    print("\n--- COLUMN NAMES ---")
    print(df.columns.tolist())

    print("\n--- MISSING VALUES ---")
    print(df.isnull().sum()[df.isnull().sum() > 0])

    print("\n--- DUPLICATE ROWS ---")
    print(df.duplicated().sum())

    if "financial_risk" in df.columns:
        print("\n--- RISK LABEL DISTRIBUTION ---")
        print(df["financial_risk"].value_counts(dropna=False))

    print("\n--- FIRST FIVE ROWS ---")
    print(df.head())

if __name__ == "__main__":
    main()
