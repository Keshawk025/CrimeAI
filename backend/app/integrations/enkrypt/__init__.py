"""
app/integrations/enkrypt/__init__.py
──────────────────────────────────────
Public surface of the Enkrypt AI integration package.
"""

from app.integrations.enkrypt.client import (
    close_enkrypt_client,
    get_enkrypt_client,
    init_enkrypt_client,
)
from app.integrations.enkrypt.config import EnkryptSettings, get_enkrypt_settings
from app.integrations.enkrypt.validator import (
    ValidationResult,
    validate_input,
    validate_output,
    validate_prompt,
)

__all__ = [
    # Client lifecycle
    "init_enkrypt_client",
    "close_enkrypt_client",
    "get_enkrypt_client",
    # Settings
    "EnkryptSettings",
    "get_enkrypt_settings",
    # Validation
    "validate_input",
    "validate_output",
    "validate_prompt",
    "ValidationResult",
]
