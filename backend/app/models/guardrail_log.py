"""
app/models/guardrail_log.py
────────────────────────────
Model to store Enkrypt AI guardrail validation events.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin, UUIDMixin


class GuardrailLog(Base, UUIDMixin, TimestampMixin):
    """Stores every guardrail validation event."""

    __tablename__ = "guardrail_logs"

    fir_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    validation_result: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Optional relationship to the parent FIR metadata record
    fir: Mapped[Optional["FIR"]] = relationship("FIR")
