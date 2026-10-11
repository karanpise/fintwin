
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from database.models import FinancialProfile, User
from optimization.engine import optimize_monthly_cash_flow


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
