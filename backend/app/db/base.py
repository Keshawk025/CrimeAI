"""
app/db/base.py
──────────────
SQLAlchemy async engine, session factory, and declarative base.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,          # logs SQL in development
    pool_pre_ping=True,           # validates connections before checkout
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass
