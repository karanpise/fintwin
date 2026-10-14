
import os

import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
)

st.set_page_config(
    page_title="FinTwin | What-If Simulator",
    page_icon="🔮",
    layout="wide",
)

st.title("🔮 What-If Financial Simulator")
st.caption(
    "Explore hypothetical financial decisions before making them."
)

token = st.session_state.get("access_token", "")

if not token:
    st.warning("Please log in from the main FinTwin page first.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

# Load the saved financial profile.
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
        st.info("Create your financial profile before running simulations.")
        st.stop()

    response.raise_for_status()
    profile = response.json()

except requests.RequestException:
    st.error("Could not connect to the FinTwin API.")
    st.stop()


st.subheader("Your hypothetical decision")

col1, col2, col3 = st.columns(3)

with col1:
    additional_emi = st.number_input(
        "Additional monthly EMI (₹)",
        min_value=0,
        value=10000,
        step=1000,
    )

with col2:
    additional_expenses = st.number_input(
        "Additional monthly expenses (₹)",
        min_value=0,
        value=0,
        step=500,
    )

with col3:
    upfront_cost = st.number_input(
        "One-time upfront cost (₹)",
        min_value=0,
        value=20000,
        step=5000,
    )

if st.button("Run simulation", type="primary", use_container_width=True):
    payload = {
        "additional_monthly_emi": additional_emi,
        "additional_monthly_expenses": additional_expenses,
        "additional_upfront_cost": upfront_cost,
    }

    try:
        simulation_response = requests.post(
            f"{API_BASE_URL}/me/simulate",
            json=payload,
            headers=headers,
            timeout=10,
        )

        if simulation_response.status_code == 401:
            st.session_state.access_token = ""
            st.warning("Your session expired. Please log in again.")
            st.stop()

        simulation_response.raise_for_status()
        result = simulation_response.json()

        st.session_state.simulation_result = result

    except requests.RequestException:
        st.error("Simulation failed. Check the backend and try again.")


result = st.session_state.get("simulation_result")

if result:
    st.divider()
    st.subheader("Simulation results")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Current monthly cash flow",
        f"₹{result['baseline_monthly_cash_flow']:,.0f}",
    )

    c2.metric(
        "Scenario monthly cash flow",
        f"₹{result['scenario_monthly_cash_flow']:,.0f}",
        delta=f"₹{result['monthly_cash_flow_change']:,.0f}",
        delta_color="normal",
    )

    c3.metric(
        "Emergency fund after upfront cost",
        (
            f"₹{result['scenario_emergency_fund']:,.0f}"
            if result.get("scenario_emergency_fund") is not None
            else "Not reported"
        ),
    )

    left, right = st.columns(2)

    with left:
        st.markdown("**Monthly cash flow comparison**")

        fig = go.Figure(
            data=[
                go.Bar(
                    x=["Current situation", "Hypothetical scenario"],
                    y=[
                        result["baseline_monthly_cash_flow"],
                        result["scenario_monthly_cash_flow"],
                    ],
                    text=[
                        f"₹{result['baseline_monthly_cash_flow']:,.0f}",
                        f"₹{result['scenario_monthly_cash_flow']:,.0f}",
                    ],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            yaxis_title="Monthly cash flow (₹)",
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**Emergency fund coverage**")

        months = result["scenario_emergency_fund_months"]

        if months is None:
            st.metric("Coverage", "N/A")
            if not result.get("emergency_fund_reported", False):
                st.caption("Coverage is unavailable because the emergency-fund balance is not reported.")
            else:
                st.caption("Monthly outflow is zero, so coverage is undefined.")
        else:
            st.metric("Scenario coverage", f"{months:.2f} months")
            st.caption(
                "Calculated using the remaining emergency fund divided "
                "by projected monthly expenses and EMI."
            )

    if result["scenario_has_insufficient_upfront_funds"]:
        st.error(
            "The upfront cost cannot be fully covered by the confirmed emergency-fund balance. "
            "The calculation shows a shortfall; it does not assume you "
            "will borrow or withdraw additional funds."
        )

    if result["scenario_is_cash_flow_negative"]:
        st.error(
            "The scenario produces negative monthly cash flow. "
            "Review affordability before making a decision."
        )
    elif result["monthly_cash_flow_change"] < 0:
        st.warning(
            "This scenario reduces your monthly cash flow."
        )
    else:
        st.success(
            "This scenario does not reduce monthly cash flow "
            "under the entered assumptions."
        )

    st.caption(
        "Simulations are hypothetical estimates, not personalized "
        "financial advice. They do not model interest-rate changes, "
        "income disruption, inflation, or other unentered costs."
    )
