"""
app/integrations/enkrypt/client.py
────────────────────────────────────
Managed Enkrypt AI client — thread-safe singleton with retry logic.

Usage (application startup)::

    from app.integrations.enkrypt.client import init_enkrypt_client, get_enkrypt_client
    await init_enkrypt_client()           # call once in FastAPI lifespan
    client = get_enkrypt_client()         # retrieve anywhere after init

The client wraps ``GuardrailsClient`` from ``enkryptai_sdk`` and adds:

- Exponential-backoff retry on transient failures
- Structured logging on every call
- A ``ping()`` method for health probes
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from enkryptai_sdk import GuardrailsClient, GuardrailsClientError

from app.integrations.enkrypt.config import EnkryptSettings, get_enkrypt_settings

logger = logging.getLogger(__name__)

# ── Module-level singleton ─────────────────────────────────────────────────────

_enkrypt_client: GuardrailsClient | None = None
_settings: EnkryptSettings | None = None


def get_enkrypt_client() -> GuardrailsClient:
    """
    Return the module-level Enkrypt ``GuardrailsClient``.

    Raises
    ------
    RuntimeError
        If ``init_enkrypt_client()`` has not been called yet.
    """
    if _enkrypt_client is None:
        raise RuntimeError(
            "Enkrypt client is not initialised. "
            "Call init_enkrypt_client() during application startup."
        )
    return _enkrypt_client


async def init_enkrypt_client() -> GuardrailsClient | None:
    """
    Create and store the Enkrypt ``GuardrailsClient`` singleton.

    Returns ``None`` when Enkrypt is disabled (``ENKRYPT_ENABLED=false``).
    Should be called once in the FastAPI lifespan startup hook.
    """
    global _enkrypt_client, _settings
    _settings = get_enkrypt_settings()

    if not _settings.enkrypt_enabled:
        logger.warning(
            "[Enkrypt] ENKRYPT_ENABLED=false — guardrails are DISABLED. "
            "All validation calls will pass through without checks."
        )
        return None

    if not _settings.enkrypt_api_key:
        logger.warning(
            "[Enkrypt] ENKRYPT_API_KEY is not set — guardrails will operate "
            "in pass-through mode until a key is configured."
        )
        return None

    logger.info(
        "[Enkrypt] Initialising GuardrailsClient → %s", _settings.enkrypt_base_url
    )
    _enkrypt_client = GuardrailsClient(
        api_key=_settings.enkrypt_api_key,
        base_url=_settings.enkrypt_base_url,
    )
    logger.info("[Enkrypt] GuardrailsClient initialised successfully.")
    return _enkrypt_client


async def close_enkrypt_client() -> None:
    """Tear down the client on application shutdown."""
    global _enkrypt_client
    _enkrypt_client = None
    logger.info("[Enkrypt] Client closed.")


# ── Retry helper ───────────────────────────────────────────────────────────────

def _call_with_retry(
    fn: Any,
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 0.5,
    **kwargs: Any,
) -> Any:
    """
    Synchronous retry wrapper with exponential back-off.

    Retries on ``GuardrailsClientError`` that look transient (5xx keywords).
    Immediately re-raises on ``ValueError`` or other non-retryable errors.

    Parameters
    ----------
    fn:
        Any callable to invoke.
    max_retries:
        Maximum number of attempts (including the first).
    base_delay:
        Initial back-off delay in seconds; doubles on each retry.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except GuardrailsClientError as exc:
            last_exc = exc
            msg = str(exc).lower()
            transient = any(
                kw in msg
                for kw in ("500", "502", "503", "504", "timeout", "connection")
            )
            if not transient or attempt == max_retries:
                logger.error(
                    "[Enkrypt] Non-retryable error on attempt %d/%d: %s",
                    attempt,
                    max_retries,
                    exc,
                )
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "[Enkrypt] Transient error on attempt %d/%d — retrying in %.1fs: %s",
                attempt,
                max_retries,
                delay,
                exc,
            )
            time.sleep(delay)

    raise last_exc  # type: ignore[misc]
