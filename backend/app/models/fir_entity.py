"""
app/models/fir_entity.py
─────────────────────────
Model to store structured entities extracted from a FIR document.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDMixin


class FIREntity(Base, UUIDMixin, TimestampMixin):
    """Stores a single structured entity extracted from an FIR document."""

    __tablename__ = "fir_entities"

    fir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_value: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Relationship to the parent FIR metadata record
    fir: Mapped["FIR"] = relationship("FIR", back_populates="entities")
