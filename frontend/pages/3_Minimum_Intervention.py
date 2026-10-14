
import os

import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
)

st.set_page_config(
    page_title="FinTwin | Minimum Intervention",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Minimum-Intervention Optimizer")
st.caption(
    "Explore the smallest adjustments that could help you reach "
    "your monthly cash-flow target."
)

token = st.session_state.get("access_token", "")

if not token:
    st.warning("Please log in from the main FinTwin page.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

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

    if response.status_code == 404:
        st.info("Save your financial profile before optimizing.")
        st.stop()

    response.raise_for_status()
    profile = response.json()

except requests.RequestException:
    st.error("Unable to load your financial profile.")
    st.stop()

st.subheader("Define your target")

provide_expense_split = st.checkbox(
    "I want to provide an essential/discretionary expense split",
    value=False,
    help="Expense cuts are available only against an amount you explicitly identify as discretionary.",
)
if provide_expense_split:
    saved_expenses = float(profile.get("monthly_expenses") or 0)
    essential_expenses = st.number_input(
        "Essential monthly expenses (₹)", min_value=0.0,
        max_value=saved_expenses, value=0.0, step=500.0,
        help="Enter your own estimate; FinTwin does not infer this amount.",
    )
    discretionary_expenses = st.number_input(
        "Discretionary monthly expenses (₹)", min_value=0.0,
        max_value=saved_expenses, value=0.0, step=500.0,
        help="Enter your own estimate; FinTwin does not infer this amount.",
    )

col1, col2 = st.columns(2)

with col1:
    target = st.number_input(
        "Desired monthly cash-flow surplus (₹)",
        min_value=0,
        value=10000,
        step=1000,
    )

    proposed_emi = st.number_input(
        "Additional monthly EMI (₹)",
        min_value=0,
        value=10000,
        step=1000,
    )

    proposed_expenses = st.number_input(
        "Additional monthly expenses (₹)",
        min_value=0,
        value=0,
        step=500,
    )

with col2:
    max_expense_reduction = st.number_input(
        "Maximum feasible monthly expense reduction (₹)",
        min_value=0,
        value=3000,
        step=500,
        help="Enter only expenses you could realistically reduce.",
    )

    max_emi_reduction = st.number_input(
        "Maximum possible reduction in proposed EMI (₹)",
        min_value=0,
        value=2000,
        step=500,
        help="Use a realistic alternative financing amount.",
    )

    max_income_increase = st.number_input(
        "Feasible monthly income increase (₹)",
        min_value=0,
        value=0,
        step=1000,
        help="Only include a realistic, achievable increase.",
    )

horizon_months = st.selectbox("Projection horizon (months)", [3, 6, 12, 24, 60], index=2)
enforce_runway = st.checkbox("Set a minimum emergency-fund runway", value=False)
if enforce_runway:
    minimum_runway = st.number_input(
        "Minimum emergency-fund runway (months)", min_value=0.0,
        value=3.0, step=0.5,
    )

if st.button(
    "Find minimum intervention",
    type="primary",
    use_container_width=True,
):
    payload = {
        "additional_monthly_emi": proposed_emi,
        "additional_monthly_expenses": proposed_expenses,
        "target_monthly_surplus": target,
        "max_expense_reduction": max_expense_reduction,
        "max_emi_reduction": max_emi_reduction,
        "max_income_increase": max_income_increase,
        "horizon_months": horizon_months,
    }
    if provide_expense_split:
        if round(essential_expenses + discretionary_expenses, 2) != round(saved_expenses, 2):
            st.error("Essential and discretionary expenses must sum to saved expenses.")
            st.stop()
        payload["essential_monthly_expenses"] = essential_expenses
        payload["discretionary_monthly_expenses"] = discretionary_expenses
    if enforce_runway:
        payload["minimum_emergency_fund_runway_months"] = minimum_runway

    try:
        result_response = requests.post(
            f"{API_BASE_URL}/me/optimize",
            json=payload,
            headers=headers,
            timeout=10,
        )

        if result_response.status_code == 401:
            st.session_state.access_token = ""
            st.warning("Your session expired. Please log in again.")
            st.stop()

        result_response.raise_for_status()
        st.session_state["optimization_result"] = result_response.json()

    except requests.RequestException as exc:
        st.error(f"Optimization failed: {exc}")

result = st.session_state.get("optimization_result")

if result:
    st.divider()
    st.subheader("Optimization results")
    st.metric(
        "Baseline profile cash flow",
        f"₹{result['baseline_outcome']['monthly_cash_flow']:,.0f}",
    )

    if result["feasible"]:
        st.success("The target is achievable within the limits you entered.")
    else:
        st.warning(
            "The target is not achievable within the current limits. "
            "Consider changing the target or revisiting your assumptions."
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
        "Scenario cash flow",
        f"₹{result['scenario_monthly_cash_flow']:,.0f}",
    )
    c2.metric(
        "Required adjustment",
        f"₹{result['required_adjustment']:,.0f}",
    )
    c3.metric(
        "Remaining shortfall",
        f"₹{result['remaining_shortfall']:,.0f}",
    )

    st.subheader("Suggested monthly adjustments")

    st.write(
        f"**Expense reduction:** "
        f"₹{result['recommended_expense_reduction']:,.0f}"
    )
    st.write(
        f"**Proposed EMI reduction:** "
        f"₹{result['recommended_new_emi_reduction']:,.0f}"
    )
    st.write(
        f"**Income increase:** "
        f"₹{result['recommended_income_increase']:,.0f}"
    )

    if len(result.get("tied_minimum_options", [])) > 1:
        st.caption("Equal-cost alternatives found (monthly amounts).")
        st.dataframe(result["tied_minimum_options"], hide_index=True)

    st.metric(
        "Projected monthly cash flow after adjustments",
        f"₹{result['optimized_monthly_cash_flow']:,.0f}",
    )

    st.caption(
        "These are mathematical scenarios, not guaranteed outcomes. "
        "Validate affordability, essential spending, financing terms, "
        "and the feasibility of each adjustment before acting."
    )
    with st.expander("Projected month-by-month comparison"):
        st.dataframe(result.get("monthly_differences", []), hide_index=True)
        st.write("Constraints checked")
        st.json(result.get("constraints_checked", {}))
        st.write("Assumptions")
        for assumption in result.get("assumptions", []):
            st.write(f"- {assumption}")
        st.caption("Search and projection limitations: " + " ".join(result.get("limitations", [])))
