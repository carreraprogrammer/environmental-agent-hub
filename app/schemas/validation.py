"""
Validation schemas for PreValidator agent.

The PreValidator agent performs binary waste detection to filter out
non-waste images (trolls, selfies, landscapes, etc.) before expensive
classification.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """
    Result from PreValidator agent's waste detection.

    This schema represents the output of the PreValidator agent which
    determines if an image contains waste material worthy of classification.

    Attributes:
        has_waste: True if image contains waste/trash, False otherwise
        confidence: Model confidence score (0.0 to 1.0)
        reason: Brief explanation in Spanish of what was detected
    """

    has_waste: bool = Field(
        description="Whether the image contains waste material"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 (low) to 1.0 (high)"
    )
    reason: str = Field(
        min_length=1,
        max_length=500,
        description="Brief explanation in Spanish of detection result"
    )
