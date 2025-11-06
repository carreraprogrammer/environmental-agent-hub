"""Domain models for classification adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, MutableMapping


class WasteMaterial(str, Enum):
    """Enumeration of supported waste material categories."""

    PLASTIC = "PLASTIC"
    PAPER = "PAPER"
    GLASS = "GLASS"
    METAL = "METAL"
    ORGANIC = "ORGANIC"
    OTHER = "OTHER"


@dataclass(slots=True)
class ClassificationResult:
    """Standardized classification result returned by adapters."""

    material: WasteMaterial
    confidence: float
    model_used: str
    model_provider: str
    raw_response: str | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Mapping[str, Any]:
        """Serialize the result to a mapping."""

        return {
            "material": self.material.value,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "model_provider": self.model_provider,
            "raw_response": self.raw_response,
            "metadata": dict(self.metadata),
        }
