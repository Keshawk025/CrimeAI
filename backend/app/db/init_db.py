"""
app/db/init_db.py
──────────────────
Database initialisation helpers.
In production, schema changes are managed by Alembic.
This module is only used to verify connectivity on startup.
"""

import logging

from sqlalchemy import text

from app.db.base import Base, engine
import app.models.fir  # noqa: F401
import app.models.fir_document_content  # noqa: F401
import app.models.fir_entity  # noqa: F401
import app.models.fir_embedding  # noqa: F401
import app.models.guardrail_log  # noqa: F401

logger = logging.getLogger(__name__)


async def check_db_connection() -> bool:
    """
    Ping the database and automatically create tables if they do not exist.
    Returns True if reachable, False otherwise.
    Called during application startup.
    """
    try:
        # Verify connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully.")

        # Automatically create tables if not exists
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verification and table creation complete.")
        return True
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        return False
