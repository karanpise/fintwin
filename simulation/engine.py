"""Deterministic month-by-month financial projections.

All monthly cash-flow values use the Phase 1 convention: expenses exclude EMI.
The model does not apply investment returns, inflation, or income growth.
"""
from decimal import Decimal

from financial_engine.balances import BALANCE_FIELDS, balance_is_reported, read_reported_balance
from financial_engine.calculations import calculate_financial_health
from financial_engine.monetary import parse_money, round_money

ZERO = Decimal("0.00")
SUPPORTED_HORIZONS = (3, 6, 12, 24, 60)


def _money(value, name, *, optional=False):
    if value is None and optional:
        return None
    return parse_money(value, name)


def _change(value, name):
    try:
        amount = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{name} must be a valid monetary amount.") from exc
    if not amount.is_finite() or abs(amount) > Decimal("999999999999.99"):
        raise ValueError(f"{name} must be finite and within supported monetary limits.")
    if amount.quantize(Decimal("0.01")) != amount:
        raise ValueError(f"{name} supports at most two decimal places.")
    return amount


def _rate(value, name):
    amount = _change(value, name)
    if amount < 0 or amount > Decimal("100"):
        raise ValueError(f"{name} must be between 0 and 100 percent.")
    return amount


def _out(value):
    return float(round_money(value)) if value is not None else None


def _loan_payment(principal, annual_rate_percent, term_months):
    monthly_rate = annual_rate_percent / Decimal("1200")
    if monthly_rate == 0:
        return round_money(principal / term_months)
    factor = (Decimal("1") + monthly_rate) ** term_months
    return round_money(principal * monthly_rate * factor / (factor - 1))


def _project(profile, *, horizon, changes, apply_surplus_to_savings,
             one_time_cost, one_time_month, one_time_source,
             loan_principal, loan_rate, loan_term, loan_start_month):
    income0 = _money(profile.get("monthly_income"), "monthly_income")
    expenses0 = _money(profile.get("monthly_expenses"), "monthly_expenses")
    emi0 = _money(profile.get("monthly_emi"), "monthly_emi")
    liquid = read_reported_balance(profile, "total_savings")
    emergency = read_reported_balance(profile, "emergency_fund")
    investments = read_reported_balance(profile, "investments")
    debt = read_reported_balance(profile, "total_debt")
    if liquid is not None and emergency is not None and emergency > liquid:
        raise ValueError("emergency_fund cannot exceed total_savings (liquid_savings).")

    loan_payment = _loan_payment(loan_principal, loan_rate, loan_term) if loan_principal else ZERO
    loan_balance = ZERO
    rows = []
    negative_months = []
    cumulative = ZERO
    cumulative_after_cost = ZERO
    min_liquid = liquid
    liquid_depleted = 0 if liquid == 0 else None
    emergency_depleted = 0 if emergency == 0 else None

    for month in range(1, horizon + 1):
        income = income0 + sum((c["income"] for c in changes if month >= c["from_month"]), ZERO)
        expenses = expenses0 + sum((c["expenses"] for c in changes if month >= c["from_month"]), ZERO)
        emi = emi0 + sum((c["emi"] for c in changes if month >= c["from_month"]), ZERO)
        for name, amount in (("income", income), ("expenses", expenses), ("EMI", emi)):
            if amount < 0 or amount > Decimal("999999999999.99"):
                raise ValueError(f"Projected {name} must remain within supported non-negative monetary limits.")
        if month >= loan_start_month and loan_principal and loan_balance == 0:
            loan_balance = loan_principal
            if debt is not None:
                debt += loan_principal
        loan_interest = ZERO
        loan_principal_paid = ZERO
        if loan_balance > 0 and month >= loan_start_month:
            loan_interest = round_money(loan_balance * loan_rate / Decimal("1200"))
            payment = min(loan_payment, loan_balance + loan_interest)
            loan_principal_paid = payment - loan_interest
            loan_balance = max(ZERO, loan_balance - loan_principal_paid)
            if debt is not None:
                debt = round_money(max(ZERO, debt - loan_principal_paid))
            emi += payment

        flow = round_money(income - expenses - emi)
        event_cost = one_time_cost if month == one_time_month else ZERO
        cumulative += flow
        if flow < 0:
            negative_months.append(month)
        cumulative_after_cost += flow - event_cost
        unfunded_event = ZERO
        unfunded_deficit = ZERO
        # One-time costs are charged at the beginning of their event month.
        if event_cost:
            if one_time_source == "emergency_fund":
                if emergency is None:
                    unfunded_event += event_cost
                else:
                    funded = min(emergency, event_cost)
                    emergency = round_money(emergency - funded)
                    if liquid is not None:
                        liquid = round_money(max(ZERO, liquid - funded))
                    unfunded_event += event_cost - funded
            elif liquid is None:
                unfunded_event += event_cost
            else:
                funded = min(liquid, event_cost)
                liquid = round_money(liquid - funded)
                if emergency is not None:
                    emergency = round_money(min(emergency, liquid))
                unfunded_event += event_cost - funded
            if liquid is not None:
                min_liquid = liquid if min_liquid is None else min(min_liquid, liquid)
                if liquid == 0 and liquid_depleted is None:
                    liquid_depleted = month
            if emergency == 0 and emergency_depleted is None:
                emergency_depleted = month
        if liquid is not None and apply_surplus_to_savings:
            if flow >= 0:
                liquid = round_money(liquid + flow)
            else:
                draw = -flow
                funded = min(liquid, draw)
                non_emergency = max(ZERO, liquid - (emergency or ZERO))
                liquid = round_money(liquid - funded)
                if emergency is not None:
                    emergency = round_money(max(ZERO, emergency - max(ZERO, draw - non_emergency)))
                unfunded_deficit += draw - funded
        if emergency is not None and liquid is not None:
            emergency = round_money(min(emergency, liquid))
        if liquid is not None:
            min_liquid = liquid if min_liquid is None else min(min_liquid, liquid)
            if liquid == 0 and liquid_depleted is None:
                liquid_depleted = month
        if emergency is not None and emergency == 0 and emergency_depleted is None:
            emergency_depleted = month

        calc_profile = {
            "monthly_income": income, "monthly_expenses": expenses,
            "monthly_emi": emi, "total_savings": liquid,
            "total_savings_reported": liquid is not None,
            "emergency_fund": emergency, "investments": investments,
            "emergency_fund_reported": emergency is not None,
            "investments_reported": investments is not None,
            "total_debt": debt,
            "total_debt_reported": debt is not None,
        }
        health = calculate_financial_health(calc_profile)
        row = {
            "month": month, "income": _out(income), "expenses": _out(expenses),
            "emi": _out(emi), "cash_flow_surplus": _out(flow),
            "one_time_cost": _out(event_cost), "unfunded_cost": _out(unfunded_event),
            "unfunded_cash_flow_deficit": _out(unfunded_deficit),
            "liquid_savings": _out(liquid), "emergency_fund": _out(emergency),
            "investments": _out(investments), "debt": _out(debt),
            "tracked_net_worth": health["tracked_net_worth"],
            "emergency_fund_runway_months": health["emergency_fund_months"],
            "new_loan_interest": _out(loan_interest),
            "new_loan_principal_paid": _out(loan_principal_paid),
        }
        rows.append(row)

    return {
        "months": rows, "negative_cash_flow_months": negative_months,
        "first_liquid_savings_depleted_month": liquid_depleted,
        "first_emergency_fund_depleted_month": emergency_depleted,
        "minimum_liquid_savings": _out(min_liquid),
        "cumulative_cash_flow_surplus": _out(cumulative),
        "cumulative_net_cash_flow_after_one_time_costs": _out(cumulative_after_cost),
        "ending_liquid_savings": _out(liquid), "ending_emergency_fund": _out(emergency),
        "ending_investments": _out(investments), "ending_debt": _out(debt),
        "ending_tracked_net_worth": rows[-1]["tracked_net_worth"],
    }


def simulate_financial_scenario(
    profile: dict, additional_monthly_emi=0, additional_monthly_expenses=0,
    additional_upfront_cost=0, scenario_monthly_income=None,
    scenario_monthly_expenses=None, scenario_monthly_emi=None, *,
    horizon_months=12, recurring_income_change=0, recurring_expense_change=0,
    recurring_emi_change=0, changes_start_month=1, one_time_cost=None,
    one_time_month=1, one_time_source=None, apply_surplus_to_savings=True,
    new_loan_principal=0, new_loan_annual_rate_percent=0,
    new_loan_term_months=0, new_loan_start_month=1,
):
    """Return compatible snapshot keys plus deterministic baseline/scenario timelines."""
    if horizon_months not in SUPPORTED_HORIZONS:
        raise ValueError(f"horizon_months must be one of {SUPPORTED_HORIZONS}.")
    for name, month in (("changes_start_month", changes_start_month), ("one_time_month", one_time_month), ("new_loan_start_month", new_loan_start_month)):
        if not isinstance(month, int) or isinstance(month, bool) or month < 1 or month > horizon_months:
            raise ValueError(f"{name} must be between 1 and horizon_months.")
    money_names = {
        "additional_monthly_emi": additional_monthly_emi,
        "additional_monthly_expenses": additional_monthly_expenses,
        "additional_upfront_cost": additional_upfront_cost,
        "recurring_income_change": recurring_income_change,
        "recurring_expense_change": recurring_expense_change,
        "recurring_emi_change": recurring_emi_change,
        "new_loan_principal": new_loan_principal,
        "new_loan_annual_rate_percent": new_loan_annual_rate_percent,
    }
    signed_names = {"recurring_income_change", "recurring_expense_change", "recurring_emi_change"}
    vals = {
        k: _change(v, k) if k in signed_names
        else _rate(v, k) if k == "new_loan_annual_rate_percent"
        else _money(v, k)
        for k, v in money_names.items()
    }
    upfront = vals["additional_upfront_cost"] if one_time_cost is None else _money(one_time_cost, "one_time_cost")
    legacy_upfront = one_time_cost is None and upfront > 0
    if one_time_source is None:
        one_time_source = "emergency_fund" if legacy_upfront else "liquid_savings"
    if one_time_source not in {"liquid_savings", "emergency_fund"}:
        raise ValueError("one_time_source must be liquid_savings or emergency_fund.")
    principal = vals["new_loan_principal"]
    if new_loan_term_months > 600:
        raise ValueError("new_loan_term_months cannot exceed 600.")
    if principal and (
        not isinstance(new_loan_term_months, int)
        or isinstance(new_loan_term_months, bool)
        or new_loan_term_months < 1
    ):
        raise ValueError("new_loan_term_months is required when new_loan_principal is positive.")
    if new_loan_term_months and new_loan_term_months < 1:
        raise ValueError("new_loan_term_months must be positive.")

    income = _money(profile.get("monthly_income"), "monthly_income")
    expenses = _money(profile.get("monthly_expenses"), "monthly_expenses")
    emi = _money(profile.get("monthly_emi"), "monthly_emi")
    base_changes = [{"from_month": 1, "income": ZERO, "expenses": ZERO, "emi": ZERO}]
    scenario_income = income if scenario_monthly_income is None else _money(scenario_monthly_income, "scenario_monthly_income")
    scenario_expenses = expenses if scenario_monthly_expenses is None else _money(scenario_monthly_expenses, "scenario_monthly_expenses")
    scenario_emi = emi if scenario_monthly_emi is None else _money(scenario_monthly_emi, "scenario_monthly_emi")
    change_start = changes_start_month
    scenario_changes = [{
        "from_month": 1, "income": scenario_income - income,
        "expenses": (
            scenario_expenses - expenses if scenario_monthly_expenses is not None
            else vals["additional_monthly_expenses"]
        ),
        "emi": (
            scenario_emi - emi if scenario_monthly_emi is not None
            else vals["additional_monthly_emi"]
        ),
    }, {
        "from_month": change_start, "income": vals["recurring_income_change"],
        "expenses": vals["recurring_expense_change"], "emi": vals["recurring_emi_change"],
    }]
    oneoff = round_money(upfront)
    baseline = _project(profile, horizon=horizon_months, changes=base_changes, apply_surplus_to_savings=apply_surplus_to_savings, one_time_cost=ZERO, one_time_month=one_time_month, one_time_source=one_time_source, loan_principal=ZERO, loan_rate=ZERO, loan_term=0, loan_start_month=1)
    scenario = _project(profile, horizon=horizon_months, changes=scenario_changes, apply_surplus_to_savings=apply_surplus_to_savings, one_time_cost=oneoff, one_time_month=one_time_month, one_time_source=one_time_source, loan_principal=principal, loan_rate=vals["new_loan_annual_rate_percent"], loan_term=new_loan_term_months or 0, loan_start_month=new_loan_start_month)

    base_first, scenario_first = baseline["months"][0], scenario["months"][0]
    comparison = []
    for b, s in zip(baseline["months"], scenario["months"]):
        differences = {}
        for key in ("income", "expenses", "emi", "cash_flow_surplus", "liquid_savings", "emergency_fund", "investments", "debt", "tracked_net_worth"):
            differences[key] = (
                _out(Decimal(str(s[key])) - Decimal(str(b[key])))
                if s[key] is not None and b[key] is not None else None
            )
        comparison.append({"month": b["month"], **differences})
    legacy_emergency_fund = _money(
        profile.get("emergency_fund"), "emergency_fund", optional=True
    )
    return {
        # Legacy one-month response keys retained for existing clients.
        "baseline_monthly_cash_flow": base_first["cash_flow_surplus"],
        "scenario_monthly_cash_flow": scenario_first["cash_flow_surplus"],
        "monthly_cash_flow_change": comparison[0]["cash_flow_surplus"],
        "baseline_emergency_fund": _out(legacy_emergency_fund or ZERO),
        "emergency_fund_reported": balance_is_reported(profile, "emergency_fund"),
        "balance_reporting_status": {
            field: balance_is_reported(profile, field) for field in BALANCE_FIELDS
        },
        "reported_baseline_balances": {
            field: _out(read_reported_balance(profile, field))
            for field in BALANCE_FIELDS
        },
        "scenario_emergency_fund": scenario_first["emergency_fund"],
        "scenario_emergency_fund_months": scenario_first["emergency_fund_runway_months"],
        "scenario_is_cash_flow_negative": scenario_first["cash_flow_surplus"] < 0,
        "scenario_has_insufficient_upfront_funds": any(
            month["unfunded_cost"] > 0 for month in scenario["months"]
        ),
        "scenario_monthly_income": scenario_first["income"],
        "scenario_monthly_expenses": scenario_first["expenses"],
        "scenario_monthly_emi": scenario_first["emi"],
        "horizon_months": horizon_months, "assumptions": {
            "monthly_surplus_applied_to_liquid_savings": bool(apply_surplus_to_savings),
            "one_time_cost_source": one_time_source,
            "one_time_cost_month": one_time_month,
            "income_expenses_and_existing_emi_are_flat_unless_changed": True,
            "investment_returns_and_inflation": "not_modelled",
            "existing_debt_amortization": "not_modelled_without_loan_terms",
            "essential_expenses": "not_available_in_profile",
        },
        "baseline": baseline, "scenario": scenario, "monthly_differences": comparison,
    }
