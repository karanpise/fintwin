
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
    }

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

    if result["feasible"]:
        st.success("The target is achievable within the limits you entered.")
    else:
        st.warning(
            "The target is not achievable within the current limits. "
            "Consider changing the target or revisiting your assumptions."
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

    st.metric(
        "Projected monthly cash flow after adjustments",
        f"₹{result['optimized_monthly_cash_flow']:,.0f}",
    )

    st.caption(
        "These are mathematical scenarios, not guaranteed outcomes. "
        "Validate affordability, essential spending, financing terms, "
        "and the feasibility of each adjustment before acting."
    )
