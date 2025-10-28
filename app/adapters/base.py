"""
Base classes for classifier adapters (placeholder).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ClassifierAdapter(ABC):
    """
    Abstract base class for classifier adapters.
    """

    @abstractmethod
    def classify(self, payload: dict[str, object]) -> dict[str, object]:
        """
        Classify the given payload.
        
        Args:
            payload: Input payload for classification
        
        Returns:
            dict: Classification result
        """


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
