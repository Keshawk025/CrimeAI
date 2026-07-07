"""
app/core/exceptions.py
───────────────────────
Centralised exception classes and FastAPI exception handlers.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ── Domain exceptions ──────────────────────────────────────────────────────────

class CrimeMindBaseException(Exception):
    """Root exception for all CrimeMind domain errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, **kwargs: Any) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundException(CrimeMindBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ValidationException(CrimeMindBaseException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed."


class ConflictException(CrimeMindBaseException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class ServiceUnavailableException(CrimeMindBaseException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Service temporarily unavailable."


# ── Exception handlers ─────────────────────────────────────────────────────────

async def crimemind_exception_handler(
    request: Request, exc: CrimeMindBaseException
) -> JSONResponse:
    logger.warning(
        "Domain exception: %s | path=%s | detail=%s",
        type(exc).__name__,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "detail": exc.detail},
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Unhandled exception | path=%s | error=%s", request.url.path, str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""
    app.add_exception_handler(CrimeMindBaseException, crimemind_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
