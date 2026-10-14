from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["healthy"]
    application: Literal["FinTwin API"]


class DatabaseReadinessResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    database: Literal["connected", "disconnected"]
