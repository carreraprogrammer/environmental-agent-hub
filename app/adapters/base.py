"""Base classes for classifier adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Final

from app.schemas.domain import ClassificationResult


class ClassifierAdapter(ABC):
    """Abstract base class for classifier adapters."""

    DEFAULT_TRACE_KEY: Final[str] = "trace_id"

    @abstractmethod
    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        """
        Classify a waste material from an image URL (V3 compatibility).

        DEPRECATED: Use classify_material() instead for V4 unified classification.
        """

    @abstractmethod
    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        """
        Perform unified material classification (V4).

        Returns complete classification with per-field confidences:
        - material: Material type with confidence
        - subtype: Specific subtype with recycling code and confidence
        - condition: Physical condition with confidence
        - volume: Volume estimation with source and confidence
        - recyclability: Recyclability assessment with confidence
        - reasoning: Model's explanation

        Args:
            image_data: Image bytes (JPEG, PNG, WEBP)
            trace_id: Request trace ID for logging

        Returns:
            Dict with classification results and per-field confidences
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the fully qualified model name."""

    @property
    @abstractmethod
    def model_provider(self) -> str:
        """Return the provider name for the adapter."""

    @property
    @abstractmethod
    def cost_per_request(self) -> float:
        """Return the estimated cost per request in USD."""


class AdapterNotConfiguredError(RuntimeError):
    """
    Raised when adapter is not configured.
    """

    def __init__(self, adapter_name: str) -> None:
        """
        Initialize the error.

        Args:
            adapter_name: Name of the adapter
        """
        super().__init__(f"Adapter '{adapter_name}' is not configured")
