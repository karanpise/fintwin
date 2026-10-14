from collections.abc import Mapping
from decimal import Decimal

from financial_engine.balances import BALANCE_FIELDS, balance_is_reported, read_reported_balance
from financial_engine.monetary import parse_money, round_money, round_percent


_MISSING = object()


def _get_value(profile, field: str):
    if isinstance(profile, Mapping):
        return profile.get(field, _MISSING)
    return getattr(profile, field, _MISSING)


def _read_money(profile, field: str, *, required: bool = False):
    value = _get_value(profile, field)
    if value is _MISSING or value is None:
        if required:
            raise ValueError(f"{field} is required and cannot be missing.")
        return None
    return parse_money(value, field)


def _output_money(value):
    return float(round_money(value)) if value is not None else None


def _output_percent(value):
    return float(round_percent(value)) if value is not None else None


def calculate_financial_health(profile) -> dict:
    """Calculate monthly cash flow and reported balance-sheet indicators.

    `monthly_expenses` excludes EMI; EMI is supplied separately. Optional
    balances and reported monthly savings remain unknown when not provided.
    """
    income = _read_money(profile, "monthly_income", required=True)
    expenses = _read_money(profile, "monthly_expenses", required=True)
    emi = _read_money(profile, "monthly_emi", required=True)

    monthly_savings = _read_money(profile, "monthly_savings")
    # Preserve the stored numeric values under their legacy keys. Derived
    # metrics use only balances explicitly confirmed by the user.
    legacy_balances = {
        field: _read_money(profile, field) for field in BALANCE_FIELDS
    }
    reported_balances = {
        field: read_reported_balance(profile, field)
        for field in BALANCE_FIELDS
    }
    liquid_savings = reported_balances["total_savings"]
    emergency_fund = reported_balances["emergency_fund"]
    investments = reported_balances["investments"]
    total_debt = reported_balances["total_debt"]

    monthly_cash_flow = income - expenses - emi
    monthly_outflow = expenses + emi

    cash_flow_surplus_rate = (
        monthly_cash_flow / income * Decimal("100")
        if income > 0
        else None
    )
    actual_savings_rate = (
        monthly_savings / income * Decimal("100")
        if monthly_savings is not None and income > 0
        else None
    )
    emi_to_income = (
        emi / income * Decimal("100") if income > 0 else None
    )
    emergency_fund_months = (
        emergency_fund / monthly_outflow
        if emergency_fund is not None and monthly_outflow > 0
        else None
    )
    emergency_fund_coverage_status = (
        "missing_emergency_fund"
        if emergency_fund is None
        else "zero_monthly_outflow"
        if monthly_outflow == 0
        else "calculated"
    )

    tracked_assets = (
        liquid_savings + investments
        if liquid_savings is not None and investments is not None
        else None
    )
    tracked_net_worth = (
        tracked_assets - total_debt
        if tracked_assets is not None and total_debt is not None
        else None
    )

    missing_net_worth_components = [
        "property and other unreported assets",
        "non-debt liabilities",
    ]
    if liquid_savings is None:
        missing_net_worth_components.append("liquid savings")
    if investments is None:
        missing_net_worth_components.append("investments")
    if total_debt is None:
        missing_net_worth_components.append("outstanding debt")

    cash_flow_rate = _output_percent(cash_flow_surplus_rate)
    return {
        "monthly_income": _output_money(income),
        "monthly_expenses": _output_money(expenses),
        "monthly_emi": _output_money(emi),
        "monthly_cash_flow": _output_money(monthly_cash_flow),
        "cash_flow_surplus_rate_percent": cash_flow_rate,
        "actual_savings_rate_percent": _output_percent(actual_savings_rate),
        "actual_savings_rate_status": (
            "not_reported"
            if monthly_savings is None
            else "zero_income"
            if income == 0
            else "calculated"
        ),
        # Legacy contract: this has always represented the cash-flow surplus
        # rate. Keep it as an alias while consumers migrate to the clear name.
        "savings_rate_percent": cash_flow_rate,
        "emi_to_income_percent": _output_percent(emi_to_income),
        # Legacy contract name retained for existing API clients.
        "debt_to_income_percent": _output_percent(emi_to_income),
        "emergency_fund_months": _output_percent(emergency_fund_months),
        "emergency_fund_coverage_status": emergency_fund_coverage_status,
        "monthly_savings": _output_money(monthly_savings),
        "liquid_savings": _output_money(liquid_savings),
        # Legacy numeric values and their serialization remain available.
        # New clients should use the reporting flags and nullable canonical
        # values below instead of treating an old default zero as confirmed.
        "total_savings": _output_money(legacy_balances["total_savings"]),
        "emergency_fund": _output_money(legacy_balances["emergency_fund"]),
        "investments": _output_money(legacy_balances["investments"]),
        "total_debt": _output_money(legacy_balances["total_debt"]),
        **{
            f"{field}_reported": balance_is_reported(profile, field)
            for field in BALANCE_FIELDS
        },
        "reported_total_savings": _output_money(liquid_savings),
        "reported_emergency_fund": _output_money(emergency_fund),
        "reported_investments": _output_money(investments),
        "reported_total_debt": _output_money(total_debt),
        "tracked_financial_assets": _output_money(tracked_assets),
        "tracked_financial_liabilities": _output_money(total_debt),
        "tracked_net_worth": _output_money(tracked_net_worth),
        "net_worth_completeness": "partial",
        "net_worth_missing_components": missing_net_worth_components,
    }
