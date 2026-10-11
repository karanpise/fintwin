
from pathlib import Path

import pandas as pd

DATASET_PATH = Path("ml/data/raw/financial_risk_dataset.csv")
TARGET_COLUMN = "financial_risk"


def validate_dataset():
    print("=" * 60)
    print("FINTWIN — DATASET VALIDATION REPORT")
    print("=" * 60)

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH.resolve()}"
        )

    df = pd.read_csv(DATASET_PATH)

    # 1. Dataset dimensions
    print(f"\nRows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    # 2. Duplicate records
    duplicates = int(df.duplicated().sum())
    print(f"\nDuplicate rows: {duplicates}")

    # 3. Missing values
    missing = df.isna().sum()
    missing = missing[missing > 0]

    print("\nMissing values:")
    if missing.empty:
        print("No missing values found.")
    else:
        print(missing.to_string())

    # 4. Target validation
    if TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' is missing."
        )

    if df[TARGET_COLUMN].isna().any():
        raise ValueError("Target column contains missing values.")

    print("\nTarget class distribution:")
    print(df[TARGET_COLUMN].value_counts().to_string())

    print("\nTarget class percentages:")
    print(
        (df[TARGET_COLUMN].value_counts(normalize=True) * 100)
        .round(2)
        .to_string()
    )

    # 5. Data types
    print("\nColumn data types:")
    print(df.dtypes.to_string())

    # 6. Constant columns
    constant_columns = [
        col for col in df.columns
        if df[col].nunique(dropna=False) <= 1
    ]
    print("\nConstant columns:")
    print(constant_columns or "None")

    # 7. Numeric summary
    print("\nNumeric summary:")
    print(df.describe().round(2).to_string())

    # 8. Duplicate identifiers, if present
    if "customer_id" in df.columns:
        duplicate_ids = int(df["customer_id"].duplicated().sum())
        print(f"\nDuplicate customer IDs: {duplicate_ids}")

    print("\n" + "=" * 60)
    print("VALIDATION REPORT COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    validate_dataset()
