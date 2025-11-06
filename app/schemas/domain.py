"""
Domain models (placeholder).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Material:
    """
    Domain model representing a material.
    """

    name: str
    properties: dict[str, Any]
