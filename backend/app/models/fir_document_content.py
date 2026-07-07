"""
app/models/fir_document_content.py
───────────────────────────────────
Model to store the extracted text and metadata of a FIR document.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDMixin


class FIRDocumentContent(Base, UUIDMixin, TimestampMixin):
    """Stores the plain text extracted from an FIR document."""

    __tablename__ = "fir_document_contents"

    fir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    extraction_status: Mapped[str] = mapped_column(String(50), nullable=False, default="success")
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to the parent FIR metadata record
    fir: Mapped["FIR"] = relationship("FIR", back_populates="document_content")
