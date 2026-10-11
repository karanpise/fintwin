
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from backend.schemas.financial_profile import (
    FinancialProfileCreate,
    FinancialProfileResponse,
)
from database.models import FinancialProfile, User

router = APIRouter(
    prefix="/me",
    tags=["Financial Profiles"],
)


@router.put(
    "/financial-profile",
    response_model=FinancialProfileResponse,
)
def save_financial_profile(
    payload: FinancialProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(FinancialProfile)
        .filter(FinancialProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile


@router.get(
    "/financial-profile",
    response_model=FinancialProfileResponse,
)
def get_financial_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(FinancialProfile)
        .filter(FinancialProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial profile not found",
        )

    return profile
