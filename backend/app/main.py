"""
app/main.py
────────────
FastAPI application factory with lifespan, CORS, and exception handlers.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.init_db import check_db_connection
from app.integrations.enkrypt.client import close_enkrypt_client, init_enkrypt_client
from app.middleware.enkrypt_middleware import (
    EnkryptInputMiddleware,
    EnkryptOutputMiddleware,
)
from app.services.qdrant_service import (
    QdrantService,
    close_qdrant_client,
    init_qdrant_client,
)

# Boot logging before anything else
configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup / shutdown hooks.
    Replaces the deprecated on_event decorators.
    """
    # ── Startup ────────────────────────────────────────────────
    logger.info("Starting %s v%s [%s]", settings.app_name, settings.app_version, settings.app_env)

    # PostgreSQL
    db_ok = await check_db_connection()
    if not db_ok:
        logger.warning(
            "Could not reach the database on startup. "
            "Ensure PostgreSQL is running and DATABASE_URL is correct."
        )

    # Qdrant
    try:
        await init_qdrant_client()
        qdrant_svc = QdrantService()
        await qdrant_svc.create_collection()   # no-op if already exists
        logger.info("Qdrant ready — collection '%s'.", settings.qdrant_collection)
    except Exception as exc:
        logger.warning(
            "Qdrant unavailable on startup (%s). "
            "Vector search features will be degraded until Qdrant is reachable.",
            exc,
        )

    # Enkrypt AI
    try:
        await init_enkrypt_client()
        logger.info("[Enkrypt] Guardrail layer initialised.")
    except Exception as exc:
        logger.warning(
            "[Enkrypt] Could not initialise guardrails (%s). "
            "Validation will operate in pass-through mode.",
            exc,
        )

    logger.info("Application startup complete.")
    yield

    # ── Shutdown ───────────────────────────────────────────────
    await close_qdrant_client()
    await close_enkrypt_client()
    logger.info("Application shutting down.")


# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Investigation Copilot for Karnataka Police — Backend API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Enkrypt AI guardrail middleware ────────────────────────
    # Output middleware wraps before input so the scan order is:
    #   request → InputMiddleware → handler → OutputMiddleware → response
    app.add_middleware(EnkryptOutputMiddleware)
    app.add_middleware(EnkryptInputMiddleware)

    # ── Exception handlers ─────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ────────────────────────────────────────────────
    app.include_router(api_router)

    return app


app = create_app()
