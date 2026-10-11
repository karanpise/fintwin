
import math
from decimal import Decimal, InvalidOperation
from typing import Any


def _to_finite_float(value: Any, field: str) -> float:
    """Convert a financial value to a finite float."""
    if value is None:
        value = 0

    try:
        number = float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a valid number.") from exc

    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite.")

    if number < 0:
        raise ValueError(f"{field} cannot be negative.")

    return number


def analyze_financial_risk(profile: dict) -> dict:
    """
    Evaluate baseline financial risk using deterministic rules.

    This is a baseline assessment, not the ML risk prediction.
    It does not modify the user's financial profile.
    """
    if not isinstance(profile, dict):
        raise TypeError("profile must be a dictionary.")

    income = _to_finite_float(
        profile.get("monthly_income", 0), "monthly_income"
    )
    expenses = _to_finite_float(
        profile.get("monthly_expenses", 0), "monthly_expenses"
    )
    emi = _to_finite_float(
        profile.get("monthly_emi", 0), "monthly_emi"
    )
    emergency_fund = _to_finite_float(
        profile.get("emergency_fund", 0), "emergency_fund"
    )
    total_debt = _to_finite_float(
        profile.get("total_debt", 0), "total_debt"
    )

    monthly_outflow = expenses + emi
    monthly_cash_flow = income - monthly_outflow

    # This metric measures monthly EMI burden, not total debt.
    debt_to_income = (
        (emi / income) * 100
        if income > 0
        else None
    )

    emergency_months = (
        emergency_fund / monthly_outflow
        if monthly_outflow > 0
        else None
    )

    risk_factors = []
    risk_points = 0

    if income <= 0:
        risk_factors.append("Monthly income is missing or zero.")
        risk_points += 2

    if monthly_cash_flow < 0:
        risk_factors.append(
            "Monthly expenses and EMI exceed monthly income."
        )
        risk_points += 3

    if debt_to_income is not None and debt_to_income > 40:
        risk_factors.append(
            "Monthly EMI exceeds 40% of monthly income."
        )
        risk_points += 2

    if emergency_months is not None and emergency_months < 3:
        risk_factors.append(
            "Emergency fund covers less than three months of outflow."
        )
        risk_points += 2

    if income > 0 and total_debt > income * 12:
        risk_factors.append(
            "Total debt exceeds twelve months of income."
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
        "monthly_cash_flow": round(monthly_cash_flow, 2),
        "debt_to_income_percent": (
            round(debt_to_income, 2)
            if debt_to_income is not None
            else None
        ),
        "emergency_fund_months": (
            round(emergency_months, 2)
            if emergency_months is not None
            else None
        ),
        "risk_factors": risk_factors,
        "method": "rule_based_baseline",
        "disclaimer": (
            "This rule-based assessment is an indicative financial "
            "screening tool, not a guarantee of future financial outcomes."
        ),
    }
