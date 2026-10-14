
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.schemas.health import (
    DatabaseReadinessResponse,
    LivenessResponse,
)
from database.connection import engine

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=LivenessResponse)
def health_check():
    return {
        "status": "healthy",
        "application": "FinTwin API",
    }


@router.get(
    "/health/database",
    response_model=DatabaseReadinessResponse,
    responses={503: {"model": DatabaseReadinessResponse}},
)
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
            },
        )
