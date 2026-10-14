from decimal import Decimal

import pytest

from simulation.engine import simulate_financial_scenario


@pytest.fixture
def profile():
    return {
        "monthly_income": Decimal("10000.00"),
        "monthly_expenses": Decimal("4000.00"),
        "monthly_emi": Decimal("1000.00"),
        "total_savings": Decimal("6000.00"),
        "total_savings_reported": True,
        "emergency_fund": Decimal("3000.00"),
        "emergency_fund_reported": True,
        "investments": Decimal("2000.00"),
        "investments_reported": True,
        "total_debt": Decimal("5000.00"),
        "total_debt_reported": True,
    }


def test_no_change_baseline_is_hand_calculated(profile):
    result = simulate_financial_scenario(
        profile,
        horizon_months=3,
        one_time_cost=Decimal("1000.00"),
        one_time_source="emergency_fund",
    )
    base = result["baseline"]
    assert [m["cash_flow_surplus"] for m in base["months"]] == [5000.0] * 3
    assert [m["liquid_savings"] for m in base["months"]] == [11000.0, 16000.0, 21000.0]
    assert base["cumulative_cash_flow_surplus"] == 15000.0
    assert base["ending_tracked_net_worth"] == 18000.0
    assert result["monthly_differences"][0]["cash_flow_surplus"] == 0.0


def test_income_increase_is_recurring(profile):
    result = simulate_financial_scenario(profile, horizon_months=3, recurring_income_change=1000)
    assert [m["cash_flow_surplus"] for m in result["scenario"]["months"]] == [6000.0] * 3
    assert result["scenario"]["ending_liquid_savings"] == 24000.0


def test_recurring_expense_increase(profile):
    result = simulate_financial_scenario(profile, horizon_months=3, recurring_expense_change=500)
    assert [m["cash_flow_surplus"] for m in result["scenario"]["months"]] == [4500.0] * 3
    assert result["scenario"]["ending_liquid_savings"] == 19500.0


def test_emi_increase_is_separate_from_expenses(profile):
    result = simulate_financial_scenario(profile, horizon_months=3, recurring_emi_change=300)
    month = result["scenario"]["months"][0]
    assert (month["expenses"], month["emi"], month["cash_flow_surplus"]) == (4000.0, 1300.0, 4700.0)


def test_one_time_major_cost_debits_liquid_savings_once(profile):
    result = simulate_financial_scenario(profile, horizon_months=3, one_time_cost=4000, one_time_month=2)
    assert [m["liquid_savings"] for m in result["scenario"]["months"]] == [11000.0, 12000.0, 17000.0]
    assert result["scenario"]["months"][1]["one_time_cost"] == 4000.0
    assert result["scenario"]["months"][1]["emergency_fund"] == 3000.0


def test_negative_cash_flow_depletes_liquid_then_emergency(profile):
    p = {**profile, "monthly_income": 5000, "monthly_expenses": 4000, "monthly_emi": 2000,
         "total_savings": 500, "emergency_fund": 200}
    projection = simulate_financial_scenario(p, horizon_months=3)["scenario"]
    assert projection["negative_cash_flow_months"] == [1, 2, 3]
    assert projection["first_liquid_savings_depleted_month"] == 1
    assert projection["first_emergency_fund_depleted_month"] == 1
    assert projection["months"][0]["liquid_savings"] == 0
    assert projection["months"][0]["unfunded_cash_flow_deficit"] == 500.0


def test_zero_income_and_zero_balances_are_safe():
    p = {"monthly_income": 0, "monthly_expenses": 0, "monthly_emi": 0,
         "total_savings": 0, "emergency_fund": 0, "investments": 0, "total_debt": 0,
         "total_savings_reported": True, "emergency_fund_reported": True,
         "investments_reported": True, "total_debt_reported": True}
    result = simulate_financial_scenario(p, horizon_months=3)
    assert result["scenario"]["months"][0]["cash_flow_surplus"] == 0
    assert result["scenario"]["first_liquid_savings_depleted_month"] == 0
    assert result["scenario"]["months"][0]["emergency_fund_runway_months"] is None


def test_missing_optional_balances_remain_unknown():
    p = {"monthly_income": 100, "monthly_expenses": 50, "monthly_emi": 10}
    result = simulate_financial_scenario(p, horizon_months=3)
    month = result["scenario"]["months"][0]
    assert month["liquid_savings"] is None
    assert month["emergency_fund"] is None
    assert month["tracked_net_worth"] is None
    assert result["monthly_differences"][0]["liquid_savings"] is None


def test_unconfirmed_legacy_balances_do_not_enter_projection_state(profile):
    profile.update({
        "total_savings_reported": False,
        "emergency_fund_reported": False,
        "investments_reported": False,
        "total_debt_reported": False,
    })

    result = simulate_financial_scenario(
        profile,
        horizon_months=3,
        one_time_cost=Decimal("1000.00"),
        one_time_source="emergency_fund",
    )
    month = result["scenario"]["months"][0]

    # Legacy top-level snapshot amount remains visible for old clients, while
    # every derived projection uses only explicitly confirmed balances.
    assert result["baseline_emergency_fund"] == 3000.0
    assert result["emergency_fund_reported"] is False
    assert result["reported_baseline_balances"] == {
        "total_savings": None,
        "emergency_fund": None,
        "investments": None,
        "total_debt": None,
    }
    assert month["liquid_savings"] is None
    assert month["emergency_fund"] is None
    assert month["investments"] is None
    assert month["debt"] is None
    assert month["emergency_fund_runway_months"] is None
    assert month["tracked_net_worth"] is None
    assert month["unfunded_cost"] == 1000.0


def test_baseline_and_scenario_share_initial_position_and_compare(profile):
    result = simulate_financial_scenario(profile, horizon_months=3, recurring_expense_change=100)
    assert result["baseline"]["months"][0]["liquid_savings"] == 11000
    assert result["scenario"]["months"][0]["liquid_savings"] == 10900
    assert result["monthly_differences"][0]["cash_flow_surplus"] == -100
    assert profile["total_savings"] == Decimal("6000.00")


def test_repeatability_and_half_up_rounding(profile):
    first = simulate_financial_scenario(profile, horizon_months=3, recurring_income_change=Decimal("0.01"))
    second = simulate_financial_scenario(profile, horizon_months=3, recurring_income_change=Decimal("0.01"))
    assert first == second
    p = {"monthly_income": 3, "monthly_expenses": 1, "monthly_emi": 0}
    result = simulate_financial_scenario(p, horizon_months=3)
    assert result["scenario"]["months"][0]["cash_flow_surplus"] == 2.0


def test_legacy_upfront_contract_reports_shortfall_without_negative_balance(profile):
    result = simulate_financial_scenario(profile, additional_upfront_cost=7000, horizon_months=3)
    assert result["scenario_has_insufficient_upfront_funds"] is True
    assert result["scenario"]["months"][0]["unfunded_cost"] == 4000.0
    result = simulate_financial_scenario(profile, additional_upfront_cost=20000, horizon_months=3)
    assert result["scenario_has_insufficient_upfront_funds"] is True
    assert result["scenario"]["months"][0]["liquid_savings"] == 8000.0
    assert result["scenario"]["months"][0]["unfunded_cost"] == 17000.0


def test_rejects_invalid_inputs_and_horizon(profile):
    with pytest.raises(ValueError, match="cannot be negative"):
        simulate_financial_scenario(profile, additional_monthly_emi=-1)
    with pytest.raises(ValueError, match="finite"):
        simulate_financial_scenario(profile, additional_monthly_expenses=float("nan"))
    with pytest.raises(ValueError, match="horizon_months"):
        simulate_financial_scenario(profile, horizon_months=5)
    with pytest.raises(ValueError, match="exceed"):
        simulate_financial_scenario({**profile, "emergency_fund": 7000})
    with pytest.raises(ValueError, match="between 0 and 100"):
        simulate_financial_scenario(profile, new_loan_annual_rate_percent=101)


def test_new_loan_amortizes_only_with_supplied_terms(profile):
    result = simulate_financial_scenario(
        profile, horizon_months=3, new_loan_principal=1200,
        new_loan_annual_rate_percent=0, new_loan_term_months=3,
    )
    loan_months = result["scenario"]["months"]
    assert [m["new_loan_principal_paid"] for m in loan_months] == [400.0, 400.0, 400.0]
    assert [m["new_loan_interest"] for m in loan_months] == [0.0, 0.0, 0.0]


def test_new_loan_uses_cent_half_up_rounding(profile):
    result = simulate_financial_scenario(
        profile, horizon_months=3, new_loan_principal=1000,
        new_loan_annual_rate_percent=12, new_loan_term_months=3,
    )
    first = result["scenario"]["months"][0]
    assert first["emi"] == 1340.02
    assert first["new_loan_interest"] == 10.0
    assert first["new_loan_principal_paid"] == 330.02
    assert first["debt"] == 5669.98
