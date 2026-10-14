
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from database.models import FinancialProfile, User
from optimization.engine import optimize_monthly_cash_flow
from financial_engine.monetary import parse_money


router = APIRouter(prefix="/me", tags=["Optimization"])


class OptimizationRequest(BaseModel):
    additional_monthly_emi: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )
    additional_monthly_expenses: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )
    target_monthly_surplus: Decimal = Field(
        default=Decimal("10000"),
        ge=0,
    )
    max_expense_reduction: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )
    max_emi_reduction: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )
    max_income_increase: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )

    essential_monthly_expenses: Decimal | None = Field(
        default=None,
        ge=0,
    )
    discretionary_monthly_expenses: Decimal | None = Field(
        default=None,
        ge=0,
    )
    horizon_months: int = Field(default=12, ge=3, le=60)
    minimum_emergency_fund_runway_months: Decimal | None = Field(default=None, ge=0, le=600)

    @field_validator(
        "additional_monthly_emi", "additional_monthly_expenses",
        "target_monthly_surplus", "max_expense_reduction", "max_emi_reduction",
        "max_income_increase", "essential_monthly_expenses",
        "discretionary_monthly_expenses",
        mode="before",
    )
    @classmethod
    def validate_money(cls, value, info):
        return None if value is None else parse_money(value, info.field_name)

    @field_validator("minimum_emergency_fund_runway_months", mode="before")
    @classmethod
    def validate_runway(cls, value, info):
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a numeric runway value.")
        amount = Decimal(str(value))
        if not amount.is_finite() or amount.quantize(Decimal("0.01")) != amount:
            raise ValueError(f"{info.field_name} must be finite and support at most two decimal places.")
        return amount

    @model_validator(mode="after")
    def validate_expense_categories(self):
        essential = self.essential_monthly_expenses
        discretionary = self.discretionary_monthly_expenses

        if (essential is None) != (discretionary is None):
            raise ValueError(
                "Provide both essential and discretionary expenses."
            )

        if essential is not None and discretionary is not None:
            if essential + discretionary < 0:
                raise ValueError("Expense categories cannot be negative.")

        return self


@router.post("/optimize")
def optimize(
    payload: OptimizationRequest,
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
            detail="Create your financial profile first.",
        )

    profile_data = {
        "monthly_income": profile.monthly_income,
        "monthly_expenses": profile.monthly_expenses,
        "monthly_emi": profile.monthly_emi,
        "total_savings": profile.total_savings,
        "total_savings_reported": profile.total_savings_reported,
        "emergency_fund": profile.emergency_fund,
        "emergency_fund_reported": profile.emergency_fund_reported,
        "investments": profile.investments,
        "investments_reported": profile.investments_reported,
        "total_debt": profile.total_debt,
        "total_debt_reported": profile.total_debt_reported,
    }

    essential = payload.essential_monthly_expenses
    discretionary = payload.discretionary_monthly_expenses

    if essential is not None and discretionary is not None:
        if essential + discretionary != profile.monthly_expenses:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Essential and discretionary expenses must sum "
                    "to your saved monthly expenses."
                ),
            )

    try:
        return optimize_monthly_cash_flow(
            profile_data,
            **payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
