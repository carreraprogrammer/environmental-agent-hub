"""
Classification schemas for MaterialClassifier V4.

This module defines the schemas used by the MaterialClassifier agent which
performs unified classification (material, subtype, condition, volume, recyclability)
in a single LLM call with per-field confidence scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, MutableMapping

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class Material(str, Enum):
    """Material base classification."""

    PLASTIC = "PLASTIC"
    PAPER = "PAPER"
    GLASS = "GLASS"
    METAL = "METAL"
    ORGANIC = "ORGANIC"
    CARDBOARD = "CARDBOARD"
    TETRAPAK = "TETRAPAK"
    OTHER = "OTHER"


class PlasticSubtype(str, Enum):
    """Plastic subtypes with recycling codes."""

    PET = "PET"  # #1 - Polyethylene Terephthalate
    HDPE = "HDPE"  # #2 - High-Density Polyethylene
    PVC = "PVC"  # #3 - Polyvinyl Chloride
    LDPE = "LDPE"  # #4 - Low-Density Polyethylene
    PP = "PP"  # #5 - Polypropylene
    PS = "PS"  # #6 - Polystyrene
    OTHER = "OTHER"  # #7 - Other plastics


class PhysicalCondition(str, Enum):
    """Physical condition of the waste item."""

    CLEAN = "CLEAN"
    CONTAMINATED = "CONTAMINATED"
    PARTIALLY_FULL = "PARTIALLY_FULL"
    DAMAGED = "DAMAGED"
    CRUSHED = "CRUSHED"


class Recyclability(str, Enum):
    """Recyclability assessment."""

    RECYCLABLE = "RECYCLABLE"
    RECYCLABLE_AFTER_CLEANING = "RECYCLABLE_AFTER_CLEANING"
    NON_RECYCLABLE = "NON_RECYCLABLE"
    COMPOSTABLE = "COMPOSTABLE"
    REQUIRES_SPECIAL_PROCESSING = "REQUIRES_SPECIAL_PROCESSING"


class VolumeSource(str, Enum):
    """Source of volume estimation."""

    LABEL_READ = "LABEL_READ"  # Read from label via OCR
    ESTIMATED = "ESTIMATED"  # Estimated by model


# ============================================================================
# Field schemas with confidence
# ============================================================================


@dataclass(slots=True)
class MaterialField:
    """Material classification with confidence."""

    material_type: Material
    confidence: float  # 0.0 to 1.0

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "material_type": self.material_type.value,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class SubtypeField:
    """Subtype classification with confidence and recycling code."""

    value: str | None  # Specific subtype (e.g., "PET", "Newspaper", "Aluminum Can")
    recycling_code: str | None  # Recycling code if applicable (e.g., "#1", "#2")
    confidence: float  # 0.0 to 1.0

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "value": self.value,
            "recycling_code": self.recycling_code,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class ConditionField:
    """Physical condition with confidence."""

    value: PhysicalCondition
    confidence: float  # 0.0 to 1.0

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "value": self.value.value,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class VolumeField:
    """Volume estimation with confidence and source."""

    liters: float | None  # Volume in liters
    source: VolumeSource  # How was volume determined
    confidence: float  # 0.0 to 1.0

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "liters": self.liters,
            "source": self.source.value,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class RecyclabilityField:
    """Recyclability assessment with confidence."""

    value: Recyclability
    confidence: float  # 0.0 to 1.0

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "value": self.value.value,
            "confidence": self.confidence,
        }


# ============================================================================
# Main classification result
# ============================================================================


@dataclass(slots=True)
class MaterialClassificationResult:
    """
    Complete classification result from MaterialClassifier agent.

    This represents the output of a unified classification that determines
    material type, subtype, physical condition, volume, and recyclability
    in a single LLM call. Each field includes its own confidence score
    to support partial success scenarios.

    Attributes:
        material: Material type with confidence
        subtype: Specific subtype with recycling code and confidence
        condition: Physical condition with confidence
        volume: Volume estimation with source and confidence
        recyclability: Recyclability assessment with confidence
        reasoning: Model's explanation of classification
        timestamp: When classification was performed
        cost: Cost of the LLM API call in USD
        model_used: Model identifier (e.g., "gpt-4-vision")
        model_provider: Provider name (e.g., "openai")
        partial_success: True if some fields have low confidence
        metadata: Additional metadata from the model
    """

    material: MaterialField
    subtype: SubtypeField
    condition: ConditionField
    volume: VolumeField
    recyclability: RecyclabilityField
    reasoning: str
    timestamp: datetime
    cost: float
    model_used: str
    model_provider: str
    partial_success: bool = False
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialize the result to a dict."""
        return {
            "material": self.material.as_dict(),
            "subtype": self.subtype.as_dict(),
            "condition": self.condition.as_dict(),
            "volume": self.volume.as_dict(),
            "recyclability": self.recyclability.as_dict(),
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "cost": self.cost,
            "model_used": self.model_used,
            "model_provider": self.model_provider,
            "partial_success": self.partial_success,
            "metadata": dict(self.metadata),
        }


# ============================================================================
# Validation result for PreValidator
# ============================================================================


class ValidationReason(str, Enum):
    """Reason codes for validation results."""

    WASTE_DETECTED = "WASTE_DETECTED"
    NO_WASTE_DETECTED = "NO_WASTE_DETECTED"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_SIZE = "INVALID_SIZE"
    INVALID_DIMENSIONS = "INVALID_DIMENSIONS"
    EMPTY_IMAGE = "EMPTY_IMAGE"
    ROBOFLOW_ERROR = "ROBOFLOW_ERROR"


class ValidationResult(BaseModel):
    """
    Result from PreValidator agent's two-layer validation.

    Layer 1: Technical validations (format, size, dimensions)
    Layer 2: Waste detection via Roboflow Object Detection

    Attributes:
        is_valid: True if image passes all validations
        reason: Reason code for the validation result
        metadata: Additional data (Roboflow detections, confidence, bbox)
        cost: Cost of Roboflow API call (typically $0.001)
        fallback_used: True if Roboflow failed and validation bypassed
    """

    is_valid: bool = Field(description="Whether image passes validation")
    reason: ValidationReason = Field(description="Validation result reason code")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional validation metadata")
    cost: float = Field(default=0.001, description="Cost of validation in USD")
    fallback_used: bool = Field(default=False, description="Whether Roboflow fallback was triggered")

    class Config:
        """Pydantic config."""
        use_enum_values = True
