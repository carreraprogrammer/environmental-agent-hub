"""
OpenAI adapter placeholder.
"""

from __future__ import annotations

from app.adapters.base import ClassifierAdapter


class OpenAIAdapter(ClassifierAdapter):
    """
    Adapter for OpenAI models (placeholder implementation).
    """

    def classify(self, payload: dict[str, object]) -> dict[str, object]:
        """
        Placeholder classify implementation.
        
        Args:
            payload: Input payload
        
        Returns:
            dict: Placeholder response
        """
        return {"provider": "openai", "payload": payload}
