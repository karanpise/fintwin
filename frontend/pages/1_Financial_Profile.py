
import os

import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
)

st.set_page_config(
    page_title="FinTwin | Financial Profile",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Your Financial Profile")
st.caption(
    "Save your financial details once to power FinTwin's "
    "risk prediction and financial simulations."
)

token = st.session_state.get("access_token", "")

if not token:
    st.warning("Please log in from the main FinTwin page first.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

# Load the user's existing profile.
try:
    response = requests.get(
        f"{API_BASE_URL}/me/financial-profile",
        headers=headers,
        timeout=10,
    )

    if response.status_code == 401:
        st.session_state.access_token = ""
        st.warning("Your session expired. Please log in again.")
        st.stop()

    if response.status_code == 200:
        profile = response.json()
    elif response.status_code == 404:
        profile = {}
    else:
        st.error(f"Unable to load profile: HTTP {response.status_code}")
        st.stop()

except requests.RequestException:
    st.error("Cannot connect to the FinTwin API.")
    st.stop()


def amount(field):
    return float(profile.get(field) or 0)


def optional_number(field):
    value = profile.get(field)
    return None if value is None else float(value)


def balance_status(field):
    # Old stored amounts are intentionally not assumed to be confirmed.
    return bool(profile.get(f"{field}_reported", False))


def select_index(options, field):
    current = profile.get(field)
    return options.index(current) if current in options else 0


employment_options = [
    "Business",
    "Contract",
    "Salaried",
    "Self-Employed",
]
yes_no_options = ["No", "Yes"]
goal_options = [
    "Car",
    "Education",
    "Emergency Fund",
    "Home",
    "Retirement",
    "Wealth Creation",
]
experience_options = [
    "Advanced",
    "Beginner",
    "Intermediate",
]
expense_options = [
    "No planned expense",
    "Business",
    "Car",
    "Education",
    "Home",
    "Medical",
    "Travel",
]

with st.form("financial_profile_form"):
    st.header("1. Monthly finances")
    st.caption(
        "Use monthly take-home income after tax. Monthly expenses are "
        "non-EMI living costs; enter loan payments separately as EMI. "
        "Amounts must be non-negative and have at most two decimal places."
    )
    st.info(
        "For each balance below, check the confirmation box only when the "
        "amount is current. An unchecked balance is treated as unknown. "
        "To report zero, leave the amount at ₹0 and check its box."
    )

    col1, col2 = st.columns(2)

    with col1:
        monthly_income = st.number_input(
            "Monthly take-home income (₹)",
            min_value=0.0,
            value=amount("monthly_income"),
            step=1000.0,
        )
        monthly_expenses = st.number_input(
            "Monthly expenses, excluding EMI (₹)",
            min_value=0.0,
            value=amount("monthly_expenses"),
            step=500.0,
            help="Recurring living and other non-loan expenses. Enter all loan repayments in the separate EMI field.",
        )
        monthly_emi = st.number_input(
            "Monthly loan EMI payments (₹)",
            min_value=0.0,
            value=amount("monthly_emi"),
            step=500.0,
        )
        total_debt_reported = st.checkbox(
            "I confirm my outstanding debt balance",
            value=balance_status("total_debt"),
        )
        total_debt = st.number_input(
            "Total outstanding debt (₹)",
            min_value=0.0,
            value=amount("total_debt"),
            step=1000.0,
        )

    with col2:
        total_savings_reported = st.checkbox(
            "I confirm my liquid savings balance",
            value=balance_status("total_savings"),
        )
        total_savings = st.number_input(
            "Liquid savings, including emergency fund (₹)",
            min_value=0.0,
            value=amount("total_savings"),
            step=1000.0,
            help="Cash and cash-equivalent savings. Include the emergency fund here; do not include investments.",
        )
        emergency_fund_reported = st.checkbox(
            "I confirm my emergency fund balance",
            value=balance_status("emergency_fund"),
        )
        emergency_fund = st.number_input(
            "Emergency fund (part of liquid savings) (₹)",
            min_value=0.0,
            value=amount("emergency_fund"),
            step=1000.0,
            help="This amount is a subset of liquid savings, not an additional balance.",
        )
        investments_reported = st.checkbox(
            "I confirm my investments balance",
            value=balance_status("investments"),
        )
        investments = st.number_input(
            "Investments, separate from liquid savings (₹)",
            min_value=0.0,
            value=amount("investments"),
            step=1000.0,
            help="Report investment balances separately; do not include them in liquid savings.",
        )
        monthly_savings = st.number_input(
            "Monthly savings (₹)",
            min_value=0.0,
            value=amount("monthly_savings"),
            step=500.0,
            help="Your reported amount saved monthly after non-EMI expenses and EMI. This is separate from calculated cash-flow surplus.",
        )

    st.divider()
    st.header("2. Personal and employment details")

    col1, col2 = st.columns(2)

    with col1:
        age = st.number_input(
            "Age",
            min_value=18,
            max_value=100,
            value=max(18, int(profile.get("age") or 18)),
            step=1,
        )
        employment_type = st.selectbox(
            "Employment type",
            employment_options,
            index=select_index(employment_options, "employment_type"),
        )
        employment_years = st.number_input(
            "Years of employment",
            min_value=0.0,
            max_value=80.0,
            value=amount("employment_years"),
            step=1.0,
        )
        dependents = st.number_input(
            "Number of dependents",
            min_value=0,
            max_value=30,
            value=int(profile.get("dependents") or 0),
            step=1,
        )

    with col2:
        income_stability_score = st.number_input(
            "Income stability score (0–100)",
            min_value=0.0,
            max_value=100.0,
            value=(
                70.0
                if profile.get("income_stability_score") is None
                else amount("income_stability_score")
            ),
            step=5.0,
            help="Your estimate of how stable and predictable your income is.",
        )
        insurance = st.selectbox(
            "Insurance",
            yes_no_options,
            index=select_index(yes_no_options, "insurance"),
        )
        health_insurance = st.selectbox(
            "Health insurance",
            yes_no_options,
            index=select_index(yes_no_options, "health_insurance"),
        )
        investment_experience = st.selectbox(
            "Investment experience",
            experience_options,
            index=select_index(
                experience_options, "investment_experience"
            ),
        )

    st.divider()
    st.header("3. Goals and future expectations")

    col1, col2 = st.columns(2)

    with col1:
        financial_goal = st.selectbox(
            "Primary financial goal",
            goal_options,
            index=select_index(goal_options, "financial_goal"),
        )
        expected_salary_growth_pct = st.number_input(
            "Expected annual salary growth (%)",
            min_value=-100.0,
            max_value=500.0,
            value=(
                5.0
                if profile.get("expected_salary_growth_pct") is None
                else amount("expected_salary_growth_pct")
            ),
            step=1.0,
        )
        expected_expense_inflation_pct = st.number_input(
            "Expected annual expense inflation (%)",
            min_value=-100.0,
            max_value=500.0,
            value=(
                5.0
                if profile.get("expected_expense_inflation_pct") is None
                else amount("expected_expense_inflation_pct")
            ),
            step=1.0,
        )

    with col2:
        planned_major_expense = st.selectbox(
            "Planned major expense",
            expense_options,
            index=(
                select_index(expense_options, "planned_major_expense")
                if profile.get("planned_major_expense") is not None
                else 0
            ),
        )
        planned_expense_month = st.selectbox(
            "Months until planned expense",
            list(range(37)),
            index=max(
                0,
                min(36, int(profile.get("planned_expense_month") or 0)),
            ),
            format_func=lambda month: (
                "No planned expense"
                if month == 0
                else f"In {month} month(s)"
            ),
            disabled=planned_major_expense == "No planned expense",
        )

    st.caption(
        "Review your values before saving. Default selections are "
        "provided for fields that have not been completed."
    )

    submitted = st.form_submit_button(
        "Save financial profile",
        type="primary",
        use_container_width=True,
    )


if submitted:
    payload = {
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_emi": monthly_emi,
        "total_savings": total_savings,
        "total_savings_reported": total_savings_reported,
        "emergency_fund": emergency_fund,
        "emergency_fund_reported": emergency_fund_reported,
        "investments": investments,
        "investments_reported": investments_reported,
        "total_debt": total_debt,
        "total_debt_reported": total_debt_reported,
        "age": age,
        "employment_type": employment_type,
        "employment_years": employment_years,
        "monthly_savings": monthly_savings,
        "dependents": dependents,
        "insurance": insurance,
        "health_insurance": health_insurance,
        "income_stability_score": income_stability_score,
        "financial_goal": financial_goal,
        "investment_experience": investment_experience,
        "expected_salary_growth_pct": expected_salary_growth_pct,
        "expected_expense_inflation_pct": expected_expense_inflation_pct,
        "planned_major_expense": (
            None
            if planned_major_expense == "No planned expense"
            else planned_major_expense
        ),
        "planned_expense_month": (
            0
            if planned_major_expense == "No planned expense"
            else planned_expense_month
        ),
    }

    errors = []

    if (
        planned_major_expense != "No planned expense"
        and planned_expense_month == 0
    ):
        errors.append(
            "Select how many months away the planned expense is."
        )

    if (
        total_savings_reported
        and emergency_fund_reported
        and emergency_fund > total_savings
    ):
        errors.append(
            "Emergency fund should not exceed total savings."
        )

    if monthly_savings > monthly_income:
        errors.append(
            "Monthly savings should not exceed monthly income."
        )

    if employment_years > age - 14:
        errors.append(
            "Please check the age and years of employment."
        )

    if any(value < 0 for value in [
        monthly_income,
        monthly_expenses,
        monthly_emi,
        total_savings,
        emergency_fund,
        investments,
        total_debt,
        monthly_savings,
    ]):
        errors.append("Financial amounts cannot be negative.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        try:
            response = requests.put(
                f"{API_BASE_URL}/me/financial-profile",
                json=payload,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                st.success("Financial profile saved successfully!")
                st.rerun()
            elif response.status_code == 401:
                st.session_state.access_token = ""
                st.error("Your session expired. Please log in again.")
            else:
                st.error(
                    f"Could not save profile: HTTP {response.status_code}. "
                    f"{response.text[:300]}"
                )

        except requests.RequestException:
            st.error(
                "Unable to save your profile. Check that the API is running."
            )
