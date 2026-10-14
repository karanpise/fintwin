
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
reported_emergency_fund = profile.get("reported_emergency_fund")
emergency_fund = (
    float(reported_emergency_fund)
    if reported_emergency_fund is not None
    else None
)

current_cash_flow = income - expenses - existing_emi
current_outflow = expenses + existing_emi

current_coverage = (
    emergency_fund / current_outflow
    if emergency_fund is not None and current_outflow > 0
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
        horizon_months = st.selectbox(
            "Projection horizon (months)", [3, 6, 12, 24, 60], index=2,
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

        scenario_emi = st.number_input(
            "Total monthly EMI after changes (₹)",
            min_value=0.0,
            value=existing_emi,
            step=500.0,
            help="EMI is separate from monthly expenses. Enter total EMI, including existing loans.",
        )
        one_time_cost = st.number_input(
            "One-time cost (₹)", min_value=0.0, value=0.0, step=5000.0,
            help="Charged at the start of month 1 from liquid savings.",
        )

        submitted = st.form_submit_button(
            "Simulate budget",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        st.session_state["fintwin_projection_scenario"] = {
            "type": "budget",
            "income": float(scenario_income),
            "expenses": float(scenario_expenses),
            "emi": float(scenario_emi),
            "one_time_cost": float(one_time_cost),
            "horizon_months": int(horizon_months),
        }


# Purchase scenario
else:
    st.subheader("Plan a major purchase")

    with st.form("purchase_scenario_form"):
        horizon_months = st.selectbox(
            "Projection horizon (months)", [3, 6, 12, 24, 60], index=2,
        )
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
            st.session_state["fintwin_projection_scenario"] = {
                "type": "purchase",
                "income": float(scenario_income),
                "expenses": float(scenario_expenses),
                "emi": float(existing_emi),
                "purchase_price": float(purchase_price),
                "down_payment": float(down_payment),
                "loan_amount": loan_amount,
                "loan_months": loan_months,
                "annual_rate": float(annual_rate),
                "horizon_months": int(horizon_months),
            }


# Send the new scenario to the backend.
scenario = st.session_state.get("fintwin_projection_scenario")

if scenario:
    if "backend_result" not in scenario:
        payload = {
            "scenario_monthly_income": scenario["income"],
            "scenario_monthly_expenses": scenario["expenses"],
            "scenario_monthly_emi": scenario["emi"],
            "horizon_months": scenario.get("horizon_months", int(horizon_months)),
            "additional_upfront_cost": (
                scenario.get("down_payment", 0.0)
                if scenario["type"] == "purchase"
                else scenario.get("one_time_cost", 0.0)
            ),
            "new_loan_principal": scenario.get("loan_amount", 0.0),
            "new_loan_annual_rate_percent": scenario.get("annual_rate", 0.0),
            "new_loan_term_months": scenario.get("loan_months", 0),
            "one_time_source": "liquid_savings",
            "apply_surplus_to_savings": True,
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
                st.session_state.pop("fintwin_projection_scenario", None)
                st.warning("Your session expired. Please log in again.")
                st.stop()

            api_response.raise_for_status()
            scenario["backend_result"] = api_response.json()
            st.session_state["fintwin_projection_scenario"] = scenario

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
    result_coverage = result["scenario_emergency_fund_months"]
    first_scenario_month = result["scenario"]["months"][0]
    result_emi = float(first_scenario_month["emi"])
    result_cash_flow = float(first_scenario_month["cash_flow_surplus"])

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
            f"₹{result_emi - existing_emi:,.2f}",
        )
        c3.metric("Total Monthly EMI", f"₹{result_emi:,.0f}")

        estimated_interest = sum(
            month["new_loan_interest"] for month in result["scenario"]["months"]
        )

        st.caption(
            f"Estimated loan interest within the selected projection horizon: "
            f"₹{estimated_interest:,.0f}. Actual lender charges "
            "and terms may differ."
        )

        scenario_liquid_savings = first_scenario_month["liquid_savings"]
        baseline_liquid_savings = result["baseline"]["months"][0]["liquid_savings"]
        liquid_delta = (
            float(scenario_liquid_savings) - float(baseline_liquid_savings)
            if scenario_liquid_savings is not None and baseline_liquid_savings is not None
            else None
        )
        st.metric(
            "Liquid Savings After Month 1",
            f"₹{scenario_liquid_savings:,.0f}"
            if scenario_liquid_savings is not None else "N/A",
            delta=f"₹{liquid_delta:,.0f}" if liquid_delta is not None else None,
        )

        if result["scenario_has_insufficient_upfront_funds"]:
            st.error(
                "The down payment exceeds reported liquid savings. "
                "The unfunded portion is shown in the monthly projection."
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

    st.plotly_chart(fig, width="stretch", alt="Current position compared with the first scenario month")

    st.subheader("Month-by-month projection")
    baseline_months = result["baseline"]["months"]
    scenario_months = result["scenario"]["months"]
    monthly_rows = []
    for base_month, scenario_month in zip(baseline_months, scenario_months):
        monthly_rows.append({
            "Month": base_month["month"],
            "Baseline surplus": base_month["cash_flow_surplus"],
            "Scenario surplus": scenario_month["cash_flow_surplus"],
            "Baseline liquid savings": base_month["liquid_savings"],
            "Scenario liquid savings": scenario_month["liquid_savings"],
            "Scenario emergency fund": scenario_month["emergency_fund"],
            "Scenario debt": scenario_month["debt"],
            "Tracked net worth": scenario_month["tracked_net_worth"],
        })
    st.dataframe(monthly_rows, alt="Baseline and scenario monthly financial projection", hide_index=True)
    st.caption(
        f"Minimum projected scenario liquid savings: "
        f"{result['scenario']['minimum_liquid_savings']} · "
        f"First liquid-savings depletion month: "
        f"{result['scenario']['first_liquid_savings_depleted_month']} · "
        f"First emergency-fund depletion month: "
        f"{result['scenario']['first_emergency_fund_depleted_month']} · "
        f"Negative cash-flow months: "
        f"{result['scenario']['negative_cash_flow_months']}"
    )
    st.caption(
        f"Cumulative cash-flow surplus: "
        f"₹{result['scenario']['cumulative_cash_flow_surplus']:,.2f} · "
        f"Ending liquid savings: "
        f"{result['scenario']['ending_liquid_savings']} · "
        f"Ending debt: {result['scenario']['ending_debt']} · "
        f"Ending tracked net worth: "
        f"{result['scenario']['ending_tracked_net_worth']}"
    )

    st.subheader("Emergency fund coverage")

    if result_coverage is None:
        st.info(
            "Emergency-fund runway is unavailable because the balance is "
            + (
                "not confirmed."
                if not result.get("emergency_fund_reported", False)
                else "scenario expenses and EMI are both zero."
            )
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

    if result["scenario"]["negative_cash_flow_months"]:
        st.error(
            "This scenario produces negative cash flow in month(s): "
            f"{result['scenario']['negative_cash_flow_months']}."
        )
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
        "paid from reported liquid savings."
    )

    if st.button("Clear scenario"):
        st.session_state.pop("fintwin_projection_scenario", None)
        st.rerun()
