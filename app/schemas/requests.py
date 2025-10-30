"""
Request schemas (placeholder).
"""

from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class ClassificationRequest(BaseModel):
    """
    Placeholder request schema for classification.
    """

    image_url: HttpUrl
    metadata: dict[str, str] | None = None
