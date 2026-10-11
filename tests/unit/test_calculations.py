
from types import SimpleNamespace

from financial_engine.calculations import calculate_financial_health


def make_profile(**overrides):
    data = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "total_savings": 100000,
        "emergency_fund": 60000,
        "investments": 25000,
        "total_debt": 80000,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_monthly_cash_flow():
    result = calculate_financial_health(make_profile())
    assert result["monthly_cash_flow"] == 15000


def test_savings_rate():
    result = calculate_financial_health(make_profile())
    assert result["savings_rate_percent"] == 30.0


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
    assert result["savings_rate_percent"] == -10.0
