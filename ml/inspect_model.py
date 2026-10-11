
from pathlib import Path

import joblib

MODEL_PATH = Path("ml/artifacts/risk_model.joblib")

LEAKAGE_PRONE_COLUMNS = {
    "financial_risk",
    "risk_score",
    "recommended_intervention",
    "savings_rate_pct",
    "debt_to_income_pct",
    "emergency_fund_months",
}


def inspect_model():
    print("=" * 65)
    print("FINTWIN — FINAL MODEL INSPECTION")
    print("=" * 65)

    # 1. Load saved model
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH.resolve()}"
        )

    model = joblib.load(MODEL_PATH)

    print(f"\nModel path: {MODEL_PATH.resolve()}")
    print(f"Model type: {type(model).__name__}")

    # 2. Inspect model features
    features = getattr(model, "feature_names_in_", None)

    if features is not None:
        feature_names = list(features)
        print(f"\nNumber of input features: {len(feature_names)}")

        for feature in feature_names:
            print(f"  - {feature}")

        found_leakage = set(feature_names) & LEAKAGE_PRONE_COLUMNS

        print("\nPotential leakage-prone input columns:")
        if found_leakage:
            for column in sorted(found_leakage):
                print(f"  WARNING: {column}")
        else:
            print("  None of the configured columns are model inputs.")
    else:
        feature_names = []
        print("\nFeature names are not available directly on the model.")

    # 3. Inspect pipeline
    named_steps = getattr(model, "named_steps", None)

    if not named_steps:
        print("\nModel is not a directly accessible sklearn Pipeline.")
        print("Inspection cannot continue.")
        return

    print("\nPipeline steps:")
    for step_name, step in named_steps.items():
        print(f"  {step_name}: {type(step).__name__}")

    # 4. Inspect ColumnTransformer
    preprocessing = named_steps.get("preprocessing")

    if preprocessing is None:
        print("\nNo step named 'preprocessing' was found.")
        return

    print("\nPREPROCESSING CONFIGURATION")
    print("-" * 65)

    for name, transformer, columns in preprocessing.transformers_:
        if isinstance(columns, str):
            column_list = [columns]
        else:
            try:
                column_list = list(columns)
            except TypeError:
                column_list = [columns]

        print(f"\nTransformer: {name}")
        print(f"Columns: {column_list}")

        if transformer == "drop":
            print("  Configuration: columns dropped")
            continue

        if transformer == "passthrough":
            print("  Configuration: passed through unchanged")
            continue

        steps = getattr(transformer, "named_steps", None)

        if steps:
            components = steps.items()
        else:
            components = [("transformer", transformer)]

        for component_name, component in components:
            print(
                f"\n  Component '{component_name}': "
                f"{type(component).__name__}"
            )

            # Missing-value imputation
            if hasattr(component, "strategy"):
                print(
                    f"    Imputation strategy: "
                    f"{component.strategy}"
                )

            if hasattr(component, "statistics_"):
                print(
                    f"    Learned imputation values: "
                    f"{component.statistics_}"
                )

            # Scaling
            if hasattr(component, "mean_") and hasattr(component, "scale_"):
                print(f"    Scaling means: {component.mean_}")
                print(f"    Scaling factors: {component.scale_}")

            # Categorical encoding
            if hasattr(component, "handle_unknown"):
                print(
                    f"    Unknown-category handling: "
                    f"{component.handle_unknown}"
                )

            if hasattr(component, "categories_"):
                print("    Learned categories:")
                for index, categories in enumerate(
                    component.categories_
                ):
                    print(f"      Feature {index}: {list(categories)}")

    # 5. Inspect classifier
    classifier = named_steps.get("model")

    print("\nCLASSIFIER")
    print("-" * 65)

    if classifier is not None:
        print(f"Type: {type(classifier).__name__}")

        if hasattr(classifier, "classes_"):
            print(f"Classes: {list(classifier.classes_)}")

        if hasattr(classifier, "n_features_in_"):
            print(f"Features received: {classifier.n_features_in_}")

    print("\n" + "=" * 65)
    print("MODEL INSPECTION COMPLETED")
    print("=" * 65)
    print(
        "Note: configuration inspection alone does not prove "
        "real-world model reliability or absence of indirect leakage."
    )


if __name__ == "__main__":
    inspect_model()
