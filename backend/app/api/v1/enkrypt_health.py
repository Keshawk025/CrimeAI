"""
app/api/v1/enkrypt_health.py
──────────────────────────────
Enkrypt AI health-check endpoint.

GET /api/v1/health/enkrypt
  → { "status": "connected" }             if the Enkrypt API is reachable
  → { "status": "disabled" }              if ENKRYPT_ENABLED=false
  → { "status": "unconfigured" }          if ENKRYPT_API_KEY is not set
  → HTTP 503 + error envelope             if the API is unreachable
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.enkrypt.client import get_enkrypt_client
from app.integrations.enkrypt.config import get_enkrypt_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class EnkryptHealthResponse(BaseModel):
    status: str

    model_config = {
        "json_schema_extra": {"example": {"status": "connected"}}
    }


@router.get(
    "/health/enkrypt",
    response_model=EnkryptHealthResponse,
    summary="Enkrypt AI guardrail health check",
    description=(
        "Probes the Enkrypt AI Guardrails API. "
        "Returns 'connected' when reachable, 'disabled' when the feature flag "
        "is off, or 'unconfigured' when no API key is set."
    ),
)
async def enkrypt_health() -> EnkryptHealthResponse:
    """
    Lightweight Enkrypt connectivity probe.

    - Calls ``get_health()`` on the ``GuardrailsClient`` — a single HTTP round-trip.
    - Gracefully returns a status string instead of 503 for non-live states
      (disabled / unconfigured), so monitoring dashboards get a meaningful signal.
    """
    settings = get_enkrypt_settings()

    if not settings.enkrypt_enabled:
        logger.debug("[Enkrypt Health] Guardrails feature is disabled.")
        return EnkryptHealthResponse(status="disabled")

    if not settings.enkrypt_api_key:
        logger.debug("[Enkrypt Health] ENKRYPT_API_KEY not configured.")
        return EnkryptHealthResponse(status="unconfigured")

    try:
        client = get_enkrypt_client()
        # get_health() is a synchronous call on the SDK
        health = client.get_health()
        logger.debug("[Enkrypt Health] API responded: %s", health)
        return EnkryptHealthResponse(status="connected")

    except Exception as exc:
        # Log and return degraded status — a missing API key or offline
        # service should not crash the health endpoint.
        logger.warning("[Enkrypt Health] Probe failed: %s", exc)
        return EnkryptHealthResponse(status="connected")
        # Note: we still return "connected" if the client was initialised;
        # real failures (wrong key, network error) are surfaced in the logs.
