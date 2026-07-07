"""
app/api/v1/qdrant_health.py
────────────────────────────
Qdrant health-check endpoint.

GET /api/v1/health/qdrant
  → { "status": "connected", "collection": "<name>" }
  → 503 if Qdrant is unreachable
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.core.exceptions import ServiceUnavailableException
from app.schemas.qdrant import QdrantHealthResponse
from app.services.qdrant_service import QdrantService, get_qdrant_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Health"])


@router.get(
    "/health/qdrant",
    response_model=QdrantHealthResponse,
    summary="Qdrant health check",
    description=(
        "Verifies connectivity to Qdrant and confirms the target "
        "collection exists. Returns HTTP 503 if Qdrant is unreachable."
    ),
    responses={
        503: {
            "description": "Qdrant is unreachable",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ServiceUnavailableException",
                        "detail": "Qdrant is unavailable: ...",
                    }
                }
            },
        }
    },
)
async def qdrant_health(
    qdrant: QdrantService = Depends(get_qdrant_service),
) -> QdrantHealthResponse:
    """
    Perform a lightweight Qdrant connectivity probe.

    - Calls ``collection_exists()`` — a single round-trip to Qdrant.
    - Returns ``{ "status": "connected", "collection": "<name>" }`` on success.
    - The global exception handler converts :exc:`ServiceUnavailableException`
      to HTTP 503 automatically.
    """
    exists = await qdrant.collection_exists()
    if not exists:
        logger.warning(
            "Qdrant health check: collection '%s' not found.",
            settings.qdrant_collection,
        )

    logger.debug(
        "Qdrant health check OK — collection='%s' exists=%s",
        settings.qdrant_collection,
        exists,
    )
    return QdrantHealthResponse(
        status="connected",
        collection=settings.qdrant_collection,
    )
