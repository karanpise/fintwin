
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from backend.dependencies.auth import get_current_user
from database.models import User
from ml.inference.predict import predict_financial_risk

router = APIRouter(prefix="/ml", tags=["ML Risk Prediction"])


class RiskPredictionRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description=(
            "Feature values matching the columns used to train "
            "the model. Exclude customer_id, risk_score, "
            "recommended_intervention, derived ratios, and financial_risk."
        ),
    )


@router.post("/predict-risk")
def predict_risk(
    payload: RiskPredictionRequest,
    current_user: User = Depends(get_current_user),
):
    # Keep authentication enforced by get_current_user.
    if not isinstance(payload.features, dict):
        raise HTTPException(
            status_code=422,
            detail="features must be a dictionary.",
        )

    try:
        result = predict_financial_risk(payload.features)
        return jsonable_encoder(result)

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="ML model is not available. Train the model first.",
        ) from exc
