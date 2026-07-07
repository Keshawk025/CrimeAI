"""
app/schemas/fir_entity.py
─────────────────────────
Pydantic schemas for FIR entities with SQLAlchemy metadata resolver.
"""

from datetime import datetime
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


class FIREntityBase(BaseModel):
    entity_type: str = Field(..., description="Type of entity (e.g. person, victim, phone)")
    entity_value: str = Field(..., description="Extracted value of the entity")
    confidence: float = Field(1.0, description="Confidence score estimated by AI")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or properties of the entity")


class FIREntityCreate(FIREntityBase):
    pass


class FIREntityRead(FIREntityBase):
    id: uuid.UUID
    fir_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def resolve_metadata_field(cls, data: Any) -> Any:
        # If the input is a SQLAlchemy model, map metadata_ to metadata
        if not isinstance(data, dict) and hasattr(data, "metadata_"):
            d = {
                "id": getattr(data, "id"),
                "fir_id": getattr(data, "fir_id"),
                "entity_type": getattr(data, "entity_type"),
                "entity_value": getattr(data, "entity_value"),
                "confidence": getattr(data, "confidence"),
                "metadata": getattr(data, "metadata_"),
                "created_at": getattr(data, "created_at"),
                "updated_at": getattr(data, "updated_at"),
            }
            return d
        return data
