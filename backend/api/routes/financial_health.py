
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from database.models import FinancialProfile, User
from financial_engine.calculations import calculate_financial_health

router = APIRouter(
    prefix="/me",
    tags=["Financial Health"],
)


@router.get("/financial-health")
def get_financial_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return deterministic metrics using take-home income.

    `monthly_expenses` excludes EMI, which is counted separately. The response
    keeps legacy rate keys and adds explicit names for surplus and actual
    reported savings. Net worth is limited to tracked balances and marked
    partial because other assets and liabilities are not collected.
    """
    profile = (
        db.query(FinancialProfile)
        .filter(FinancialProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create your financial profile first",
        )

    return calculate_financial_health(profile)
