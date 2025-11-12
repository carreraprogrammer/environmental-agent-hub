"""
Request schemas for classification pipeline.

Supports two input formats:
1. ClassifyRequestForm (multipart/form-data with bytes) - PREFERRED
2. ClassifyRequest (JSON with image_url) - LEGACY
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ClassifyRequest(BaseModel):
    """
    Request schema for JSON input (legacy).

    Used for backward compatibility with systems that send image URLs.
    The Router agent will fetch the image from the URL and convert to bytes.

    Attributes:
        scan_id: Unique identifier for this scan (auto-generated if not provided)
        station_id: Identifier of the scanning station (1-50 chars)
        image_url: S3 or public URL to the image
        tenant_id: Identifier of the tenant (1-50 chars)
        trace_id: Distributed tracing ID (auto-generated if not provided)
        idempotency_key: Key for idempotent operations (auto-generated if not provided)
    """

    scan_id: UUID = Field(default_factory=uuid4)
    station_id: str = Field(min_length=1, max_length=50)
    image_url: str = Field(description="S3 or public URL")
    tenant_id: str = Field(min_length=1, max_length=50)
    trace_id: UUID = Field(default_factory=uuid4)
    idempotency_key: UUID = Field(default_factory=uuid4)

    @field_validator("image_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that image_url starts with valid protocol."""
        if not v.startswith(("http://", "https://", "s3://")):
            raise ValueError("Invalid URL format - must start with http://, https://, or s3://")
        return v


class ClassifyRequestForm(BaseModel):
    """
    Request schema for multipart/form-data (preferred).

    Preferred format for optimal performance - image is already in memory
    and does not require downloading from a URL.

    Attributes:
        scan_id: Unique identifier for this scan (auto-generated if not provided)
        station_id: Identifier of the scanning station (1-50 chars)
        image_bytes: Raw image data in bytes (populated by Router or from form data)
        tenant_id: Identifier of the tenant (1-50 chars)
        trace_id: Distributed tracing ID (auto-generated if not provided)
        idempotency_key: Key for idempotent operations (auto-generated if not provided)
    """

    scan_id: UUID = Field(default_factory=uuid4)
    station_id: str = Field(min_length=1, max_length=50)
    image_bytes: Optional[bytes] = None
    tenant_id: str = Field(min_length=1, max_length=50)
    trace_id: UUID = Field(default_factory=uuid4)
    idempotency_key: UUID = Field(default_factory=uuid4)


# Legacy alias for backward compatibility
class ClassificationRequest(ClassifyRequest):
    """
    Legacy alias for ClassifyRequest.

    Maintained for backward compatibility with existing code.
    New code should use ClassifyRequest or ClassifyRequestForm.
    """

    pass
