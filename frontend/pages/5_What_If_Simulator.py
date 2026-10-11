
import math
import os

import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(
    page_title="FinTwin | What-if Simulator",
    page_icon="🧮",
    layout="wide",
)

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

st.title("🧮 What-if Financial Simulator")
st.caption(
    "Explore hypothetical purchases and monthly financial changes "
    "without modifying your saved financial profile."
)


def get_error_detail(response):
    try:
        return str(response.json().get("detail", response.text))
    except ValueError:
        return response.text


# Authentication
token = st.session_state.get("access_token", "")

if not token:
    st.warning("Please log in through the FinTwin dashboard first.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}


# Load current financial position
try:
    response = requests.get(
        f"{API_BASE_URL}/me/financial-health",
        headers=headers,
        timeout=10,
    )

    if response.status_code == 401:
        st.session_state["access_token"] = ""
        st.warning("Your session expired. Please log in again.")
        st.stop()

    if response.status_code == 404:
        st.warning("Create and save your financial profile first.")
        st.stop()

    response.raise_for_status()
    profile = response.json()

except requests.RequestException as exc:
    st.error(
        "Unable to load your financial profile. "
        "Check that FastAPI is running."
    )

    if getattr(exc, "response", None) is not None:
        st.code(get_error_detail(exc.response))
    else:
        st.caption(str(exc))

    st.stop()


income = float(profile.get("monthly_income") or 0)
expenses = float(profile.get("monthly_expenses") or 0)
existing_emi = float(profile.get("monthly_emi") or 0)
emergency_fund = float(profile.get("emergency_fund") or 0)

current_cash_flow = income - expenses - existing_emi
current_outflow = expenses + existing_emi

current_coverage = (
    emergency_fund / current_outflow
    if current_outflow > 0
    else None
)


# Current position
st.subheader("Your current financial position")

c1, c2, c3 = st.columns(3)
c1.metric("Monthly Income", f"₹{income:,.0f}")
c2.metric("Monthly Outgoings", f"₹{current_outflow:,.0f}")
c3.metric("Monthly Cash Flow", f"₹{current_cash_flow:,.0f}")


# Scenario type
scenario_type = st.radio(
    "Choose a scenario",
    [
        "Monthly budget changes",
        "Major purchase / loan",
    ],
    horizontal=True,
)


# Budget scenario
if scenario_type == "Monthly budget changes":
    st.subheader("Adjust your monthly budget")

    with st.form("budget_scenario_form"):
        scenario_income = st.number_input(
            "Expected monthly income (₹)",
            min_value=0.0,
            value=income,
            step=1000.0,
        )

        scenario_expenses = st.number_input(
            "Expected monthly expenses (₹)",
            min_value=0.0,
            value=expenses,
            step=1000.0,
        )

        scenario_emi = st.number_input(
            "Total monthly EMI after changes (₹)",
            min_value=0.0,
            value=existing_emi,
            step=500.0,
            help="Enter total EMI, including existing loans.",
        )

        submitted = st.form_submit_button(
            "Simulate budget",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        st.session_state["fintwin_scenario"] = {
            "type": "budget",
            "income": float(scenario_income),
            "expenses": float(scenario_expenses),
            "emi": float(scenario_emi),
        }


# Purchase scenario
else:
    st.subheader("Plan a major purchase")

    with st.form("purchase_scenario_form"):
        purchase_price = st.number_input(
            "Purchase price (₹)",
            min_value=0.0,
            value=800000.0,
            step=50000.0,
        )

        down_payment = st.number_input(
            "Down payment (₹)",
            min_value=0.0,
            value=150000.0,
            step=10000.0,
        )

        annual_rate = st.number_input(
            "Annual interest rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=9.0,
            step=0.5,
        )

        loan_years = st.number_input(
            "Loan tenure (years)",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
        )

        scenario_income = st.number_input(
            "Expected monthly income (₹)",
            min_value=0.0,
            value=income,
            step=1000.0,
        )

        scenario_expenses = st.number_input(
            "Expected monthly expenses (₹)",
            min_value=0.0,
            value=expenses,
            step=1000.0,
        )

        submitted = st.form_submit_button(
            "Calculate purchase impact",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if down_payment > purchase_price:
            st.error("Down payment cannot exceed the purchase price.")
        else:
            loan_amount = float(purchase_price - down_payment)
            loan_months = int(loan_years * 12)
            monthly_rate = float(annual_rate) / 1200

            if loan_amount <= 0:
                new_loan_emi = 0.0
            elif monthly_rate == 0:
                new_loan_emi = loan_amount / loan_months
            else:
                factor = math.pow(
                    1 + monthly_rate,
                    loan_months,
                )
                new_loan_emi = (
                    loan_amount
                    * monthly_rate
                    * factor
                    / (factor - 1)
                )

            st.session_state["fintwin_scenario"] = {
                "type": "purchase",
                "income": float(scenario_income),
                "expenses": float(scenario_expenses),
                "emi": float(existing_emi + new_loan_emi),
                "purchase_price": float(purchase_price),
                "down_payment": float(down_payment),
                "loan_amount": loan_amount,
                "new_loan_emi": float(new_loan_emi),
                "loan_months": loan_months,
            }


# Send the new scenario to the backend.
scenario = st.session_state.get("fintwin_scenario")

if scenario:
    if "backend_result" not in scenario:
        payload = {
            "scenario_monthly_income": scenario["income"],
            "scenario_monthly_expenses": scenario["expenses"],
            "scenario_monthly_emi": scenario["emi"],
            "additional_upfront_cost": (
                scenario.get("down_payment", 0.0)
                if scenario["type"] == "purchase"
                else 0.0
            ),
        }

        try:
            api_response = requests.post(
                f"{API_BASE_URL}/me/simulate",
                headers=headers,
                json=payload,
                timeout=15,
            )

            if api_response.status_code == 401:
                st.session_state["access_token"] = ""
                st.session_state.pop("fintwin_scenario", None)
                st.warning("Your session expired. Please log in again.")
                st.stop()

            api_response.raise_for_status()
            scenario["backend_result"] = api_response.json()
            st.session_state["fintwin_scenario"] = scenario

        except requests.RequestException as exc:
            st.error("Backend simulation failed.")

            if getattr(exc, "response", None) is not None:
                st.code(get_error_detail(exc.response))
            else:
                st.caption(str(exc))

            st.stop()


# Display backend results
if scenario:
    result = scenario["backend_result"]

    result_income = float(result["scenario_monthly_income"])
    result_expenses = float(result["scenario_monthly_expenses"])
    result_emi = float(result["scenario_monthly_emi"])
    result_cash_flow = float(result["scenario_monthly_cash_flow"])
    result_emergency_fund = float(result["scenario_emergency_fund"])
    result_coverage = result["scenario_emergency_fund_months"]

    cash_flow_rate = (
        result_cash_flow / result_income * 100
        if result_income > 0
        else None
    )

    emi_ratio = (
        result_emi / result_income * 100
        if result_income > 0
        else None
    )

    st.divider()
    st.subheader("Scenario results")

    if scenario["type"] == "purchase":
        st.markdown("**Purchase and loan breakdown**")

        c1, c2, c3 = st.columns(3)
        c1.metric("Loan Amount", f"₹{scenario['loan_amount']:,.0f}")
        c2.metric(
            "Estimated New EMI",
            f"₹{scenario['new_loan_emi']:,.0f}",
        )
        c3.metric("Total Monthly EMI", f"₹{result_emi:,.0f}")

        total_payments = (
            scenario["new_loan_emi"] * scenario["loan_months"]
        )
        estimated_interest = max(
            0.0,
            total_payments - scenario["loan_amount"],
        )

        st.caption(
            f"Estimated loan interest over the tenure: "
            f"₹{estimated_interest:,.0f}. Actual lender charges "
            "and terms may differ."
        )

        st.metric(
            "Emergency Fund After Down Payment",
            f"₹{result_emergency_fund:,.0f}",
            delta=(
                f"-₹{scenario['down_payment']:,.0f}"
                if scenario["down_payment"] > 0
                else None
            ),
        )

        if result["scenario_has_insufficient_upfront_funds"]:
            st.error(
                "The down payment exceeds your reported emergency fund. "
                "This assumes the entire down payment comes from that fund."
            )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Projected Monthly Cash Flow",
        f"₹{result_cash_flow:,.0f}",
        delta=f"₹{float(result['monthly_cash_flow_change']):,.0f}",
    )

    c2.metric(
        "Cash-Flow Rate",
        f"{cash_flow_rate:.2f}%" if cash_flow_rate is not None else "N/A",
    )

    c3.metric(
        "EMI / Income",
        f"{emi_ratio:.2f}%" if emi_ratio is not None else "N/A",
    )

    st.subheader("Current vs. scenario")

    fig = go.Figure()
    categories = ["Income", "Expenses", "Total EMI", "Cash Flow"]

    fig.add_trace(
        go.Bar(
            name="Current",
            x=categories,
            y=[income, expenses, existing_emi, current_cash_flow],
        )
    )

    fig.add_trace(
        go.Bar(
            name="Scenario",
            x=categories,
            y=[
                result_income,
                result_expenses,
                result_emi,
                result_cash_flow,
            ],
        )
    )

    fig.update_layout(
        barmode="group",
        yaxis_title="Amount (₹)",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Emergency fund coverage")

    if result_coverage is None:
        st.info(
            "Coverage cannot be calculated because scenario "
            "expenses and EMI are both zero."
        )
    else:
        coverage = float(result_coverage)

        st.metric(
            "Projected Coverage",
            f"{coverage:.2f} months",
            delta=(
                f"{coverage - current_coverage:.2f} months"
                if current_coverage is not None
                else None
            ),
        )

    if result["scenario_is_cash_flow_negative"]:
        st.error("This scenario produces negative monthly cash flow.")
    elif result_cash_flow == 0:
        st.warning("This scenario leaves no monthly cash-flow surplus.")
    else:
        st.success("This scenario retains positive monthly cash flow.")

    if result_coverage is not None and float(result_coverage) < 3:
        st.warning(
            "Emergency fund coverage would be below the "
            "three-month planning target."
        )

    if emi_ratio is not None and emi_ratio > 40:
        st.warning("EMI exceeds 40% of monthly income. Review affordability.")

    st.caption(
        "These are simplified estimates, not a guarantee of affordability. "
        "Taxes, lender fees, investment returns, and all future expenses "
        "are not modelled. Purchase scenarios assume the down payment is "
        "paid from the reported emergency fund."
    )

    if st.button("Clear scenario"):
        st.session_state.pop("fintwin_scenario", None)
        st.rerun()
