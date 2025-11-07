"""Anthropic adapter placeholder implementation."""

from __future__ import annotations

from app.adapters.base import ClassifierAdapter
from app.schemas.domain import ClassificationResult, WasteMaterial


class AnthropicAdapter(ClassifierAdapter):
    """Placeholder adapter returning static responses."""

    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        return ClassificationResult(
            material=WasteMaterial.OTHER,
            confidence=0.0,
            model_used=self.model_name,
            model_provider=self.model_provider,
            raw_response="unsupported",
        )

    @property
    def model_name(self) -> str:
        return "anthropic/claude-vision"

    @property
    def model_provider(self) -> str:
        return "anthropic"

    @property
    def cost_per_request(self) -> float:
        return 0.0
