
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from database.models import FinancialProfile, User
from financial_engine.risk_analysis import analyze_financial_risk

router = APIRouter(prefix="/me", tags=["Financial Risk"])


@router.get("/risk-analysis")
def get_risk_analysis(
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
            detail="Create your financial profile before running risk analysis.",
        )

    profile_data = {
        "monthly_income": profile.monthly_income,
        "monthly_expenses": profile.monthly_expenses,
        "monthly_emi": profile.monthly_emi,
        "emergency_fund": profile.emergency_fund,
        "total_debt": profile.total_debt,
    }

    result = analyze_financial_risk(profile_data)
    return result
