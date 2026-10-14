
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from backend.schemas.financial_profile import (
    FinancialProfileCreate,
    FinancialProfileResponse,
    missing_monthly_baseline_fields,
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

    # Validate the complete candidate state, including fields omitted by a
    # partial update, before mutating the ORM object.
    candidate = {}
    for field in ("total_savings", "emergency_fund"):
        candidate[field] = (
            getattr(payload, field)
            if field in payload.model_fields_set
            else getattr(profile, field, 0)
        )
    for field in ("total_savings", "emergency_fund"):
        status_field = f"{field}_reported"
        candidate[status_field] = (
            getattr(payload, status_field)
            if status_field in payload.model_fields_set
            else getattr(profile, status_field, False)
        )
    if (
        candidate["total_savings_reported"]
        and candidate["emergency_fund_reported"]
        and candidate["emergency_fund"] > candidate["total_savings"]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A reported emergency fund cannot exceed reported liquid savings.",
        )

    if profile is None:
        missing_fields = missing_monthly_baseline_fields(payload)
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Provide monthly take-home income, monthly expenses "
                    "excluding EMI, and monthly EMI when creating a profile. "
                    f"Missing: {', '.join(missing_fields)}."
                ),
            )
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
