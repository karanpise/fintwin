
from decimal import Decimal


def simulate_financial_scenario(
    profile: dict,
    additional_monthly_emi: float = 0,
    additional_monthly_expenses: float = 0,
    additional_upfront_cost: float = 0,
    scenario_monthly_income=None,
    scenario_monthly_expenses=None,
    scenario_monthly_emi=None,
) -> dict:
    """Simulate a hypothetical financial decision without changing the profile."""

    income = Decimal(str(profile.get("monthly_income", 0)))
    expenses = Decimal(str(profile.get("monthly_expenses", 0)))
    current_emi = Decimal(str(profile.get("monthly_emi", 0)))
    emergency_fund = Decimal(str(profile.get("emergency_fund", 0)))

    extra_emi = Decimal(str(additional_monthly_emi))
    extra_expenses = Decimal(str(additional_monthly_expenses))
    upfront_cost = Decimal(str(additional_upfront_cost))

    projected_income = (
        income if scenario_monthly_income is None
        else Decimal(str(scenario_monthly_income))
    )
    projected_expenses = (
        expenses + extra_expenses
        if scenario_monthly_expenses is None
        else Decimal(str(scenario_monthly_expenses))
    )
    projected_emi = (
        current_emi + extra_emi
        if scenario_monthly_emi is None
        else Decimal(str(scenario_monthly_emi))
    )

    values = [
        income, expenses, current_emi, emergency_fund,
        extra_emi, extra_expenses, upfront_cost,
        projected_income, projected_expenses, projected_emi,
    ]
    if any(not value.is_finite() for value in values):
        raise ValueError("Financial amounts must be finite numbers.")

    if any(value < 0 for value in values):
        raise ValueError("Financial amounts cannot be negative.")

    baseline_cash_flow = income - expenses - current_emi
    scenario_cash_flow = (
        projected_income - projected_expenses - projected_emi
    )
    scenario_emergency_fund = emergency_fund - upfront_cost
    scenario_outflow = projected_expenses + projected_emi

    emergency_months = (
        scenario_emergency_fund / scenario_outflow
        if scenario_emergency_fund >= 0 and scenario_outflow > 0
        else None
    )

    return {
        "baseline_monthly_cash_flow": round(float(baseline_cash_flow), 2),
        "scenario_monthly_cash_flow": round(float(scenario_cash_flow), 2),
        "monthly_cash_flow_change": round(
            float(scenario_cash_flow - baseline_cash_flow), 2
        ),
        "baseline_emergency_fund": round(float(emergency_fund), 2),
        "scenario_emergency_fund": round(float(scenario_emergency_fund), 2),
        "scenario_emergency_fund_months": (
            round(float(emergency_months), 2)
            if emergency_months is not None else None
        ),
        "scenario_is_cash_flow_negative": scenario_cash_flow < 0,
        "scenario_has_insufficient_upfront_funds": scenario_emergency_fund < 0,
        "scenario_monthly_income": round(float(projected_income), 2),
        "scenario_monthly_expenses": round(float(projected_expenses), 2),
        "scenario_monthly_emi": round(float(projected_emi), 2),
    }
