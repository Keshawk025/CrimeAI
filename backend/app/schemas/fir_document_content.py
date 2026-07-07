"""
app/schemas/fir_document_content.py
───────────────────────────────────
Pydantic v2 schemas for FIR document content extraction.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FIRDocumentContentBase(BaseModel):
    extracted_text: str
    page_count: int
    word_count: int
    character_count: int
    language: str
    extraction_status: str = "success"


class FIRDocumentContentCreate(FIRDocumentContentBase):
    fir_id: uuid.UUID


class FIRDocumentContentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fir_id: uuid.UUID
    extracted_text: str
    page_count: int
    word_count: int
    character_count: int
    language: str
    extraction_status: str
    extracted_at: datetime
