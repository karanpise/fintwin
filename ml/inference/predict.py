
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "ml" / "artifacts" / "risk_model.joblib"


@lru_cache(maxsize=1)
def load_model():
    """Load the trained model once and cache it."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}. "
            "Run python -m ml.training.train first."
        )

    return joblib.load(MODEL_PATH)


def predict_financial_risk(customer_data: dict) -> dict:
    """
    Predict the financial-risk label using the trained ML pipeline.

    Input keys must match the feature columns used during training.

    Note:
        The model was trained on synthetic data. Predictions are
        experimental and are not validated for real-world decisions.
    """
    model = load_model()

    if not isinstance(customer_data, dict):
        raise TypeError("customer_data must be a dictionary.")

    input_df = pd.DataFrame([customer_data])

    # Validate feature compatibility with the trained model.
    expected_features = list(model.feature_names_in_)

    missing = [
        column
        for column in expected_features
        if column not in input_df.columns
    ]
    extra = [
        column
        for column in input_df.columns
        if column not in expected_features
    ]

    if missing:
        raise ValueError(f"Missing required features: {missing}")

    if extra:
        raise ValueError(f"Unexpected features: {extra}")

    # Preserve feature order and represent optional missing values as NaN
    # so the trained pipeline can apply its configured imputers.
    input_df = input_df[expected_features]
    input_df = input_df.replace({None: float("nan")})

    # Predict the risk category.
    prediction = str(model.predict(input_df)[0])

    # Identify the actual classifier in the pipeline.
    classifier = getattr(model, "named_steps", {}).get("model")

    model_names = {
        "LogisticRegression": "logistic_regression",
        "RandomForestClassifier": "random_forest",
    }

    if classifier is not None:
        classifier_type = type(classifier).__name__
        model_name = model_names.get(
            classifier_type,
            classifier_type.lower(),
        )
    else:
        model_name = type(model).__name__.lower()

    result = {
        "predicted_risk": prediction,
        "model": model_name,
        "status": "experimental",
        "disclaimer": (
            "This model was trained on synthetic data. Its prediction "
            "is not validated for real-world financial decisions."
        ),
    }

    # Include class probabilities when supported by the model.
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(input_df)[0]
        classes = model.classes_

        result["class_probabilities"] = {
            str(label): round(float(probability), 4)
            for label, probability in zip(classes, probabilities)
        }

    return result
