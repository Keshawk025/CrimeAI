"""
app/schemas/fir_embedding.py
────────────────────────────
Pydantic schemas for FIR embedding metadata.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class FIREmbeddingBase(BaseModel):
    qdrant_point_id: str = Field(..., description="The point ID inside the Qdrant collection")
    embedding_model: str = Field(..., description="The model name used to generate embeddings")
    vector_dimension: int = Field(..., description="The dimension size of the generated vector")


class FIREmbeddingCreate(FIREmbeddingBase):
    fir_id: uuid.UUID


class FIREmbeddingRead(FIREmbeddingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fir_id: uuid.UUID
    indexed_at: datetime
