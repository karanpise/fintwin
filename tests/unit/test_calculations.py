
from types import SimpleNamespace
from decimal import Decimal

import pytest

from financial_engine.calculations import calculate_financial_health


def make_profile(**overrides):
    data = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "total_savings": 100000,
        "total_savings_reported": True,
        "emergency_fund": 60000,
        "emergency_fund_reported": True,
        "investments": 25000,
        "investments_reported": True,
        "total_debt": 80000,
        "total_debt_reported": True,
        "monthly_savings": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_monthly_cash_flow():
    result = calculate_financial_health(make_profile())
    assert result["monthly_cash_flow"] == 15000


def test_savings_rate():
    result = calculate_financial_health(make_profile())
    assert result["cash_flow_surplus_rate_percent"] == 30.0
    assert result["actual_savings_rate_percent"] is None
    # Kept for compatibility with existing API consumers.
    assert result["savings_rate_percent"] == 30.0


def test_actual_savings_rate_is_reported_separately_from_surplus():
    result = calculate_financial_health(
        make_profile(monthly_savings=Decimal("7500.00"))
    )

    # Hand calculation: 7,500 / 50,000 = 15%;
    # cash-flow surplus is (50,000 - 30,000 - 5,000) / 50,000 = 30%.
    assert result["actual_savings_rate_percent"] == 15.0
    assert result["cash_flow_surplus_rate_percent"] == 30.0


def test_debt_to_income_ratio():
    result = calculate_financial_health(make_profile())
    assert result["debt_to_income_percent"] == 10.0


def test_zero_income():
    result = calculate_financial_health(make_profile(monthly_income=0))
    assert result["savings_rate_percent"] is None
    assert result["debt_to_income_percent"] is None


def test_emergency_fund_coverage():
    result = calculate_financial_health(make_profile())
    assert result["emergency_fund_months"] == 1.71


def test_balance_taxonomy_avoids_counting_emergency_fund_twice():
    result = calculate_financial_health(
        make_profile(
            total_savings=Decimal("120000.00"),
            emergency_fund=Decimal("60000.00"),
            investments=Decimal("25000.00"),
            total_debt=Decimal("80000.00"),
        )
    )

    # Liquid savings already includes the 60,000 emergency fund.
    # Tracked assets = 120,000 + 25,000; tracked net worth = 145,000 - 80,000.
    assert result["tracked_financial_assets"] == 145000.0
    assert result["tracked_financial_liabilities"] == 80000.0
    assert result["tracked_net_worth"] == 65000.0
    assert result["net_worth_completeness"] == "partial"
    assert "property and other unreported assets" in result[
        "net_worth_missing_components"
    ]


def test_zero_monthly_outflow():
    result = calculate_financial_health(
        make_profile(
            monthly_expenses=0,
            monthly_emi=0,
            emergency_fund=60000,
        )
    )

    # Coverage is undefined when there is no monthly outflow.
    assert result["emergency_fund_months"] is None


def test_negative_monthly_cash_flow():
    result = calculate_financial_health(
        make_profile(
            monthly_income=50000,
            monthly_expenses=50000,
            monthly_emi=5000,
        )
    )

    assert result["monthly_cash_flow"] == -5000
    assert result["cash_flow_surplus_rate_percent"] == -10.0
    assert result["savings_rate_percent"] == -10.0


@pytest.mark.parametrize(
    "value",
    [None, Decimal("NaN"), Decimal("Infinity"), Decimal("-1"),
     Decimal("1000000000000.00"), Decimal("1.001")],
)
def test_invalid_required_money_is_rejected(value):
    with pytest.raises(ValueError):
        calculate_financial_health(make_profile(monthly_income=value))


def test_missing_required_monthly_value_is_rejected():
    profile = make_profile()
    del profile.monthly_expenses

    with pytest.raises(ValueError, match="monthly_expenses.*missing"):
        calculate_financial_health(profile)


def test_missing_optional_monthly_savings_remains_unknown():
    profile = make_profile()
    del profile.monthly_savings

    result = calculate_financial_health(profile)
    assert result["monthly_savings"] is None
    assert result["actual_savings_rate_percent"] is None


def test_optional_missing_balances_are_not_used_as_zero_assets():
    profile = make_profile()
    del profile.total_savings
    del profile.investments
    del profile.total_debt
    profile.total_savings_reported = False
    profile.investments_reported = False
    profile.total_debt_reported = False

    result = calculate_financial_health(profile)

    assert result["liquid_savings"] is None
    assert result["investments"] is None
    assert result["total_debt"] is None
    assert result["tracked_financial_assets"] is None
    assert result["tracked_net_worth"] is None


def test_balance_amount_without_reporting_flag_remains_unknown():
    profile = {
        "monthly_income": 10000,
        "monthly_expenses": 4000,
        "monthly_emi": 1000,
        "total_savings": 0,
        "emergency_fund": 0,
        "investments": 0,
        "total_debt": 0,
    }

    result = calculate_financial_health(profile)

    assert result["reported_total_savings"] is None
    assert result["reported_emergency_fund"] is None
    assert result["reported_investments"] is None
    assert result["reported_total_debt"] is None
    assert result["emergency_fund_months"] is None
    assert result["tracked_net_worth"] is None


def test_unconfirmed_stored_amounts_remain_legacy_visible_but_not_calculated():
    result = calculate_financial_health(
        make_profile(
            total_savings_reported=False,
            emergency_fund_reported=False,
            investments_reported=False,
            total_debt_reported=False,
        )
    )

    assert result["total_savings"] == 100000.0  # Legacy response value retained.
    assert result["reported_total_savings"] is None
    assert result["reported_emergency_fund"] is None
    assert result["reported_investments"] is None
    assert result["reported_total_debt"] is None
    assert result["liquid_savings"] is None
    assert result["emergency_fund_months"] is None
    assert result["tracked_financial_assets"] is None
    assert result["tracked_net_worth"] is None
    assert result["total_savings_reported"] is False


def test_explicitly_reported_zero_is_distinct_from_unknown():
    result = calculate_financial_health(
        make_profile(
            total_savings=Decimal("0.00"),
            emergency_fund=Decimal("0.00"),
            investments=Decimal("0.00"),
            total_debt=Decimal("0.00"),
            total_savings_reported=True,
            emergency_fund_reported=True,
            investments_reported=True,
            total_debt_reported=True,
        )
    )

    assert result["reported_total_savings"] == 0.0
    assert result["reported_emergency_fund"] == 0.0
    assert result["emergency_fund_months"] == 0.0
    assert result["tracked_financial_assets"] == 0.0
    assert result["tracked_financial_liabilities"] == 0.0
    assert result["tracked_net_worth"] == 0.0


def test_partial_tracked_net_worth_does_not_treat_unknown_balance_as_zero():
    result = calculate_financial_health(
        make_profile(
            total_savings=Decimal("100000.00"),
            investments=Decimal("25000.00"),
            total_debt=Decimal("80000.00"),
            total_savings_reported=True,
            emergency_fund_reported=False,
            investments_reported=True,
            total_debt_reported=False,
        )
    )

    # Known assets are surfaced, but unknown debt prevents a net-worth value.
    assert result["tracked_financial_assets"] == 125000.0
    assert result["tracked_financial_liabilities"] is None
    assert result["tracked_net_worth"] is None
    assert "outstanding debt" in result["net_worth_missing_components"]


def test_ratio_rounding_uses_decimal_half_up():
    result = calculate_financial_health(
        make_profile(
            monthly_income=Decimal("3.00"),
            monthly_expenses=Decimal("2.50"),
            monthly_emi=Decimal("0.00"),
            monthly_savings=Decimal("0.50"),
        )
    )

    assert result["cash_flow_surplus_rate_percent"] == 16.67
    assert result["actual_savings_rate_percent"] == 16.67
