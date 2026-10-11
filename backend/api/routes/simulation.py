
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from database.models import FinancialProfile, User
from simulation.engine import simulate_financial_scenario

router = APIRouter(prefix="/me", tags=["What-If Simulation"])


class SimulationRequest(BaseModel):
    additional_monthly_emi: Decimal = Field(default=Decimal("0"), ge=0)
    additional_monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0)
    additional_upfront_cost: Decimal = Field(default=Decimal("0"), ge=0)
    
    scenario_monthly_income: Decimal | None = Field(default=None, ge=0)
    scenario_monthly_expenses: Decimal | None = Field(default=None, ge=0)
    scenario_monthly_emi: Decimal | None = Field(default=None, ge=0)



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
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
