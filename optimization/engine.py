
from decimal import Decimal


def optimize_monthly_cash_flow(
    profile: dict,
    additional_monthly_emi: Decimal = Decimal("0"),
    additional_monthly_expenses: Decimal = Decimal("0"),
    target_monthly_surplus: Decimal = Decimal("10000"),
    max_expense_reduction: Decimal = Decimal("0"),
    max_emi_reduction: Decimal = Decimal("0"),
    max_income_increase: Decimal = Decimal("0"),
    essential_monthly_expenses: Decimal | None = None,
    discretionary_monthly_expenses: Decimal | None = None,
) -> dict:
    """
    Optimize monthly cash flow using user-specified adjustment limits.

    Expense reduction is prioritized, followed by proposed EMI
    reduction and income increase.

    When expense categories are provided, expense reductions are
    capped at discretionary spending. Category values are inputs
    for the scenario, not independently verified facts.
    """

    def dec(value):
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError(
                "Financial inputs must be finite numbers."
            )
        return result

    income = dec(profile["monthly_income"])
    expenses = dec(profile["monthly_expenses"])
    existing_emi = dec(profile["monthly_emi"])

    new_emi = dec(additional_monthly_emi)
    new_expenses = dec(additional_monthly_expenses)
    target = dec(target_monthly_surplus)

    expense_limit = dec(max_expense_reduction)
    emi_limit = dec(max_emi_reduction)
    income_limit = dec(max_income_increase)

    values = [
        income,
        expenses,
        existing_emi,
        new_emi,
        new_expenses,
        target,
        expense_limit,
        emi_limit,
        income_limit,
    ]

    if any(value < 0 for value in values):
        raise ValueError("Financial inputs must be non-negative.")

    categories_provided = (
        essential_monthly_expenses is not None
        or discretionary_monthly_expenses is not None
    )

    essential = None
    discretionary = None

    if categories_provided:
        if (
            essential_monthly_expenses is None
            or discretionary_monthly_expenses is None
        ):
            raise ValueError(
                "Provide both essential and discretionary expenses."
            )

        essential = dec(essential_monthly_expenses)
        discretionary = dec(discretionary_monthly_expenses)

        if essential < 0 or discretionary < 0:
            raise ValueError(
                "Expense categories must be non-negative."
            )

        if essential + discretionary != expenses:
            raise ValueError(
                "Essential and discretionary expenses must sum "
                "to the saved monthly expenses."
            )

        # Do not recommend cutting essential expenses.
        expense_limit = min(
            expense_limit,
            discretionary,
        )
    else:
        # Without categories, a discretionary-only recommendation
        # cannot be established. Disable expense reduction.
        expense_limit = Decimal("0")

    # EMI reduction applies only to the proposed additional EMI.
    emi_limit = min(emi_limit, new_emi)

    scenario_cash_flow = (
        income
        - expenses
        - existing_emi
        - new_emi
        - new_expenses
    )

    shortfall = max(
        Decimal("0"),
        target - scenario_cash_flow,
    )

    expense_reduction = min(shortfall, expense_limit)
    remaining = shortfall - expense_reduction

    emi_reduction = min(remaining, emi_limit)
    remaining -= emi_reduction

    income_increase = min(remaining, income_limit)
    remaining -= income_increase

    feasible = remaining == 0

    total_adjustment = (
        expense_reduction
        + emi_reduction
        + income_increase
    )

    optimized_cash_flow = (
        scenario_cash_flow + total_adjustment
    )

    def money(value):
        return round(float(value), 2)

    return {
        "feasible": feasible,
        "mathematical_feasibility": (
            "feasible" if feasible else "infeasible"
        ),
        "target_monthly_surplus": money(target),
        "scenario_monthly_cash_flow": money(
            scenario_cash_flow
        ),
        "required_adjustment": money(shortfall),
        "recommended_expense_reduction": money(
            expense_reduction
        ),
        "recommended_new_emi_reduction": money(
            emi_reduction
        ),
        "recommended_income_increase": money(
            income_increase
        ),
        "total_proposed_adjustment": money(
            total_adjustment
        ),
        "remaining_shortfall": money(remaining),
        "optimized_monthly_cash_flow": money(
            optimized_cash_flow
        ),
        "expense_categories_provided": categories_provided,
        "essential_monthly_expenses": (
            money(essential) if essential is not None else None
        ),
        "discretionary_monthly_expenses": (
            money(discretionary)
            if discretionary is not None
            else None
        ),
        "affordability_assessment": "not_assessed",
        "method": "minimum_absolute_adjustment",
        "limitations": [
            "Expense categories are supplied by the user "
            "and are not independently verified.",
            "Income increases and expense reductions may not "
            "be achievable in practice.",
            "Mathematical feasibility does not guarantee "
            "real-world affordability.",
        ],
    }
