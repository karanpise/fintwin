
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from database.models import FinancialProfile, User
from simulation.engine import simulate_financial_scenario
from financial_engine.monetary import parse_money

router = APIRouter(prefix="/me", tags=["What-If Simulation"])


class SimulationRequest(BaseModel):
    horizon_months: Literal[3, 6, 12, 24, 60] = 12
    additional_monthly_emi: Decimal = Field(default=Decimal("0"), ge=0)
    additional_monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0)
    additional_upfront_cost: Decimal = Field(default=Decimal("0"), ge=0)
    
    scenario_monthly_income: Decimal | None = Field(default=None, ge=0)
    scenario_monthly_expenses: Decimal | None = Field(default=None, ge=0)
    scenario_monthly_emi: Decimal | None = Field(default=None, ge=0)
    recurring_income_change: Decimal = Decimal("0")
    recurring_expense_change: Decimal = Decimal("0")
    recurring_emi_change: Decimal = Decimal("0")
    changes_start_month: int = Field(default=1, ge=1, le=60)
    one_time_cost: Decimal | None = Field(default=None, ge=0)
    one_time_month: int = Field(default=1, ge=1, le=60)
    one_time_source: str | None = None
    apply_surplus_to_savings: bool = True
    new_loan_principal: Decimal = Field(default=Decimal("0"), ge=0)
    new_loan_annual_rate_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    new_loan_term_months: int = Field(default=0, ge=0, le=600)
    new_loan_start_month: int = Field(default=1, ge=1, le=60)

    @field_validator(
        "additional_monthly_emi", "additional_monthly_expenses", "additional_upfront_cost",
        "scenario_monthly_income", "scenario_monthly_expenses", "scenario_monthly_emi",
        "one_time_cost", "new_loan_principal",
    )
    @classmethod
    def validate_money(cls, value, info):
        return None if value is None else parse_money(value, info.field_name)

    @field_validator("recurring_income_change", "recurring_expense_change", "recurring_emi_change")
    @classmethod
    def validate_change(cls, value, info):
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > Decimal("999999999999.99") or amount.quantize(Decimal("0.01")) != amount:
            raise ValueError(f"{info.field_name} must be finite and support at most two decimal places.")
        return amount



@router.post("/simulate")
def simulate(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.scalar(
        select(FinancialProfile).where(
            FinancialProfile.user_id == current_user.id
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Create your financial profile before running a simulation.",
        )

    profile_data = {
        "monthly_income": profile.monthly_income,
        "monthly_expenses": profile.monthly_expenses,
        "monthly_emi": profile.monthly_emi,
        "emergency_fund": profile.emergency_fund,
        "emergency_fund_reported": profile.emergency_fund_reported,
        "total_savings": profile.total_savings,
        "total_savings_reported": profile.total_savings_reported,
        "investments": profile.investments,
        "investments_reported": profile.investments_reported,
        "total_debt": profile.total_debt,
        "total_debt_reported": profile.total_debt_reported,
    }

    try:
        return simulate_financial_scenario(
            profile_data,
            additional_monthly_emi=payload.additional_monthly_emi,
            additional_monthly_expenses=payload.additional_monthly_expenses,
            additional_upfront_cost=payload.additional_upfront_cost,
            scenario_monthly_income=payload.scenario_monthly_income,
            scenario_monthly_expenses=payload.scenario_monthly_expenses,
            scenario_monthly_emi=payload.scenario_monthly_emi,
            horizon_months=payload.horizon_months,
            recurring_income_change=payload.recurring_income_change,
            recurring_expense_change=payload.recurring_expense_change,
            recurring_emi_change=payload.recurring_emi_change,
            changes_start_month=payload.changes_start_month,
            one_time_cost=payload.one_time_cost,
            one_time_month=payload.one_time_month,
            one_time_source=payload.one_time_source,
            apply_surplus_to_savings=payload.apply_surplus_to_savings,
            new_loan_principal=payload.new_loan_principal,
            new_loan_annual_rate_percent=payload.new_loan_annual_rate_percent,
            new_loan_term_months=payload.new_loan_term_months,
            new_loan_start_month=payload.new_loan_start_month,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
