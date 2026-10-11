
from fastapi import APIRouter
from sqlalchemy import text

from database.connection import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "FinTwin API",
    }


@router.get("/health/database")
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }
