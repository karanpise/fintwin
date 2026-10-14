
import os

import requests
import streamlit as st
import plotly.graph_objects as go


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="FinTwin | Financial Dashboard",
    page_icon="💹",
    layout="wide",
)

API_BASE_URL = os.getenv(
    "FINTWIN_API_URL",
    "http://127.0.0.1:8000",
)

if "access_token" not in st.session_state:
    st.session_state.access_token = ""


# --------------------------------------------------
# Login and Registration
# --------------------------------------------------

def login_form():
    st.title("?? FinTwin")
    st.subheader("Your personal financial simulator")

    login_tab, register_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input(
                "Password", type="password", key="login_password"
            )
            submitted = st.form_submit_button(
                "Log in", type="primary", use_container_width=True
            )

        if submitted:
            if not email.strip() or not password:
                st.warning("Enter your email and password.")
            else:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/auth/login",
                        data={
                            "username": email.strip(),
                            "password": password,
                        },
                        timeout=10,
                    )
                    if response.status_code == 200:
                        st.session_state.access_token = response.json()["access_token"]
                        st.rerun()
                    elif response.status_code == 401:
                        st.error("Incorrect email or password.")
                    elif response.status_code == 403:
                        st.error("Your account is inactive.")
                    else:
                        st.error(f"Login failed: HTTP {response.status_code}.")
                except requests.RequestException:
                    st.error(
                        "Cannot connect to FinTwin API. Check that FastAPI is running."
                    )

    with register_tab:
        st.subheader("Create your FinTwin account")
        with st.form("register_form"):
            reg_email = st.text_input("Email address", key="register_email")
            reg_password = st.text_input(
                "Password (minimum 8 characters)",
                type="password",
                key="register_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="register_confirm_password",
            )
            register_submitted = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )

        if register_submitted:
            if not reg_email.strip() or not reg_password:
                st.warning("Enter an email address and password.")
            elif len(reg_password) < 8:
                st.warning("Password must contain at least 8 characters.")
            elif len(reg_password) > 128:
                st.warning("Password cannot exceed 128 characters.")
            elif reg_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/auth/register",
                        json={
                            "email": reg_email.strip(),
                            "password": reg_password,
                        },
                        timeout=10,
                    )
                    if response.status_code == 201:
                        st.success("Account created! Open the Log in tab to sign in.")
                    elif response.status_code == 409:
                        st.error("An account with this email already exists.")
                    elif response.status_code == 422:
                        st.error(
                            "Invalid email or registration details. Check your email address."
                        )
                    else:
                        st.error(
                            f"Registration failed: HTTP {response.status_code}."
                        )
                except requests.RequestException:
                    st.error(
                        "Cannot connect to FinTwin API. Check that FastAPI is running."
                    )


# --------------------------------------------------
# Financial alerts
# --------------------------------------------------

def show_financial_alerts(health_data: dict):
    cash_flow = float(
        health_data.get("monthly_cash_flow") or 0
    )

    emergency_months = health_data.get(
        "emergency_fund_months"
    )

    emi_ratio = health_data.get(
        "debt_to_income_percent"
    )

    st.subheader("Financial Alerts")

    # Cash flow warning
    if cash_flow < 0:
        st.error(
            f"Negative monthly cash flow: "
            f"₹{abs(cash_flow):,.2f} deficit. "
            "Review your expenses and EMI commitments."
        )

    elif cash_flow == 0:
        st.warning(
            "Your monthly cash flow is zero. "
            "Your reported income has no remaining surplus "
            "after expenses and EMI."
        )

    else:
        st.success(
            f"Positive monthly cash flow: ₹{cash_flow:,.2f}"
        )

    # Emergency fund warning
    if emergency_months is None:
        if not health_data.get("emergency_fund_reported", False):
            st.info("Emergency fund coverage is unavailable because the balance is not reported.")
        elif health_data.get("emergency_fund_coverage_status") == "zero_monthly_outflow":
            st.info("Emergency fund runway is undefined because monthly expenses and EMI are both zero.")

    elif emergency_months < 3:
        st.warning(
            f"Your emergency fund covers "
            f"{emergency_months:.2f} months of outgoings. "
            "A common planning target is 3–6 months of "
            "essential expenses."
        )

    elif emergency_months < 6:
        st.info(
            f"Your emergency fund covers "
            f"{emergency_months:.2f} months of outgoings. "
            "Consider whether building a larger reserve "
            "would suit your circumstances."
        )

    else:
        st.success(
            f"Your emergency fund covers "
            f"{emergency_months:.2f} months of outgoings."
        )

    # EMI-to-income warning
    if emi_ratio is not None:
        emi_ratio = float(emi_ratio)

        if emi_ratio > 40:
            st.warning(
                f"Your EMIs consume {emi_ratio:.2f}% "
                "of monthly income. Review repayment "
                "affordability and other commitments."
            )

        else:
            st.caption(
                f"EMI-to-income ratio: {emi_ratio:.2f}%"
            )


# --------------------------------------------------
# Authentication guard
# --------------------------------------------------

if not st.session_state.access_token:
    login_form()
    st.stop()


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.title("💹 FinTwin")
    st.caption("Financial dashboard")

    if st.button(
        "Refresh dashboard",
        use_container_width=True,
    ):
        st.rerun()

    if st.button(
        "Log out",
        use_container_width=True,
    ):
        st.session_state.access_token = ""
        st.rerun()


token = st.session_state.access_token

headers = {
    "Authorization": f"Bearer {token}"
}


# --------------------------------------------------
# Fetch financial health
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
        st.rerun()

    if response.status_code == 403:
        st.error(
            "Your account cannot access this information."
        )
        st.stop()

    if response.status_code == 404:
        st.warning(
            "Financial profile not found. "
            "Create your financial profile first."
        )
        st.stop()

    response.raise_for_status()
    data = response.json()

except requests.RequestException:
    st.error(
        "Unable to retrieve financial data. "
        "Check that the FastAPI backend is running."
    )
    st.stop()


# --------------------------------------------------
# Extract financial metrics
# --------------------------------------------------

income = float(data.get("monthly_income") or 0)
expenses = float(data.get("monthly_expenses") or 0)
emi = float(data.get("monthly_emi") or 0)
cash_flow = float(data.get("monthly_cash_flow") or 0)

savings_rate = data.get("savings_rate_percent")
debt_to_income = data.get("debt_to_income_percent")
emergency_months = data.get("emergency_fund_months")

total_savings = (
    float(data["reported_total_savings"])
    if data.get("reported_total_savings") is not None else None
)
investments = (
    float(data["reported_investments"])
    if data.get("reported_investments") is not None else None
)
emergency_fund = (
    float(data["reported_emergency_fund"])
    if data.get("reported_emergency_fund") is not None else None
)
total_debt = (
    float(data["reported_total_debt"])
    if data.get("reported_total_debt") is not None else None
)


# --------------------------------------------------
# Dashboard heading
# --------------------------------------------------

st.title("Your Financial Health Dashboard")

st.caption(
    "Understand your cash flow, savings, "
    "investments, and financial obligations."
)


# --------------------------------------------------
# Financial risk assessment
# --------------------------------------------------

st.subheader("Financial Risk Assessment")

try:
    risk_response = requests.get(
        f"{API_BASE_URL}/me/risk-analysis",
        headers=headers,
        timeout=10,
    )

    if risk_response.status_code == 401:
        st.session_state.access_token = ""
        st.warning("Your session expired. Please log in again.")
        st.stop()

    risk_response.raise_for_status()
    risk_data = risk_response.json()

    risk_level = risk_data.get(
        "risk_level",
        "Unavailable",
    )

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric(
            "Indicative Risk Level",
            risk_level,
        )

        st.caption(
            f"Baseline risk points: "
            f"{risk_data.get('risk_points', 'N/A')}"
        )

    with col2:
        st.markdown("**Factors to review**")

        risk_factors = risk_data.get(
            "risk_factors",
            [],
        )

        if risk_factors:
            for factor in risk_factors:
                st.warning(factor)
        else:
            st.success(
                "No risk triggers were identified "
                "by the baseline rules."
            )

    st.caption(
        risk_data.get("disclaimer", "")
    )

except requests.RequestException:
    st.warning(
        "Unable to load risk analysis. "
        "Check the backend and risk-analysis endpoint."
    )


# --------------------------------------------------
# Monthly overview
# --------------------------------------------------

st.subheader("Monthly Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Monthly Income",
    f"₹{income:,.0f}",
)

c2.metric(
    "Monthly Expenses",
    f"₹{expenses:,.0f}",
)

c3.metric(
    "Monthly EMI",
    f"₹{emi:,.0f}",
)

c4.metric(
    "Monthly Cash Flow",
    f"₹{cash_flow:,.0f}",
)


# --------------------------------------------------
# Financial indicators
# --------------------------------------------------

st.subheader("Financial Indicators")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Cash-Flow Rate",
    (
        f"{float(savings_rate):.2f}%"
        if savings_rate is not None
        else "N/A"
    ),
)

c2.metric(
    "EMI / Income",
    (
        f"{float(debt_to_income):.2f}%"
        if debt_to_income is not None
        else "N/A"
    ),
)

c3.metric(
    "Emergency Fund Coverage",
    (
        f"{float(emergency_months):.2f} months"
        if emergency_months is not None
        else "N/A"
    ),
)

st.caption(
    "Cash-flow rate is calculated as "
    "(income − expenses − EMI) ÷ income. "
    "It may differ from the monthly savings rate "
    "you report in your financial profile."
)


# --------------------------------------------------
# Charts
# --------------------------------------------------

left, right = st.columns(2)

with left:
    st.subheader("Monthly Cash Flow Breakdown")

    fig = go.Figure(
        go.Bar(
            x=[
                "Income",
                "Expenses",
                "EMI",
                "Remaining Cash Flow",
            ],
            y=[
                income,
                expenses,
                emi,
                cash_flow,
            ],
            text=[
                f"₹{income:,.0f}",
                f"₹{expenses:,.0f}",
                f"₹{emi:,.0f}",
                f"₹{cash_flow:,.0f}",
            ],
            textposition="auto",
        )
    )

    fig.update_layout(
        yaxis_title="Amount (INR)",
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


with right:
    st.subheader("Savings and Investments")

    fig = go.Figure(
        go.Bar(
            x=[
                "Total Savings",
                "Investments",
                "Emergency Fund",
            ],
            y=[
                total_savings,
                investments,
                emergency_fund,
            ],
            text=[
                f"₹{total_savings:,.0f}" if total_savings is not None else "Not reported",
                f"₹{investments:,.0f}" if investments is not None else "Not reported",
                f"₹{emergency_fund:,.0f}" if emergency_fund is not None else "Not reported",
            ],
            textposition="auto",
        )
    )

    fig.update_layout(
        yaxis_title="Amount (INR)",
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.caption(
        "These balances are displayed separately for comparison. "
        "Liquid savings includes the emergency fund. Investments are separate. "
        "Do not add the emergency fund to liquid savings again."
    )


# --------------------------------------------------
# Financial alerts
# --------------------------------------------------

show_financial_alerts(data)


# --------------------------------------------------
# Additional financial summary
# --------------------------------------------------

st.subheader("Financial Summary")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Total Savings",
    f"₹{total_savings:,.0f}" if total_savings is not None else "Not reported",
)

c2.metric(
    "Investments",
    f"₹{investments:,.0f}" if investments is not None else "Not reported",
)

c3.metric(
    "Total Debt",
    f"₹{total_debt:,.0f}" if total_debt is not None else "Not reported",
)


# --------------------------------------------------
# Disclaimer
# --------------------------------------------------

st.divider()

st.caption(
    "FinTwin provides estimates based on the financial "
    "information you enter. Risk indicators and thresholds "
    "are for planning purposes only; they are not a credit "
    "rating, a guarantee of future outcomes, or personalized "
    "financial advice."
)
