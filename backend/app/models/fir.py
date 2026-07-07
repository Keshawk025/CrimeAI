"""
app/models/fir.py
──────────────────
FIR (First Information Report) ORM model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileType(str, PyEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class FIRStatus(str, PyEnum):
    UPLOADED = "uploaded"
    TEXT_EXTRACTED = "text_extracted"
    ENTITIES_EXTRACTED = "entities_extracted"
    INDEXED = "indexed"
    READY_FOR_INVESTIGATION = "ready_for_investigation"
    FAILED = "failed"


class FIR(Base):
    """Stores metadata for every uploaded FIR document."""

    __tablename__ = "firs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, name="filetype", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    status: Mapped[FIRStatus] = mapped_column(
        Enum(FIRStatus, name="fir_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=FIRStatus.UPLOADED,
        server_default=FIRStatus.UPLOADED.value,
    )
    created_by: Mapped[str] = mapped_column(
        String(255), nullable=False, default="system"
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    document_content: Mapped[FIRDocumentContent] = relationship(
        "FIRDocumentContent",
        back_populates="fir",
        uselist=False,
        cascade="all, delete-orphan",
    )

    entities: Mapped[list[FIREntity]] = relationship(
        "FIREntity",
        back_populates="fir",
        cascade="all, delete-orphan",
    )

    embedding: Mapped[FIREmbedding] = relationship(
        "FIREmbedding",
        back_populates="fir",
        uselist=False,
        cascade="all, delete-orphan",
    )
