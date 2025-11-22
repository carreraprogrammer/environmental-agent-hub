"""
Response schemas for classification pipeline.

This module defines the final response schemas returned by the Assembler agent
after consolidating outputs from all agents in the pipeline.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.bin_color import BinColor
from app.schemas.classification import Material


class ResponseMeta(BaseModel):
    """
    Metadata about the classification request.

    Contains information about model usage, timing, costs, and pipeline execution
    that is useful for debugging and monitoring.

    Attributes:
        model_used: Model identifier (e.g., "openai/gpt-4o")
        model_provider: Provider name (e.g., "openai")
        latency_ms: Total request latency in milliseconds
        cost_usd: Total cost of all API calls in USD
        validator_passed: Whether image passed validation
        estimation_method: Volume estimation method used ("lookup", "fallback", etc.)
        input_format: Input format ("bytes" or "url")
        s3_upload_status: Status of S3 upload ("pending", "uploaded", etc.)
        agents_executed: List of agents that were executed in the pipeline
        backend_integration: Whether backend integration was performed
    """

    model_used: str = Field(description="Model identifier used for classification")
    model_provider: str = Field(description="Model provider name")
    latency_ms: int = Field(ge=0, description="Total latency in milliseconds")
    cost_usd: float = Field(ge=0.0, description="Total cost in USD")
    validator_passed: bool = Field(description="Whether image passed validation")
    estimation_method: str = Field(description="Volume estimation method")
    input_format: str = Field(description="Input format (bytes or url)")
    s3_upload_status: str = Field(description="S3 upload status")
    agents_executed: list[str] = Field(description="List of executed agents")
    backend_integration: bool = Field(
        default=False, description="Whether backend integration was performed"
    )


class EnvironmentalImpact(BaseModel):
    """
    Environmental impact data from Backend integration.

    This is populated when backend_integration is True and contains
    the environmental impact data calculated by the Backend.

    Attributes:
        co2_saved_kg: CO2 saved in kilograms
        water_saved_l: Water saved in liters
        energy_saved_kwh: Energy saved in kilowatt-hours
    """

    co2_saved_kg: float = Field(ge=0.0, description="CO2 saved in kilograms")
    water_saved_l: float = Field(ge=0.0, description="Water saved in liters")
    energy_saved_kwh: float = Field(ge=0.0, description="Energy saved in kilowatt-hours")


class ClassifyResponse(BaseModel):
    """
    Final classification response returned to the client.

    This is the main response schema that consolidates outputs from all
    agents in the pipeline into a single, validated response object.

    Attributes:
        material: Classified material type (PLASTIC, METAL, GLASS, etc.)
        confidence: Classification confidence score (0.0 to 1.0)
        color: Bin color for proper disposal
        volume_ml: Estimated volume in milliliters
        weight_g: Estimated weight in grams
        waste_type_code: Backend waste type code
        message: User-friendly feedback message
        meta: Request metadata (timing, costs, etc.)
        environmental_impact: Environmental impact data (if backend integrated)
        characteristics: Material-specific characteristics
    """

    material: Material = Field(description="Classified material type")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Classification confidence (0.0 to 1.0)"
    )
    color: BinColor = Field(description="Bin color for disposal")
    volume_ml: float = Field(ge=0.0, description="Estimated volume in milliliters")
    weight_g: float = Field(ge=0.0, description="Estimated weight in grams")
    waste_type_code: str = Field(min_length=1, description="Backend waste type code")
    message: str = Field(
        min_length=1, max_length=240, description="User feedback message"
    )
    meta: ResponseMeta = Field(description="Request metadata")
    environmental_impact: EnvironmentalImpact | None = Field(
        default=None, description="Environmental impact data"
    )
    characteristics: dict[str, Any] | None = Field(
        default=None, description="Material-specific characteristics"
    )
