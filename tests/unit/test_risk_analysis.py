
from decimal import Decimal

import pytest

from financial_engine.risk_analysis import analyze_financial_risk


def make_profile(**overrides):
    data = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "emergency_fund": 60000,
        "emergency_fund_reported": True,
        "total_debt": 80000,
        "total_debt_reported": True,
    }
    data.update(overrides)
    return data


def test_emergency_fund_shortfall_is_flagged():
    result = analyze_financial_risk(make_profile())
    assert result["risk_level"] == "Medium"
    assert any(
        "Emergency fund" in factor
        for factor in result["risk_factors"]
    )


def test_negative_cash_flow_is_flagged():
    result = analyze_financial_risk(
        make_profile(monthly_expenses=55000)
    )
    assert result["monthly_cash_flow"] < 0
    assert result["risk_level"] == "High"



def test_no_income_is_flagged():
    result = analyze_financial_risk(make_profile(monthly_income=0))

    assert result["risk_level"] == "High"
    assert any(
        "income" in factor.lower()
        for factor in result["risk_factors"]
    )



def test_healthy_baseline_has_no_triggers():
    result = analyze_financial_risk(
        make_profile(
            monthly_income=100000,
            monthly_expenses=20000,
            monthly_emi=5000,
            emergency_fund=300000,
            total_debt=100000,
        )
    )
    assert result["risk_level"] == "Low"
    assert result["risk_factors"] == []


def test_risk_uses_shared_cash_flow_and_emi_definitions():
    result = analyze_financial_risk(make_profile())

    # Hand calculation: 50,000 - 30,000 - 5,000 = 15,000;
    # EMI / income = 5,000 / 50,000 = 10%.
    assert result["monthly_cash_flow"] == 15000.0
    assert result["cash_flow_surplus_rate_percent"] == 30.0
    assert result["emi_to_income_percent"] == 10.0
    assert result["debt_to_income_percent"] == 10.0


def test_missing_optional_risk_balances_are_not_treated_as_zero():
    profile = make_profile()
    profile["emergency_fund"] = None
    profile["emergency_fund_reported"] = False
    profile["total_debt"] = None
    profile["total_debt_reported"] = False

    result = analyze_financial_risk(profile)

    assert result["emergency_fund_months"] is None
    assert result["assessment_completeness"] == "partial"


def test_unconfirmed_emergency_fund_and_debt_are_unassessed():
    profile = make_profile(
        emergency_fund_reported=False,
        total_debt_reported=False,
    )

    result = analyze_financial_risk(profile)

    assert result["emergency_fund_months"] is None
    assert result["reported_emergency_fund"] is None
    assert result["reported_total_debt"] is None
    assert result["emergency_fund_reported"] is False
    assert result["total_debt_reported"] is False
    assert "emergency fund coverage" in result["unassessed_factors"]
    assert "outstanding debt level" in result["unassessed_factors"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("monthly_income", float("inf")),
        ("monthly_expenses", -1),
        ("monthly_emi", Decimal("1.001")),
    ],
)
def test_invalid_risk_inputs_are_rejected(field, value):
    with pytest.raises(ValueError):
        analyze_financial_risk(make_profile(**{field: value}))
