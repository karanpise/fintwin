
from decimal import Decimal

import pytest

from optimization.engine import optimize_monthly_cash_flow


def make_profile():
    return {
        "monthly_income": Decimal("50000"),
        "monthly_expenses": Decimal("30000"),
        "monthly_emi": Decimal("5000"),
    }


def test_expense_reduction_stays_within_discretionary_limit():
    result = optimize_monthly_cash_flow(
        profile=make_profile(),
        target_monthly_surplus=Decimal("20000"),
        max_expense_reduction=Decimal("10000"),
        essential_monthly_expenses=Decimal("22000"),
        discretionary_monthly_expenses=Decimal("8000"),
    )

    assert result["recommended_expense_reduction"] <= Decimal("8000")
    assert result["recommended_expense_reduction"] == Decimal("5000")
    assert result["feasible"] is True


def test_expense_categories_must_match_total_expenses():
    with pytest.raises(ValueError):
        optimize_monthly_cash_flow(
            profile=make_profile(),
            essential_monthly_expenses=Decimal("20000"),
            discretionary_monthly_expenses=Decimal("5000"),
        )


def test_optimizer_does_not_reduce_expenses_without_categories():
    result = optimize_monthly_cash_flow(
        profile=make_profile(),
        target_monthly_surplus=Decimal("20000"),
        max_expense_reduction=Decimal("10000"),
        max_income_increase=Decimal("10000"),
    )

    assert result["recommended_expense_reduction"] == Decimal("0")
    assert result["feasible"] is True



def test_emi_reduction_cannot_exceed_additional_emi():
    result = optimize_monthly_cash_flow(
        profile=make_profile(),
        additional_monthly_emi=Decimal("3000"),
        target_monthly_surplus=Decimal("20000"),
        max_emi_reduction=Decimal("10000"),
    )

    assert result["recommended_new_emi_reduction"] <= Decimal("3000")
    assert result["recommended_new_emi_reduction"] == Decimal("3000")



def test_optimizer_reports_unachievable_target():
    result = optimize_monthly_cash_flow(
        profile=make_profile(),
        target_monthly_surplus=Decimal("50000"),
    )

    assert result["feasible"] is False
    assert result["remaining_shortfall"] > Decimal("0")
