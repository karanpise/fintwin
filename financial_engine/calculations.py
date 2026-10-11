
from decimal import Decimal


def calculate_financial_health(profile) -> dict:
    income = Decimal(str(profile.monthly_income))
    expenses = Decimal(str(profile.monthly_expenses))
    emi = Decimal(str(profile.monthly_emi))
    savings = Decimal(str(profile.total_savings))
    emergency_fund = Decimal(str(profile.emergency_fund))
    investments = Decimal(str(profile.investments))
    total_debt = Decimal(str(profile.total_debt))

    monthly_cash_flow = income - expenses - emi

    savings_rate = (
        (monthly_cash_flow / income) * 100
        if income > 0
        else None
    )

    debt_to_income = (
        (emi / income) * 100
        if income > 0
        else None
    )

    monthly_outflow = expenses + emi

    emergency_fund_months = (
        emergency_fund / monthly_outflow
        if monthly_outflow > 0
        else None
    )

    return {
        "monthly_income": float(income),
        "monthly_expenses": float(expenses),
        "monthly_emi": float(emi),
        "monthly_cash_flow": float(monthly_cash_flow),
        "savings_rate_percent": (
            round(float(savings_rate), 2)
            if savings_rate is not None
            else None
        ),
        "debt_to_income_percent": (
            round(float(debt_to_income), 2)
            if debt_to_income is not None
            else None
        ),
        "emergency_fund_months": (
            round(float(emergency_fund_months), 2)
            if emergency_fund_months is not None
            else None
        ),
        "total_savings": float(savings),
        "emergency_fund": float(emergency_fund),
        "investments": float(investments),
        "total_debt": float(total_debt),
    }
