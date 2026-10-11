
from optimization.engine import optimize_monthly_cash_flow


def test_minimum_intervention():
    profile = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
    }

    result = optimize_monthly_cash_flow(
        profile,
        additional_monthly_emi=10000,
        target_monthly_surplus=10000,
        max_expense_reduction=3000,
        max_emi_reduction=2000,
        essential_monthly_expenses=27000,
        discretionary_monthly_expenses=3000,
    )

    assert result["feasible"] is True
    assert result["recommended_expense_reduction"] == 3000
    assert result["recommended_new_emi_reduction"] == 2000
    assert result["optimized_monthly_cash_flow"] == 10000


def test_infeasible_scenario():
    profile = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
    }

    result = optimize_monthly_cash_flow(
        profile,
        additional_monthly_emi=10000,
        target_monthly_surplus=10000,
        max_expense_reduction=1000,
        max_emi_reduction=1000,
        essential_monthly_expenses=29000,
        discretionary_monthly_expenses=1000,
    )

    assert result["feasible"] is False
    assert result["remaining_shortfall"] == 3000


def test_no_adjustment_needed():
    profile = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
    }

    result = optimize_monthly_cash_flow(
        profile,
        target_monthly_surplus=10000,
    )

    assert result["feasible"] is True
    assert result["total_proposed_adjustment"] == 0
