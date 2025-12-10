"""
Discrepancy tracking schemas for Fast Path vs Full Pipeline comparison.

This module defines schemas for tracking classification discrepancies between
Fast Path (Roboflow) and Full Pipeline (Gemini/GPT-4o), enabling dataset
collection for model retraining.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.classification import Material


class DiscrepancyRecord(BaseModel):
    """
    Record of discrepancy between Fast Path and Full Pipeline classification.

    This captures cases where Roboflow's fast classification differs from
    the ground truth provided by Gemini/GPT-4o, enabling collection of
    correction data for future model retraining.

    Attributes:
        trace_id: Request trace identifier
        scan_id: Scan identifier (optional)
        tenant_id: Tenant identifier (optional)
        station_id: Station identifier (optional)
        fast_path_material: Material classified by Roboflow (incorrect)
        fast_path_confidence: Roboflow confidence score
        fast_path_model: Roboflow model identifier
        ground_truth_material: Material from Gemini/GPT (correct)
        ground_truth_confidence: Gemini/GPT confidence score
        ground_truth_model: Gemini/GPT model identifier
        image_url: S3 URL for retraining dataset (optional)
        timestamp: When discrepancy was detected
        confidence_delta: Difference in confidence (ground_truth - fast_path)
    """

    # Identifiers
    trace_id: str = Field(description="Request trace identifier")
    scan_id: Optional[str] = Field(default=None, description="Scan identifier")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    station_id: Optional[str] = Field(default=None, description="Station identifier")

    # Fast Path (Roboflow) - What needs correction
    fast_path_material: Material = Field(description="Material classified by Roboflow")
    fast_path_confidence: float = Field(
        ge=0.0, le=1.0, description="Roboflow confidence score"
    )
    fast_path_model: str = Field(
        default="roboflow/waste-classifier-louut-b9sot",
        description="Roboflow model identifier",
    )

    # Ground Truth (Gemini/GPT) - The correction
    ground_truth_material: Material = Field(
        description="Material from Gemini/GPT (ground truth)"
    )
    ground_truth_confidence: float = Field(
        ge=0.0, le=1.0, description="Gemini/GPT confidence score"
    )
    ground_truth_model: str = Field(
        description="Gemini/GPT model identifier (e.g., 'google/gemini-2.0-flash')"
    )

    # Image for retraining
    image_url: Optional[str] = Field(
        default=None, description="S3 URL for retraining dataset"
    )

    # Metadata
    timestamp: datetime = Field(description="When discrepancy was detected")
    confidence_delta: float = Field(
        description="Confidence difference (ground_truth - fast_path)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trace_id": "req-abc123",
                "scan_id": "scan-456",
                "tenant_id": "udenar",
                "station_id": "station-1",
                "fast_path_material": "PLASTIC",
                "fast_path_confidence": 0.72,
                "fast_path_model": "roboflow/waste-classifier-louut-b9sot",
                "ground_truth_material": "METAL",
                "ground_truth_confidence": 0.94,
                "ground_truth_model": "google/gemini-2.0-flash",
                "image_url": "s3://agent-hub/scans/scan-456.jpg",
                "timestamp": "2025-11-26T14:30:00Z",
                "confidence_delta": 0.22,
            }
        }
    )


class CorrectionPayload(BaseModel):
    """
    Payload for sending corrections to Backend Rails API.

    This schema maps to the Backend's POST /api/v1/classification_corrections
    endpoint, enabling persistence of correction data for analytics and
    retraining workflows.

    Attributes:
        trace_id: Request trace identifier
        scan_id: Scan identifier (optional)
        tenant_id: Tenant identifier (optional)
        station_id: Station identifier (optional)
        incorrect_material: Material classified incorrectly (Roboflow)
        incorrect_confidence: Confidence of incorrect classification
        incorrect_model: Model that made incorrect classification
        correct_material: Correct material classification (Gemini/GPT)
        correct_confidence: Confidence of correct classification
        correct_model: Model that made correct classification
        image_url: S3 URL for retraining dataset (optional)
        timestamp: When correction was created
    """

    # Identifiers
    trace_id: str = Field(description="Request trace identifier")
    scan_id: Optional[str] = Field(default=None, description="Scan identifier")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    station_id: Optional[str] = Field(default=None, description="Station identifier")

    # Incorrect classification (Roboflow)
    incorrect_material: str = Field(description="Material classified incorrectly")
    incorrect_confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence of incorrect classification"
    )
    incorrect_model: str = Field(
        description="Model that made incorrect classification"
    )

    # Correct classification (Gemini/GPT)
    correct_material: str = Field(description="Correct material classification")
    correct_confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence of correct classification"
    )
    correct_model: str = Field(
        description="Model that made correct classification"
    )

    # For retraining
    image_url: Optional[str] = Field(
        default=None, description="S3 URL for retraining dataset"
    )

    # Metadata
    timestamp: datetime = Field(description="When correction was created")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trace_id": "req-abc123",
                "scan_id": "scan-456",
                "tenant_id": "udenar",
                "station_id": "station-1",
                "incorrect_material": "PLASTIC",
                "incorrect_confidence": 0.72,
                "incorrect_model": "roboflow/waste-classifier-louut-b9sot",
                "correct_material": "METAL",
                "correct_confidence": 0.94,
                "correct_model": "google/gemini-2.0-flash",
                "image_url": "s3://agent-hub/scans/scan-456.jpg",
                "timestamp": "2025-11-26T14:30:00Z",
            }
        }
    )
