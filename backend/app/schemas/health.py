"""
app/schemas/health.py
──────────────────────
Pydantic response schemas for the health endpoint.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "healthy"

    model_config = {"json_schema_extra": {"example": {"status": "healthy"}}}
