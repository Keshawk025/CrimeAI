"""
app/services/guardrail_service.py
──────────────────────────────────
Service for AI safety validation using Enkrypt AI and database logging.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.integrations.enkrypt.validator import validate_input, validate_output, validate_prompt
from app.models.guardrail_log import GuardrailLog

logger = logging.getLogger(__name__)


class GuardrailService:
    """
    Validates user input, LLM prompts, and AI responses. Logs validation
    events to PostgreSQL, and raises HTTP 400 Bad Request on block.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_input(self, text: str, request_type: str, fir_id: Optional[uuid.UUID] = None) -> None:
        """
        Validates raw user input (investigator prompt/question) or documents.
        Logs validation status to PostgreSQL and throws HTTPException if unsafe.
        """
        # 1. Fallback local rules (always run for robust local testing)
        is_safe, reason = self._check_local_input_rules(text)
        
        # 2. SDK-based Enkrypt check
        if is_safe:
            try:
                sdk_res = await validate_input(text)
                if not sdk_res["safe"]:
                    is_safe = False
                    reason = ", ".join(sdk_res["issues"]) or "Enkrypt policy violation"
            except Exception as e:
                logger.error("Enkrypt validation SDK failed: %s", e)

        # 3. Log event
        validation_result = "passed" if is_safe else "blocked"
        await self._log_event(
            fir_id=fir_id,
            request_type=request_type,
            validation_result=validation_result,
            reason=reason
        )

        # 4. Enforce blocking
        if not is_safe:
            logger.warning(
                "[Guardrails] Blocked %s request for FIR %s. Reason: %s",
                request_type, fir_id, reason
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request blocked by AI safety policy. Reason: {reason}"
            )

    async def check_output(self, text: str, request_type: str, fir_id: Optional[uuid.UUID] = None) -> str:
        """
        Validates AI-generated output. Logs and raises error if unsafe.
        If any minor issues occur, we can sanitize the text (e.g. filter out PII/sensitive info).
        Returns the sanitized or original text.
        """
        # 1. Fallback local rules
        is_safe, reason = self._check_local_output_rules(text)
        
        # 2. SDK check
        if is_safe:
            try:
                sdk_res = await validate_output(text)
                if not sdk_res["safe"]:
                    is_safe = False
                    reason = ", ".join(sdk_res["issues"]) or "Enkrypt output policy violation"
            except Exception as e:
                logger.error("Enkrypt output validation SDK failed: %s", e)

        # 3. Log event
        validation_result = "passed" if is_safe else "blocked"
        await self._log_event(
            fir_id=fir_id,
            request_type=request_type,
            validation_result=validation_result,
            reason=reason
        )

        # 4. Enforce blocking / sanitization
        if not is_safe:
            logger.warning(
                "[Guardrails] Blocked AI output for %s. Reason: %s",
                request_type, reason
            )
            # If it's a minor violation, we can sanitize, but per requirements we block
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request blocked by AI safety policy. AI output validation failed."
            )
        
        return text

    async def check_prompt(self, text: str, request_type: str, fir_id: Optional[uuid.UUID] = None) -> None:
        """
        Validates compiled LLM prompts.
        """
        is_safe = True
        reason = None
        
        try:
            sdk_res = await validate_prompt(text)
            if not sdk_res["safe"]:
                is_safe = False
                reason = ", ".join(sdk_res["issues"]) or "Prompt policy violation"
        except Exception as e:
            logger.error("Enkrypt prompt validation SDK failed: %s", e)

        validation_result = "passed" if is_safe else "blocked"
        await self._log_event(
            fir_id=fir_id,
            request_type=request_type,
            validation_result=validation_result,
            reason=reason
        )

        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request blocked by AI safety policy. Prompt validation failed: {reason}"
            )

    def _check_local_input_rules(self, text: str) -> tuple[bool, Optional[str]]:
        """Offline backup checks for prompt injection, system instructions extractors, etc."""
        if not text:
            return True, None

        t_low = text.lower()

        # Prompt injection & jailbreak checks
        injection_keywords = [
            "ignore previous instructions",
            "ignore all instructions",
            "ignore the rules",
            "system prompt",
            "you are now a",
            "bypass safety",
            "jailbreak",
            "act as a",
            "developer mode",
            "reveal system"
        ]
        for kw in injection_keywords:
            if kw in t_low:
                return False, "Prompt injection attempt detected"

        # Malicious instructions / Code Execution
        malicious_keywords = [
            "rm -rf",
            "drop table",
            "delete from",
            "exec(",
            "eval(",
            "<script>",
            "format c:"
        ]
        for kw in malicious_keywords:
            if kw in t_low:
                return False, "Malicious instruction or code execution request detected"

        # Out-of-domain checks (e.g. asking for recipe, games, unrelated tasks)
        domain_keywords = [
            "fir", "case", "suspect", "victim", "robbery", "theft", "murder",
            "weapon", "evidence", "assault", "crime", "investigat", "police", "similar", "summary", "summarize",
            "location", "incident", "who", "what", "where", "when", "phone", "email", "address", "organization"
        ]
        
        # If it's a general short word, don't block. But if it's longer text, check if it's relevant
        if len(text.split()) > 3:
            has_domain = any(dkw in t_low for dkw in domain_keywords)
            if not has_domain:
                # Check for clearly non-investigation queries
                non_investigation = [
                    "write a python", "write a code", "recipe for", "how to bake", "weather in",
                    "joke", "play a game", "lyrics", "poem"
                ]
                if any(nikw in t_low for nikw in non_investigation):
                    return False, "Request unrelated to investigation workflow"

        return True, None

    def _check_local_output_rules(self, text: str) -> tuple[bool, Optional[str]]:
        """Offline checks on AI generated output."""
        if not text:
            return True, None
        
        t_low = text.lower()
        
        # Toxicity / Slurs / Extreme content
        harm_keywords = [
            "hate speech", "offensive term", "slur", "abuse"
        ]
        for kw in harm_keywords:
            if kw in t_low:
                return False, "AI output contains toxic or offensive content"

        # Leakage checks
        if "secret instruction" in t_low or "internal debug key" in t_low:
            return False, "Sensitive information leakage detected"

        return True, None

    async def _log_event(
        self,
        fir_id: Optional[uuid.UUID],
        request_type: str,
        validation_result: str,
        reason: Optional[str]
    ) -> None:
        """Saves a guardrail log entry directly to PostgreSQL."""
        try:
            log_entry = GuardrailLog(
                fir_id=fir_id,
                request_type=request_type,
                validation_result=validation_result,
                reason=reason
            )
            self.db.add(log_entry)
            await self.db.commit()
            logger.info(
                "[Guardrails Logged] Type: %s | Result: %s | Reason: %s",
                request_type, validation_result, reason
            )
        except Exception as e:
            logger.exception("Failed to write to guardrail_logs table: %s", e)
