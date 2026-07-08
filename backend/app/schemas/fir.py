"""
app/schemas/fir.py
───────────────────
Pydantic v2 schemas for FIR upload and retrieval.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.fir import FileType, FIRStatus
from app.schemas.fir_embedding import FIREmbeddingRead


class FIRBase(BaseModel):
    case_number: str = Field(..., min_length=1, max_length=100)
    created_by: str = Field(default="system", max_length=255)


class FIRCreate(FIRBase):
    """Internal schema populated after file save."""
    original_filename: str
    file_type: FileType
    file_size: int
    storage_path: str


class FIRRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_number: str
    original_filename: str
    file_type: FileType
    file_size: int
    storage_path: str
    status: FIRStatus
    created_by: str
    uploaded_at: datetime
    updated_at: datetime
    embedding: Optional[FIREmbeddingRead] = None


class FIRListResponse(BaseModel):
    total: int
    items: list[FIRRead]


class FIRUploadResponse(BaseModel):
    """Returned immediately after a successful upload."""
    id: uuid.UUID
    case_number: str
    original_filename: str
    file_type: FileType
    file_size: int
    status: FIRStatus
    uploaded_at: datetime
    message: str = "FIR uploaded successfully"


class FIRDeleteResponse(BaseModel):
    id: uuid.UUID
    message: str = "FIR deleted successfully"


class CopilotQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)


class CopilotResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: int

