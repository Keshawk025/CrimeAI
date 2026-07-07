"""
app/models/fir_embedding.py
────────────────────────────
Model to store embedding and vector index metadata for a FIR document.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import UUIDMixin


class FIREmbedding(Base, UUIDMixin):
    """Stores metadata about the generated semantic vector index for an FIR."""

    __tablename__ = "fir_embeddings"

    fir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    qdrant_point_id: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(150), nullable=False)
    vector_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to the parent FIR metadata record
    fir: Mapped["FIR"] = relationship("FIR", back_populates="embedding")
