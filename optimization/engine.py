"""Deterministic minimum-intervention search for monthly cash-flow goals.

The search treats one rupee of monthly expense reduction, proposed EMI
reduction, and feasible income increase as equal intervention magnitude.
Because this gives many tied solutions, the engine reports deterministic
extreme-point alternatives instead of claiming a unique recommendation.
Every candidate is checked by the Phase 2 simulator.
"""
from decimal import Decimal, ROUND_CEILING
from itertools import combinations

from financial_engine.balances import read_reported_balance
from financial_engine.monetary import MAX_MONEY, parse_money, round_money
from simulation.engine import SUPPORTED_HORIZONS, simulate_financial_scenario

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value, name):
    return parse_money(value, name)


def _runway(value):
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except Exception as exc:
        raise ValueError("minimum_emergency_fund_runway_months must be a number.") from exc
    if not amount.is_finite() or amount < 0 or amount > Decimal("600"):
        raise ValueError("minimum_emergency_fund_runway_months must be between 0 and 600.")
    if amount.quantize(CENT) != amount:
        raise ValueError("minimum_emergency_fund_runway_months supports at most two decimal places.")
    return amount


def _candidate_points(total, expense_cap, emi_cap, income_cap, outflow_reduction_floor):
    """Return all vertices of the minimum-cost feasible allocation polygon.

    Let e and m be recurring expense and proposed-EMI reductions and i be an
    income increase. The minimum objective fixes e+m+i=total. Constraints are
    box limits and (when known) e+m >= outflow_reduction_floor. The remaining
    feasible set is a bounded polygon in (e,m); all its vertices are found by
    intersecting pairs of its boundary lines.
    """
    lines = [
        ("e", ZERO), ("e", expense_cap),
        ("m", ZERO), ("m", emi_cap),
        ("sum", total),
        ("sum", total - income_cap),
        ("sum", max(outflow_reduction_floor, ZERO)),
    ]
    points = set()
    for first, second in combinations(lines, 2):
        kind1, value1 = first
        kind2, value2 = second
        if kind1 == kind2 == "e":
            continue
        if kind1 == kind2 == "m":
            continue
        if kind1 == "e" and kind2 == "m":
            expense, emi = value1, value2
        elif kind1 == "m" and kind2 == "e":
            expense, emi = value2, value1
        elif kind1 == "e" and kind2 == "sum":
            expense, emi = value1, value2 - value1
        elif kind1 == "sum" and kind2 == "e":
            expense, emi = value2, value1 - value2
        elif kind1 == "m" and kind2 == "sum":
            expense, emi = value2 - value1, value1
        elif kind1 == "sum" and kind2 == "m":
            expense, emi = value1 - value2, value2
        else:
            continue
        income = total - expense - emi
        if (
            ZERO <= expense <= expense_cap
            and ZERO <= emi <= emi_cap
            and ZERO <= income <= income_cap
            and expense + emi >= outflow_reduction_floor
            and expense + emi + income == total
        ):
            points.add((expense, emi, income))
    return sorted(points)


def _simulate(profile, *, horizon_months, additional_expenses, additional_emi,
              expense_reduction, emi_reduction, income_increase):
    profile_income = _money(profile["monthly_income"], "monthly_income")
    profile_expenses = _money(profile["monthly_expenses"], "monthly_expenses")
    profile_emi = _money(profile["monthly_emi"], "monthly_emi")
    scenario_expenses = profile_expenses + additional_expenses - expense_reduction
    scenario_emi = profile_emi + additional_emi - emi_reduction
    scenario_income = profile_income + income_increase
    if min(scenario_expenses, scenario_emi, scenario_income) < ZERO:
        raise ValueError("Candidate projections cannot have negative income, expenses, or EMI.")
    if max(scenario_expenses, scenario_emi, scenario_income) > MAX_MONEY:
        raise ValueError("Candidate projections exceed supported monetary limits.")
    return simulate_financial_scenario(
        profile,
        horizon_months=horizon_months,
        scenario_monthly_income=scenario_income,
        scenario_monthly_expenses=scenario_expenses,
        scenario_monthly_emi=scenario_emi,
    )


def optimize_monthly_cash_flow(
    profile: dict,
    additional_monthly_emi: Decimal = ZERO,
    additional_monthly_expenses: Decimal = ZERO,
    target_monthly_surplus: Decimal = Decimal("10000"),
    max_expense_reduction: Decimal = ZERO,
    max_emi_reduction: Decimal = ZERO,
    max_income_increase: Decimal = ZERO,
    essential_monthly_expenses: Decimal | None = None,
    discretionary_monthly_expenses: Decimal | None = None,
    *,
    horizon_months: int = 12,
    minimum_emergency_fund_runway_months: Decimal | None = None,
) -> dict:
    """Find minimum monthly intervention for a cash-flow surplus target.

    Expense cuts are permitted only against an explicitly supplied
    discretionary amount. EMI cuts apply only to a proposed additional EMI.
    User-entered maximums bound the three possible intervention types.
    """
    if horizon_months not in SUPPORTED_HORIZONS:
        raise ValueError(f"horizon_months must be one of {SUPPORTED_HORIZONS}.")
    runway_floor = _runway(minimum_emergency_fund_runway_months)
    income = _money(profile.get("monthly_income"), "monthly_income")
    expenses = _money(profile.get("monthly_expenses"), "monthly_expenses")
    existing_emi = _money(profile.get("monthly_emi"), "monthly_emi")
    new_emi = _money(additional_monthly_emi, "additional_monthly_emi")
    new_expenses = _money(additional_monthly_expenses, "additional_monthly_expenses")
    target = _money(target_monthly_surplus, "target_monthly_surplus")
    expense_cap = _money(max_expense_reduction, "max_expense_reduction")
    emi_cap = min(_money(max_emi_reduction, "max_emi_reduction"), new_emi)
    income_cap = min(
        _money(max_income_increase, "max_income_increase"),
        max(ZERO, MAX_MONEY - income),
    )

    categories_provided = essential_monthly_expenses is not None or discretionary_monthly_expenses is not None
    essential = discretionary = None
    if categories_provided:
        if essential_monthly_expenses is None or discretionary_monthly_expenses is None:
            raise ValueError("Provide both essential and discretionary expenses.")
        essential = _money(essential_monthly_expenses, "essential_monthly_expenses")
        discretionary = _money(discretionary_monthly_expenses, "discretionary_monthly_expenses")
        if essential + discretionary != expenses:
            raise ValueError("Essential and discretionary expenses must sum to the saved monthly expenses.")
        expense_cap = min(expense_cap, discretionary)
    else:
        expense_cap = ZERO

    scenario_flow = income - expenses - existing_emi - new_emi - new_expenses
    needed = max(ZERO, round_money(target - scenario_flow))
    emergency = read_reported_balance(profile, "emergency_fund")
    outflow_floor = ZERO
    runway_status = "not_configured"
    if runway_floor is not None:
        if emergency is None:
            runway_status = "unassessed_missing_emergency_fund"
        else:
            emergency_balance = emergency
            starting_outflow = expenses + new_expenses + existing_emi + new_emi
            if starting_outflow == ZERO:
                runway_status = "unassessed_zero_monthly_outflow"
            else:
                runway_status = "checked"
                allowed_outflow = emergency_balance / runway_floor if runway_floor else MAX_MONEY
                raw_floor = max(ZERO, starting_outflow - allowed_outflow)
                outflow_floor = raw_floor.quantize(CENT, rounding=ROUND_CEILING)

    minimum_total = max(needed, outflow_floor)
    candidates = _candidate_points(minimum_total, expense_cap, emi_cap, income_cap, outflow_floor)
    enough_capacity = expense_cap + emi_cap + income_cap >= minimum_total
    if not candidates:
        candidates = [(expense_cap, emi_cap, income_cap)]

    baseline = simulate_financial_scenario(profile, horizon_months=horizon_months)
    checked = []
    rejection_reasons = []
    for expense_cut, emi_cut, income_raise in candidates:
        projection = _simulate(
            profile,
            horizon_months=horizon_months,
            additional_expenses=new_expenses,
            additional_emi=new_emi,
            expense_reduction=expense_cut,
            emi_reduction=emi_cut,
            income_increase=income_raise,
        )
        flows_ok = all(
            Decimal(str(row["cash_flow_surplus"])) >= target
            for row in projection["scenario"]["months"]
        )
        runway_ok = True
        candidate_runway_status = runway_status
        if runway_status == "checked":
            runways = [row["emergency_fund_runway_months"] for row in projection["scenario"]["months"]]
            if any(value is None for value in runways):
                candidate_runway_status = "unassessed_undefined_projected_runway"
            else:
                runway_ok = all(Decimal(str(value)) >= runway_floor for value in runways)
        elif runway_floor is not None:
            # A configured minimum runway is a hard constraint. Unknown
            # emergency funds or undefined runway cannot satisfy it.
            runway_ok = False
        feasible = flows_ok and runway_ok and expense_cut + emi_cut + income_raise >= needed
        record = {
            "expense_reduction": expense_cut,
            "proposed_emi_reduction": emi_cut,
            "income_increase": income_raise,
            "total": expense_cut + emi_cut + income_raise,
            "projection": projection,
            "feasible": feasible,
            "runway_status": candidate_runway_status,
        }
        checked.append(record)
        if not flows_ok:
            rejection_reasons.append("simulated_monthly_surplus_below_target")
        if not runway_ok:
            rejection_reasons.append("minimum_emergency_fund_runway_not_met")
    best = next((item for item in checked if item["feasible"]), None)
    if best is None and enough_capacity and runway_floor is not None and runway_status == "checked":
        rejection_reasons.append("no_feasible_minimum_cost_vertex_passed_runway_constraint")
    if best is None and runway_floor is not None and runway_status != "checked":
        rejection_reasons.append("minimum_emergency_fund_runway_unassessed")
    if best is None and not enough_capacity:
        if outflow_floor > needed:
            rejection_reasons.append("configured_intervention_limits_cannot_meet_emergency_fund_runway_constraint")
        else:
            rejection_reasons.append("configured_intervention_limits_cannot_cover_required_adjustment")

    def money(value):
        return float(round_money(value))

    is_feasible = best is not None
    selected = best or (checked[0] if checked else None)
    intervention = selected or {
        "expense_reduction": ZERO, "proposed_emi_reduction": ZERO,
        "income_increase": ZERO, "total": ZERO,
    }
    if selected is not None:
        projection = selected["projection"]
        base_rows = baseline["baseline"]["months"]
        scenario_rows = projection["scenario"]["months"]
        differences = []
        for base, scenario in zip(base_rows, scenario_rows):
            differences.append({
                "month": base["month"],
                **{
                    key: (
                        money(Decimal(str(scenario[key])) - Decimal(str(base[key])))
                        if scenario[key] is not None and base[key] is not None else None
                    )
                    for key in (
                        "cash_flow_surplus", "liquid_savings", "emergency_fund",
                        "emergency_fund_runway_months", "tracked_net_worth",
                    )
                },
            })
    else:
        projection = None
        differences = []
    alternatives = []
    for candidate in checked:
        if candidate["feasible"] and candidate["total"] == minimum_total:
            alternatives.append({
                "expense_reduction": money(candidate["expense_reduction"]),
                "proposed_emi_reduction": money(candidate["proposed_emi_reduction"]),
                "income_increase": money(candidate["income_increase"]),
                "total_monthly_intervention": money(candidate["total"]),
            })
    result = {
        "feasible": is_feasible,
        "mathematical_feasibility": "feasible" if is_feasible else "infeasible",
        "goal": {"type": "monthly_cash_flow_surplus", "target_monthly_surplus": money(target)},
        "target_monthly_surplus": money(target),
        "baseline_outcome": {
            "monthly_cash_flow": baseline["baseline"]["months"][0]["cash_flow_surplus"],
            "projection": baseline["baseline"],
        },
        "scenario_monthly_cash_flow": money(scenario_flow),
        "required_adjustment": money(needed),
        "recommended_expense_reduction": money(intervention["expense_reduction"]),
        "recommended_new_emi_reduction": money(intervention["proposed_emi_reduction"]),
        "recommended_income_increase": money(intervention["income_increase"]),
        "total_proposed_adjustment": money(intervention["total"]),
        "remaining_shortfall": money(max(ZERO, needed - intervention["total"])),
        "optimized_monthly_cash_flow": money(scenario_flow + intervention["total"]),
        "expense_categories_provided": categories_provided,
        "essential_monthly_expenses": money(essential) if essential is not None else None,
        "discretionary_monthly_expenses": money(discretionary) if discretionary is not None else None,
        "method": "minimum_absolute_adjustment",
        "objective": "minimize expense_reduction + proposed_emi_reduction + income_increase, in INR per month",
        "tie_policy": "return every feasible minimum-cost extreme-point option found; choose lexicographically smallest (expense reduction, EMI reduction, income increase) for legacy single-option fields",
        "tied_minimum_options": alternatives,
        "search": {"strategy": "enumerate vertices of the minimum-cost feasible allocation polygon; validate every candidate with the multi-month simulator", "candidate_count": len(checked), "minimum_cost_found": money(minimum_total) if is_feasible else None, "global_optimality_claimed": False},
        "constraints_checked": {
            "user_configured_maximums": True,
            "expense_reduction_limited_to_user_supplied_discretionary_expenses": True,
            "proposed_emi_reduction_cannot_exceed_proposed_emi": True,
            "monthly_surplus_meets_target_in_every_projected_month": is_feasible,
            "minimum_emergency_fund_runway_months": money(runway_floor) if runway_floor is not None else None,
            "emergency_fund_runway_status": runway_status,
        },
        "rejected_candidate_reasons": sorted(set(rejection_reasons)),
        "baseline_projection": baseline["baseline"],
        "scenario_projection": projection["scenario"] if projection else None,
        "monthly_differences": differences,
        "affordability_assessment": "not_assessed",
        "assumptions": [
            "One INR of recurring expense reduction, proposed EMI reduction, or feasible income increase has equal objective cost.",
            "Income, expenses, and EMI remain flat over the projection horizon after the selected intervention.",
            "Simulator applies non-negative surplus to liquid savings; investments have no assumed returns.",
            "Existing debt is not amortized without explicit loan terms.",
        ],
        "limitations": [
            "Tied options are the feasible extreme points found by this search; interior tied combinations are not listed.",
            "The search is bounded by user-entered maximums and does not guarantee global optimality under all future constraints.",
            "Expense categories and income feasibility are user-supplied, not independently verified.",
            "Planned-purchase delay or budget optimization is unavailable because no planned purchase amount or valuation is stored.",
            "Projections depend on the supplied inputs and assumptions and are not financial advice.",
        ],
    }
    # Compatibility keys retained for existing clients.
    result["total_proposed_adjustment"] = money(intervention["total"])
    return result
