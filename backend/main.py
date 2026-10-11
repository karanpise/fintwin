
from fastapi import FastAPI

from backend.api.routes.auth import router as auth_router
from backend.api.routes.health import router as health_router
from backend.api.routes.financial_profile import (
    router as financial_profile_router,
)

from backend.api.routes.financial_health import (
    router as financial_health_router,
)
from backend.api.routes.risk_analysis import router as risk_analysis_router
from backend.api.routes.simulation import router as simulation_router
from backend.api.routes.optimization import router as optimization_router
from backend.api.routes.ml_prediction import router as ml_prediction_router

app = FastAPI(
    title="FinTwin API",
    description="Financial risk analysis and simulation API",
    version="0.1.0",
)

# Register API routers here
app.include_router(health_router)
app.include_router(financial_profile_router)
app.include_router(auth_router)
app.include_router(financial_health_router)
app.include_router(risk_analysis_router)
app.include_router(simulation_router)
app.include_router(optimization_router)
app.include_router(ml_prediction_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to FinTwin API",
        "docs": "/docs",
    }

