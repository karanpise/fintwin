
import os

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

st.set_page_config(
    page_title="FinTwin | ML Risk Prediction",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 ML Risk Prediction")
st.warning(
    "Experimental demonstration: this model was trained on synthetic data. "
    "Its predictions are not validated for real-world financial decisions."
)

token = st.session_state.get("access_token", "")

if not token:
    st.info("Please log in from the main FinTwin page.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

# Load the authenticated user's saved financial profile.
try:
    profile_response = requests.get(
        f"{API_BASE_URL}/me/financial-profile",
        headers=headers,
        timeout=15,
    )

    if profile_response.status_code == 401:
        st.session_state.access_token = ""
        st.warning("Your session expired. Please log in again.")
        st.stop()

    if profile_response.status_code == 404:
        st.info(
            "No saved financial profile was found. "
            "Complete your Financial Profile before predicting risk."
        )
        st.stop()

    profile_response.raise_for_status()
    profile = profile_response.json()

except requests.RequestException as exc:
    st.error(f"Unable to load your financial profile: {exc}")
    st.stop()

# These are the exact 21 model input features.
numeric_features = [
    "age",
    "employment_years",
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
    "expected_salary_growth_pct",
    "expected_expense_inflation_pct",
    "planned_expense_month",
]

categorical_features = [
    "employment_type",
    "insurance",
    "health_insurance",
    "financial_goal",
    "investment_experience",
    "planned_major_expense",
]

required_features = numeric_features + categorical_features

st.subheader("Your saved financial profile")
st.caption(
    "Predictions use the values saved on your Financial Profile page. "
    "Update that page if any information is missing or incorrect."
)

financial_fields = [
    "monthly_income",
    "monthly_expenses",
    "monthly_emi",
    "total_savings",
    "emergency_fund",
    "investments",
    "total_debt",
    "monthly_savings",
]

columns = st.columns(4)

for index, field in enumerate(financial_fields):
    value = profile.get(field)

    if value is None:
        display_value = "Missing"
    else:
        display_value = f"₹{float(value):,.2f}"

    columns[index % 4].metric(
        field.replace("_", " ").title(),
        display_value,
    )

with st.expander("View saved personal and ML details"):
    for field in required_features:
        value = profile.get(field)
        label = field.replace("_", " ").title()

        if value is None:
            st.write(f"**{label}:** Not provided")
        else:
            st.write(f"**{label}:** {value}")

st.divider()

# Never silently substitute zero or invented values for missing inputs.
no_planned_expense = (
    profile.get("planned_major_expense") is None
    and profile.get("planned_expense_month") == 0
)

missing_fields = [
    field
    for field in required_features
    if profile.get(field) is None
    and not (
        no_planned_expense
        and field == "planned_major_expense"
    )
]

if missing_fields:
    st.warning(
        "Your profile is incomplete. Complete these fields before "
        "making a prediction:"
    )

    for field in missing_fields:
        st.write(f"- {field.replace('_', ' ').title()}")

    st.info(
        "Open the Financial Profile page, enter your actual details, "
        "save the profile, and then return here."
    )
    st.stop()

# Validate and convert the saved values to the types expected by the model.
try:
    features = {}

    for field in numeric_features:
        value = float(profile[field])

        if not pd.notna(value) or value in (
            float("inf"),
            float("-inf"),
        ):
            raise ValueError(
                f"{field.replace('_', ' ').title()} must be finite."
            )

        features[field] = value

    integer_fields = {"age", "dependents", "planned_expense_month"}

    for field in integer_fields:
        value = features[field]

        if not value.is_integer():
            raise ValueError(
                f"{field.replace('_', ' ').title()} must be a whole number."
            )

        features[field] = int(value)

    if not 18 <= features["age"] <= 100:
        raise ValueError("Age must be between 18 and 100.")

    if features["employment_years"] < 0:
        raise ValueError("Years of employment cannot be negative.")

    if features["dependents"] < 0:
        raise ValueError("Number of dependents cannot be negative.")

    if not 0 <= features["income_stability_score"] <= 100:
        raise ValueError("Income stability score must be between 0 and 100.")

    planned_category = profile.get("planned_major_expense")
    planned_month = features["planned_expense_month"]

    if planned_category is None:
        if planned_month != 0:
            raise ValueError(
                "Without a planned expense category, the month value must be 0."
            )
    elif not 1 <= planned_month <= 36:
        raise ValueError(
            "A planned expense must be between 1 and 36 months away."
        )

    for field in [
        "monthly_income",
        "monthly_expenses",
        "monthly_emi",
        "monthly_savings",
        "total_savings",
        "emergency_fund",
        "investments",
        "total_debt",
    ]:
        if features[field] < 0:
            raise ValueError(
                f"{field.replace('_', ' ').title()} cannot be negative."
            )

    if features["monthly_savings"] > features["monthly_income"]:
        raise ValueError(
            "Monthly savings cannot exceed monthly income. "
            "Update your Financial Profile if these values are incorrect."
        )

    if features["employment_years"] > features["age"] - 14:
        raise ValueError(
            "Please check the saved age and years of employment."
        )

    for field in categorical_features:
        value = profile[field]

        if field == "planned_major_expense" and no_planned_expense:
            features[field] = None
            continue

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field.replace('_', ' ').title()} must be provided."
            )

        features[field] = value.strip()

    # Ensure no model features are missing.
    if set(features) != set(required_features):
        raise ValueError(
            "The saved profile does not match the expected model inputs. "
            "Please contact the developer."
        )

except (TypeError, ValueError, KeyError) as exc:
    st.error(f"Profile validation failed: {exc}")
    st.info("Correct your details on the Financial Profile page.")
    st.stop()

st.subheader("Ready to predict")
st.success(
    "All 21 required model features are available in your saved profile."
)

if st.button(
    "Predict my financial risk",
    type="primary",
    use_container_width=True,
):
    try:
        with st.spinner("Analyzing your saved financial information..."):
            response = requests.post(
                f"{API_BASE_URL}/ml/predict-risk",
                json={"features": features},
                headers=headers,
                timeout=20,
            )

        if response.status_code == 401:
            st.session_state.access_token = ""
            st.warning("Your session expired. Please log in again.")
            st.stop()

        if response.status_code == 422:
            st.error(
                "The API rejected the model inputs. "
                "Check that your saved profile matches the model's "
                "expected feature values."
            )
            st.code(response.text[:1000])
            st.stop()

        if response.status_code == 503:
            st.error(
                "The ML model is currently unavailable. "
                "Check that the model artifact has been trained and saved."
            )
            st.stop()

        response.raise_for_status()
        result = response.json()

        st.subheader("Prediction result")
        st.metric(
            "Predicted risk category",
            result["predicted_risk"],
        )

        probabilities = result.get("class_probabilities", {})

        if probabilities:
            chart_df = pd.DataFrame.from_dict(
                probabilities,
                orient="index",
                columns=["Probability"],
            )

            chart_df["Probability"] *= 100
            st.bar_chart(chart_df)
            st.caption(
                "These are model-estimated class probabilities, "
                "not guarantees of your future financial outcome."
            )

        st.warning(
            result.get(
                "disclaimer",
                "Experimental model output; not validated for "
                "real-world financial decisions.",
            )
        )

    except requests.RequestException as exc:
        st.error(f"Prediction request failed: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        st.error(f"Unexpected prediction response: {exc}")
