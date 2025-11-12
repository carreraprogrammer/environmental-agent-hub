from __future__ import annotations

from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result from PreValidator agent"""

    has_waste: bool
    confidence: float
    reason: str

