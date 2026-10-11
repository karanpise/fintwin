from decimal import Decimal

import pytest

from simulation.engine import simulate_financial_scenario


@pytest.fixture
def profile():
    return {
        "monthly_income": 50000,
        "monthly_expenses": 30000,
        "monthly_emi": 5000,
        "emergency_fund": 60000,
    }


def test_simulation_calculates_cash_flow_and_emergency_fund(profile):
    result = simulate_financial_scenario(
        profile,
        additional_monthly_emi=1000,
        additional_monthly_expenses=2000,
        additional_upfront_cost=10000,
    )

    assert result["baseline_monthly_cash_flow"] == 15000
    assert result["scenario_monthly_cash_flow"] == 12000
    assert result["monthly_cash_flow_change"] == -3000
    assert result["scenario_emergency_fund"] == 50000
    assert result["scenario_emergency_fund_months"] == 1.32
    assert result["scenario_has_insufficient_upfront_funds"] is False


def test_simulation_flags_insufficient_upfront_funds(profile):
    result = simulate_financial_scenario(
        profile,
        additional_upfront_cost=70000,
    )

    assert result["scenario_emergency_fund"] == -10000
    assert result["scenario_has_insufficient_upfront_funds"] is True
    assert result["scenario_emergency_fund_months"] is None


def test_simulation_rejects_negative_amounts(profile):
    with pytest.raises(ValueError, match="cannot be negative"):
        simulate_financial_scenario(
            profile,
            additional_upfront_cost=-1,
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_simulation_rejects_non_finite_amounts(profile, value):
    with pytest.raises(ValueError, match="finite"):
        simulate_financial_scenario(
            profile,
            additional_monthly_expenses=value,
        )


def test_simulation_does_not_mutate_profile(profile):
    original = profile.copy()

    simulate_financial_scenario(
        profile,
        additional_monthly_expenses=1000,
    )

    assert profile == original
