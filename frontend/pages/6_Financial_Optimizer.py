
import os

import requests
import streamlit as st
import plotly.graph_objects as go


st.set_page_config(
    page_title="FinTwin | Financial Optimizer",
    page_icon="🎯",
    layout="wide",
)

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
)

st.title("🎯 Financial Intervention Optimizer")
st.caption(
    "Explore possible monthly adjustments without modifying "
    "your saved financial profile."
)

# --------------------------------------------------
# Authentication
# --------------------------------------------------

token = st.session_state.get("access_token", "")

if not token:
    st.warning(
        "Please log in through the FinTwin dashboard first."
    )
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

# --------------------------------------------------
# Load financial health
# --------------------------------------------------

try:
    response = requests.get(
        f"{API_BASE_URL}/me/financial-health",
        headers=headers,
        timeout=10,
    )

    if response.status_code == 401:
        st.session_state.access_token = ""
        st.warning("Your session expired. Please log in again.")
        st.stop()

    if response.status_code == 404:
        st.warning("Create your financial profile first.")
        st.stop()

    response.raise_for_status()
    profile = response.json()

except requests.RequestException:
    st.error(
        "Unable to load your financial profile. "
        "Check that FastAPI is running."
    )
    st.stop()

income = float(profile.get("monthly_income") or 0)
expenses = float(profile.get("monthly_expenses") or 0)
existing_emi = float(profile.get("monthly_emi") or 0)

current_cash_flow = income - expenses - existing_emi

# --------------------------------------------------
# Current position
# --------------------------------------------------

st.subheader("Current financial position")

c1, c2, c3 = st.columns(3)

c1.metric("Monthly Income", f"₹{income:,.0f}")
c2.metric(
    "Monthly Expenses + EMI",
    f"₹{expenses + existing_emi:,.0f}",
)
c3.metric("Monthly Cash Flow", f"₹{current_cash_flow:,.0f}")

# --------------------------------------------------
# Optimizer form
# --------------------------------------------------

st.subheader("Configure your scenario")

st.info(
    "Expense reduction is considered only when you explicitly provide "
    "an essential/discretionary split."
)
provide_expense_split = st.checkbox("I want to provide an expense split", value=False)
enforce_runway = st.checkbox("Set a minimum emergency-fund runway", value=False)

with st.form("financial_optimizer_form"):
    if provide_expense_split:
        essential_expenses = st.number_input(
            "Essential monthly expenses (₹)", min_value=0.0,
            max_value=expenses, value=0.0, step=500.0,
            help="Enter your own estimate; FinTwin does not infer this amount.",
        )
        discretionary_expenses = st.number_input(
            "Discretionary monthly expenses (₹)", min_value=0.0,
            max_value=expenses, value=0.0, step=500.0,
            help="Enter your own estimate; FinTwin does not infer this amount.",
        )

    st.caption(
        f"Your saved monthly expenses: ₹{expenses:,.2f}"
    )

    target_surplus = st.number_input(
        "Target monthly surplus (₹)",
        min_value=0.0,
        value=10000.0,
        step=1000.0,
    )

    additional_expenses = st.number_input(
        "Additional monthly expenses (₹)",
        min_value=0.0,
        value=0.0,
        step=500.0,
    )

    additional_emi = st.number_input(
        "Proposed additional monthly EMI (₹)",
        min_value=0.0,
        value=0.0,
        step=500.0,
    )

    st.markdown("**Maximum proposed adjustments**")

    max_expense_reduction = st.number_input(
        "Maximum monthly expense reduction (₹)",
        min_value=0.0,
        value=min(5000.0, expenses),
        step=500.0,
    )

    max_emi_reduction = st.number_input(
        "Maximum reduction in proposed EMI (₹)",
        min_value=0.0,
        value=0.0,
        step=500.0,
    )

    max_income_increase = st.number_input(
        "Maximum monthly income increase (₹)",
        min_value=0.0,
        value=5000.0,
        step=500.0,
    )

    horizon_months = st.selectbox("Projection horizon (months)", [3, 6, 12, 24, 60], index=2)
    if enforce_runway:
        minimum_runway = st.number_input(
            "Minimum emergency-fund runway (months)", min_value=0.0,
            value=3.0, step=0.5,
        )

    submitted = st.form_submit_button(
        "Optimize my scenario",
        type="primary",
        use_container_width=True,
    )

# --------------------------------------------------
# Run optimizer
# --------------------------------------------------

if submitted:
    if provide_expense_split and abs(
        essential_expenses
        + discretionary_expenses
        - expenses
    ) > 0.01:
        st.error(
            "Essential and discretionary expenses must add up "
            "to your saved monthly expenses."
        )
        st.stop()

    payload = {
        "additional_monthly_emi": additional_emi,
        "additional_monthly_expenses": additional_expenses,
        "target_monthly_surplus": target_surplus,
        "max_expense_reduction": max_expense_reduction,
        "max_emi_reduction": max_emi_reduction,
        "max_income_increase": max_income_increase,
        "horizon_months": horizon_months,
    }
    if provide_expense_split:
        payload["essential_monthly_expenses"] = essential_expenses
        payload["discretionary_monthly_expenses"] = discretionary_expenses
    if enforce_runway:
        payload["minimum_emergency_fund_runway_months"] = minimum_runway

    try:
        response = requests.post(
            f"{API_BASE_URL}/me/optimize",
            json=payload,
            headers=headers,
            timeout=15,
        )

        if response.status_code == 401:
            st.session_state.access_token = ""
            st.warning("Your session expired. Please log in again.")
            st.stop()

        if response.status_code == 404:
            st.error(
                response.json().get(
                    "detail",
                    "Financial profile not found.",
                )
            )
            st.stop()

        if response.status_code == 422:
            detail = response.json().get(
                "detail",
                "Invalid optimizer inputs.",
            )
            st.error(f"Could not optimize: {detail}")
            st.stop()

        response.raise_for_status()
        result = response.json()

    except requests.RequestException as exc:
        st.error(f"Optimizer request failed: {exc}")
        st.stop()

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    st.divider()
    st.subheader("Optimization results")
    st.metric(
        "Baseline profile cash flow",
        f"₹{result['baseline_outcome']['monthly_cash_flow']:,.2f}",
    )

    if result["feasible"]:
        st.success(
            "A feasible minimum-cost candidate was found by the documented search."
        )
    else:
        st.warning(
            "The target cannot be reached within the configured "
            "adjustment limits."
        )
    runway_status = result.get("constraints_checked", {}).get(
        "emergency_fund_runway_status"
    )
    if enforce_runway and runway_status != "checked":
        st.info(
            "The emergency-fund runway constraint is not assessed as met "
            "because the balance is unconfirmed or projected outflow makes "
            "runway undefined. Confirm the balance or revise the constraint."
        )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Scenario Cash Flow",
        f"₹{result['scenario_monthly_cash_flow']:,.2f}",
    )

    c2.metric(
        "Required Adjustment",
        f"₹{result['required_adjustment']:,.2f}",
    )

    c3.metric(
        "Remaining Shortfall",
        f"₹{result['remaining_shortfall']:,.2f}",
    )

    st.subheader("Recommended monthly adjustments")

    recommendations = [
        (
            "Expense reduction",
            result["recommended_expense_reduction"],
        ),
        (
            "Proposed EMI reduction",
            result["recommended_new_emi_reduction"],
        ),
        (
            "Income increase",
            result["recommended_income_increase"],
        ),
    ]

    for label, amount in recommendations:
        if amount > 0:
            st.write(f"**{label}:** ₹{amount:,.2f}")

    if not any(amount > 0 for _, amount in recommendations):
        st.info("No adjustments are required for this scenario.")

    if len(result.get("tied_minimum_options", [])) > 1:
        st.caption("Equal-cost alternatives found (all amounts are monthly).")
        st.dataframe(result["tied_minimum_options"], hide_index=True)

    c1, c2 = st.columns(2)

    c1.metric(
        "Projected Monthly Cash Flow",
        f"₹{result['optimized_monthly_cash_flow']:,.2f}",
    )

    c2.metric(
        "Target Monthly Surplus",
        f"₹{result['target_monthly_surplus']:,.2f}",
    )

    # --------------------------------------------------
    # Chart
    # --------------------------------------------------

    st.subheader("Before vs. after")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Before adjustment",
            x=["Monthly Cash Flow"],
            y=[result["scenario_monthly_cash_flow"]],
        )
    )

    fig.add_trace(
        go.Bar(
            name="After adjustment",
            x=["Monthly Cash Flow"],
            y=[result["optimized_monthly_cash_flow"]],
        )
    )

    fig.add_hline(
        y=result["target_monthly_surplus"],
        line_dash="dash",
        annotation_text="Target surplus",
    )

    fig.update_layout(
        barmode="group",
        yaxis_title="Amount (₹)",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.subheader("Affordability limitations")

    st.info(
        "The optimizer uses your stated expense categories and "
        "adjustment limits. It does not independently verify them, "
        "and it cannot guarantee that income increases or spending "
        "reductions are achievable."
    )

    st.caption(
        "No changes have been saved to your financial profile."
    )
    with st.expander("Projected month-by-month comparison"):
        st.write("Baseline vs. selected intervention")
        st.dataframe(result.get("monthly_differences", []), hide_index=True)
        st.write("Constraints checked")
        st.json(result.get("constraints_checked", {}))
        st.write("Assumptions")
        for assumption in result.get("assumptions", []):
            st.write(f"- {assumption}")
        st.caption("Search and projection limitations: " + " ".join(result.get("limitations", [])))
