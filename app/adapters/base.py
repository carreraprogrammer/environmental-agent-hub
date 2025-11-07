"""Base classes for classifier adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

from app.schemas.domain import ClassificationResult


class ClassifierAdapter(ABC):
    """Abstract base class for classifier adapters."""

    DEFAULT_TRACE_KEY: Final[str] = "trace_id"

    @abstractmethod
    async def classify(
        self, image_url: str, *, trace_id: str | None = None
    ) -> ClassificationResult:
        """Classify a waste material from an image URL."""

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
