from decimal import Decimal

from financial_engine.balances import balance_is_reported, read_reported_balance
from financial_engine.calculations import calculate_financial_health
from financial_engine.monetary import parse_money, round_money, round_percent


def analyze_financial_risk(profile: dict) -> dict:
    """Apply deterministic screening rules to validated profile inputs.

    This is a rule-based screen, not a probability of financial failure.
    Missing optional balances are reported as unassessed, never as zero.
    """
    if not isinstance(profile, dict):
        raise TypeError("profile must be a dictionary.")

    metrics = calculate_financial_health(profile)
    income = parse_money(profile["monthly_income"], "monthly_income")
    expenses = parse_money(profile["monthly_expenses"], "monthly_expenses")
    emi = parse_money(profile["monthly_emi"], "monthly_emi")
    emergency_fund = read_reported_balance(profile, "emergency_fund")
    total_debt = read_reported_balance(profile, "total_debt")

    monthly_outflow = expenses + emi
    monthly_cash_flow = income - monthly_outflow
    emi_to_income = (
        emi / income * Decimal("100") if income > 0 else None
    )
    emergency_months = (
        emergency_fund / monthly_outflow
        if emergency_fund is not None and monthly_outflow > 0
        else None
    )

    risk_factors = []
    unassessed_factors = []
    risk_points = 0

    if income <= 0:
        risk_factors.append("Monthly income is zero.")
        risk_points += 2

    if monthly_cash_flow < 0:
        risk_factors.append(
            "Monthly non-EMI expenses plus required EMI exceed income."
        )
        risk_points += 3

    if emi_to_income is not None and emi_to_income > 40:
        risk_factors.append(
            "Monthly EMI exceeds 40% of monthly take-home income."
        )
        risk_points += 2

    if emergency_fund is None:
        unassessed_factors.append("emergency fund coverage")
    elif emergency_months is not None and emergency_months < 3:
        risk_factors.append(
            "Emergency fund covers less than three months of "
            "reported expenses plus EMI."
        )
        risk_points += 2
    elif emergency_months is None:
        unassessed_factors.append(
            "emergency fund coverage (monthly outflow is zero)"
        )

    if total_debt is None:
        unassessed_factors.append("outstanding debt level")
    elif income > 0 and total_debt > income * 12:
        risk_factors.append(
            "Outstanding debt exceeds twelve months of take-home income."
        )
        risk_points += 1

    if risk_points >= 5:
        risk_level = "High"
    elif risk_points >= 2:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "risk_level": risk_level,
        "risk_points": risk_points,
        "monthly_cash_flow": float(round_money(monthly_cash_flow)),
        "cash_flow_surplus_rate_percent": metrics[
            "cash_flow_surplus_rate_percent"
        ],
        "emi_to_income_percent": (
            float(round_percent(emi_to_income))
            if emi_to_income is not None
            else None
        ),
        "debt_to_income_percent": (
            float(round_percent(emi_to_income))
            if emi_to_income is not None
            else None
        ),
        "emergency_fund_months": metrics["emergency_fund_months"],
        "emergency_fund_reported": balance_is_reported(profile, "emergency_fund"),
        "total_debt_reported": balance_is_reported(profile, "total_debt"),
        "reported_emergency_fund": metrics["reported_emergency_fund"],
        "reported_total_debt": metrics["reported_total_debt"],
        "risk_factors": risk_factors,
        "unassessed_factors": unassessed_factors,
        "assessment_completeness": (
            "complete" if not unassessed_factors else "partial"
        ),
        "method": "rule_based_baseline",
        "disclaimer": (
            "This rule-based assessment is an indicative financial "
            "screening tool, not a probability or guarantee of future "
            "financial outcomes. Ratios use reported take-home income, "
            "non-EMI expenses, and separate EMI payments."
        ),
    }
