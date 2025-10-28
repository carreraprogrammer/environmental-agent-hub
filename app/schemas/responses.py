"""
Response schemas (placeholder).
"""

from __future__ import annotations

from pydantic import BaseModel


class ClassificationResponse(BaseModel):
    """
    Placeholder response schema for classification.
    """

    status: str
    label: str | None = None
    confidence: float | None = None
    feedback: str | None = None
