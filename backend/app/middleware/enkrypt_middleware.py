"""
app/middleware/enkrypt_middleware.py
─────────────────────────────────────
FastAPI middleware for Enkrypt AI guardrails.

Two middleware classes:

``EnkryptInputMiddleware``
    Intercepts every ``POST /api/v1/investigate/*`` request, reads the body,
    and calls ``validate_input()`` before passing the request downstream.
    Returns HTTP 422 if the input is flagged as unsafe.

``EnkryptOutputMiddleware``
    Intercepts every ``POST /api/v1/investigate/*`` response and calls
    ``validate_output()`` on the JSON body before returning it to the client.
    Returns HTTP 422 if the output is flagged as unsafe.

Both middleware classes operate in pass-through mode when Enkrypt is disabled
or unconfigured, so the API continues to function without a live API key.
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.integrations.enkrypt.config import get_enkrypt_settings
from app.integrations.enkrypt.validator import validate_input, validate_output

logger = logging.getLogger(__name__)

# ── Paths that trigger guardrail scanning ─────────────────────────────────────
_GUARDED_PREFIXES = ("/api/v1/investigate",)


def _is_guarded(path: str) -> bool:
    return any(path.startswith(p) for p in _GUARDED_PREFIXES)


# ── Input Middleware ───────────────────────────────────────────────────────────


class EnkryptInputMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming request bodies against Enkrypt AI guardrails.

    Only applies to POST/PUT requests that match ``_GUARDED_PREFIXES``.
    If the input is flagged as unsafe, returns HTTP 422 with a structured
    error body instead of forwarding the request.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._settings = get_enkrypt_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only scan modifying requests on guarded routes
        if (
            request.method not in ("POST", "PUT", "PATCH")
            or not _is_guarded(request.url.path)
            or not self._settings.enkrypt_enabled
            or not self._settings.enkrypt_api_key
        ):
            return await call_next(request)

        # Read and buffer the body (Starlette consumes it once)
        body_bytes = await request.body()
        text_to_scan = body_bytes.decode("utf-8", errors="replace")

        # Extract the most meaningful text field from JSON bodies
        try:
            payload = json.loads(text_to_scan)
            if isinstance(payload, dict):
                text_to_scan = (
                    payload.get("text")
                    or payload.get("query")
                    or payload.get("input")
                    or text_to_scan
                )
        except json.JSONDecodeError:
            pass  # use raw body as-is

        logger.debug(
            "[Enkrypt Input] Scanning %s %s (body length=%d)",
            request.method,
            request.url.path,
            len(text_to_scan),
        )

        result = await validate_input(text_to_scan)

        if not result["safe"]:
            logger.warning(
                "[Enkrypt Input] Request BLOCKED — path=%s issues=%s risk_score=%.4f",
                request.url.path,
                result["issues"],
                result["risk_score"],
            )
            return JSONResponse(
                status_code=422,
                content={
                    "error": "GuardrailViolation",
                    "detail": "Input validation failed — request contains unsafe content.",
                    "issues": result["issues"],
                    "risk_score": result["risk_score"],
                },
            )

        # Re-attach body so downstream handlers can read it
        async def receive():
            return {"type": "http.request", "body": body_bytes}

        request._receive = receive  # type: ignore[attr-defined]
        return await call_next(request)


# ── Output Middleware ──────────────────────────────────────────────────────────


class EnkryptOutputMiddleware(BaseHTTPMiddleware):
    """
    Validate outgoing JSON responses from Enkrypt AI guardrails.

    Only applies to responses from guarded routes.  If the output is flagged
    as unsafe, replaces the response with HTTP 422.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._settings = get_enkrypt_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Only inspect guarded routes with JSON responses
        content_type = response.headers.get("content-type", "")
        if (
            not _is_guarded(request.url.path)
            or "application/json" not in content_type
            or not self._settings.enkrypt_enabled
            or not self._settings.enkrypt_api_key
        ):
            return response

        # Consume the response body
        body_bytes = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()

        text_to_scan = body_bytes.decode("utf-8", errors="replace")

        # Extract a meaningful text field
        try:
            payload = json.loads(text_to_scan)
            if isinstance(payload, dict):
                scan_text = (
                    payload.get("result")
                    or payload.get("response")
                    or payload.get("text")
                    or text_to_scan
                )
            else:
                scan_text = text_to_scan
        except json.JSONDecodeError:
            scan_text = text_to_scan

        logger.debug(
            "[Enkrypt Output] Scanning response for %s (body length=%d)",
            request.url.path,
            len(scan_text),
        )

        result = await validate_output(scan_text)

        if not result["safe"]:
            logger.warning(
                "[Enkrypt Output] Response BLOCKED — path=%s issues=%s risk_score=%.4f",
                request.url.path,
                result["issues"],
                result["risk_score"],
            )
            return JSONResponse(
                status_code=422,
                content={
                    "error": "GuardrailViolation",
                    "detail": "Output validation failed — response contains unsafe content.",
                    "issues": result["issues"],
                    "risk_score": result["risk_score"],
                },
            )

        # Return the original (unmodified) response body
        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
