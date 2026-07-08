"""
app/mastra/workflows/investigation_copilot.py
─────────────────────────────────────────────
Mastra-style workflow orchestrator for the Investigation Copilot.
"""

from typing import List


class InvestigationCopilotWorkflow:
    """
    Implements a Python-based step-by-step workflow structure matching the Mastra spec.
    """

    def __init__(self, steps: List[str] = None):
        self.steps = steps or [
            "retrieve-fir",
            "retrieve-text",
            "retrieve-entities",
            "retrieve-similar-cases",
            "build-context",
            "generate-gemini-response"
        ]

    def get_registered_steps(self) -> List[str]:
        return self.steps
