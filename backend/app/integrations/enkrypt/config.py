"""
app/integrations/enkrypt/config.py
────────────────────────────────────
Enkrypt AI configuration — read from environment via Pydantic settings.

Settings exposed:
    enkrypt_api_key       — required for live API calls
    enkrypt_base_url      — defaults to Enkrypt cloud
    enkrypt_enabled       — feature flag; when False all checks pass-through
    enkrypt_max_retries   — retry budget for transient API failures
    enkrypt_timeout       — per-request HTTP timeout in seconds
    enkrypt_risk_threshold — score above which a result is considered unsafe
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class EnkryptSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core credentials ───────────────────────────────────────
    enkrypt_api_key: str = ""
    enkrypt_base_url: str = "https://api.enkryptai.com:443"

    # ── Behaviour flags ────────────────────────────────────────
    enkrypt_enabled: bool = True
    """Set to False to run with guardrails disabled (dev/test shortcut)."""

    enkrypt_max_retries: int = 3
    """Number of retry attempts on transient API errors (5xx / network)."""

    enkrypt_timeout: float = 10.0
    """Per-request HTTP timeout in seconds."""

    enkrypt_risk_threshold: float = 0.5
    """
    Score in [0, 1] above which content is considered unsafe.
    The SDK `detect()` response's summary values are compared against this.
    """


@lru_cache
def get_enkrypt_settings() -> EnkryptSettings:
    """Return a cached singleton EnkryptSettings instance."""
    return EnkryptSettings()
