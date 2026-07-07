"""
app/schemas/qdrant.py
──────────────────────
Pydantic response schemas for Qdrant-related endpoints.
"""

from pydantic import BaseModel


class QdrantHealthResponse(BaseModel):
    status: str
    collection: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "connected",
                "collection": "crime_reports",
            }
        }
    }
