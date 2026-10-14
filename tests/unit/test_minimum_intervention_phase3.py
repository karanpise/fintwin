from copy import deepcopy
from decimal import Decimal

import pytest

from backend.api.routes.optimization import OptimizationRequest
from optimization.engine import optimize_monthly_cash_flow


def profile(**overrides):
    values = {
        "monthly_income": Decimal("50000.00"),
        "monthly_expenses": Decimal("30000.00"),
        "monthly_emi": Decimal("5000.00"),
        "total_savings": Decimal("10000.00"),
        "total_savings_reported": True,
        "emergency_fund": Decimal("5000.00"),
        "emergency_fund_reported": True,
        "investments": Decimal("4000.00"),
        "investments_reported": True,
        "total_debt": Decimal("20000.00"),
        "total_debt_reported": True,
    }
    values.update(overrides)
    return values


def test_goal_already_satisfied_has_zero_intervention_and_projection():
    result = optimize_monthly_cash_flow(profile(), target_monthly_surplus=Decimal("15000"))
    assert result["feasible"] is True
    assert result["total_proposed_adjustment"] == 0
    assert result["scenario_projection"]["months"][0]["cash_flow_surplus"] == 15000
    assert result["baseline_projection"]["months"][0]["cash_flow_surplus"] == 15000


def test_explicit_discretionary_reduction_is_simulated_and_compared():
    result = optimize_monthly_cash_flow(
        profile(), target_monthly_surplus=Decimal("20000"),
        max_expense_reduction=Decimal("7000"),
        essential_monthly_expenses=Decimal("25000"),
        discretionary_monthly_expenses=Decimal("5000"),
    )
    assert result["feasible"] is True
    assert result["recommended_expense_reduction"] == 5000
    assert result["recommended_income_increase"] == 0
    assert result["scenario_projection"]["months"][0]["cash_flow_surplus"] == 20000
    assert result["monthly_differences"][0]["liquid_savings"] == 5000
    assert result["monthly_differences"][0]["emergency_fund_runway_months"] > 0
    assert result["tied_minimum_options"] == [
        {"expense_reduction": 5000.0, "proposed_emi_reduction": 0.0,
         "income_increase": 0.0, "total_monthly_intervention": 5000.0}
    ]


def test_equal_cost_income_and_expense_alternatives_are_reported():
    result = optimize_monthly_cash_flow(
        profile(emergency_fund=Decimal("6000")), target_monthly_surplus=Decimal("20000"),
        max_expense_reduction=Decimal("5000"), max_income_increase=Decimal("5000"),
        essential_monthly_expenses=Decimal("25000"),
        discretionary_monthly_expenses=Decimal("5000"),
    )
    assert result["feasible"] is True
    assert len(result["tied_minimum_options"]) == 2
    assert result["tied_minimum_options"][0]["expense_reduction"] == 0
    assert result["tied_minimum_options"][0]["income_increase"] == 5000
    assert result["tied_minimum_options"][1]["expense_reduction"] == 5000


def test_no_feasible_candidate_reports_limit_reason():
    result = optimize_monthly_cash_flow(
        profile(), target_monthly_surplus=Decimal("20000"),
        max_income_increase=Decimal("1000"),
    )
    assert result["feasible"] is False
    assert result["remaining_shortfall"] == 4000
    assert "configured_intervention_limits_cannot_cover_required_adjustment" in result["rejected_candidate_reasons"]


def test_emi_reduction_is_capped_to_proposed_emi():
    result = optimize_monthly_cash_flow(
        profile(), additional_monthly_emi=Decimal("3000"),
        target_monthly_surplus=Decimal("15000"), max_emi_reduction=Decimal("9000"),
    )
    assert result["recommended_new_emi_reduction"] == 3000
    assert result["feasible"] is True


def test_invalid_missing_and_nonfinite_inputs_fail_validation():
    with pytest.raises(ValueError, match="monthly_income"):
        optimize_monthly_cash_flow({"monthly_expenses": 1, "monthly_emi": 0})
    with pytest.raises(ValueError):
        optimize_monthly_cash_flow(profile(), target_monthly_surplus=Decimal("NaN"))
    with pytest.raises(ValueError):
        optimize_monthly_cash_flow(profile(), max_income_increase=Decimal("1.001"))
    with pytest.raises(ValueError, match="horizon_months"):
        optimize_monthly_cash_flow(profile(), horizon_months=5)


def test_emergency_runway_constraint_selects_a_cut_or_reports_unassessed():
    result = optimize_monthly_cash_flow(
        profile(emergency_fund=Decimal("6000")), target_monthly_surplus=Decimal("20000"),
        max_expense_reduction=Decimal("5000"), max_income_increase=Decimal("5000"),
        essential_monthly_expenses=Decimal("25000"),
        discretionary_monthly_expenses=Decimal("5000"),
        minimum_emergency_fund_runway_months=Decimal("0.18"),
    )
    assert result["constraints_checked"]["emergency_fund_runway_status"] == "checked"
    assert result["feasible"] is True
    assert all(option["expense_reduction"] > 0 for option in result["tied_minimum_options"])

    missing = profile()
    missing["emergency_fund"] = None
    missing["emergency_fund_reported"] = False
    skipped = optimize_monthly_cash_flow(
        missing, target_monthly_surplus=Decimal("15000"),
        minimum_emergency_fund_runway_months=Decimal("3"),
    )
    assert skipped["feasible"] is False
    assert skipped["constraints_checked"]["emergency_fund_runway_status"] == "unassessed_missing_emergency_fund"


def test_runway_floor_rejects_income_only_solution_when_it_cannot_improve_outflow():
    result = optimize_monthly_cash_flow(
        profile(emergency_fund=Decimal("6000")),
        target_monthly_surplus=Decimal("20000"),
        max_income_increase=Decimal("5000"),
        minimum_emergency_fund_runway_months=Decimal("0.22"),
    )
    assert result["feasible"] is False
    assert result["tied_minimum_options"] == []
    assert "configured_intervention_limits_cannot_meet_emergency_fund_runway_constraint" in result["rejected_candidate_reasons"]


def test_immutability_repeatability_and_cent_rounding():
    source = profile(monthly_income=Decimal("50000.01"))
    before = deepcopy(source)
    kwargs = dict(
        target_monthly_surplus=Decimal("15000.02"),
        max_income_increase=Decimal("0.01"),
    )
    first = optimize_monthly_cash_flow(source, **kwargs)
    second = optimize_monthly_cash_flow(source, **kwargs)
    assert source == before
    assert first == second
    assert first["scenario_monthly_cash_flow"] == 15000.01
    assert first["optimized_monthly_cash_flow"] == 15000.02


def test_zero_income_and_zero_starting_balances_are_safe():
    result = optimize_monthly_cash_flow(
        profile(monthly_income=Decimal("0"), monthly_expenses=Decimal("0"),
                monthly_emi=Decimal("0"), total_savings=Decimal("0"),
                emergency_fund=Decimal("0"), investments=Decimal("0"), total_debt=Decimal("0")),
        target_monthly_surplus=Decimal("100"), max_income_increase=Decimal("100"),
        minimum_emergency_fund_runway_months=Decimal("3"),
    )
    assert result["recommended_income_increase"] == 100
    assert result["feasible"] is False
    assert result["constraints_checked"]["emergency_fund_runway_status"] == "unassessed_zero_monthly_outflow"


def test_unconfirmed_stored_emergency_fund_cannot_satisfy_configured_runway():
    result = optimize_monthly_cash_flow(
        profile(emergency_fund_reported=False),
        target_monthly_surplus=Decimal("15000"),
        minimum_emergency_fund_runway_months=Decimal("1"),
    )

    assert result["feasible"] is False
    assert result["constraints_checked"]["emergency_fund_runway_status"] == "unassessed_missing_emergency_fund"
    assert "minimum_emergency_fund_runway_unassessed" in result["rejected_candidate_reasons"]


def test_request_schema_validates_money_horizon_and_optional_runway():
    request = OptimizationRequest.model_validate({
        "target_monthly_surplus": "100.00", "horizon_months": 24,
        "minimum_emergency_fund_runway_months": "3.00",
    })
    assert request.horizon_months == 24
    with pytest.raises(ValueError):
        OptimizationRequest.model_validate({"max_income_increase": "1.001"})
    with pytest.raises(ValueError):
        OptimizationRequest.model_validate({"minimum_emergency_fund_runway_months": "NaN"})
    with pytest.raises(ValueError):
        OptimizationRequest.model_validate({"max_income_increase": True})
