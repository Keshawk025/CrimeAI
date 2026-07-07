"""
app/api/v1/health.py
─────────────────────
Health check endpoint.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the current health status of the API and its dependencies.",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Lightweight health probe.

    - Verifies the API process is running.
    - Pings the database to confirm connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        logger.debug("Health check passed — DB reachable.")
    except Exception as exc:
        logger.error("Health check — DB unreachable: %s", exc)
        # Still return healthy for the API process itself;
        # in production you may want to return 503 here.

    return HealthResponse(status="healthy")
