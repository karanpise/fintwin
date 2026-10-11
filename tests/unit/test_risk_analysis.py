
from financial_engine.risk_analysis import analyze_financial_risk


def make_profile(**overrides):
    data = {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "emergency_fund": 60000,
        "total_debt": 80000,
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
