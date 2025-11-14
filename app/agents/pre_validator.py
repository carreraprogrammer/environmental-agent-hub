"""
PreValidator Agent V4 - Two-layer waste detection.

Responsibilities:
- Layer 1: Technical validations (format, size, dimensions)
- Layer 2: Waste detection via Roboflow Object Detection API
- Fast and cheap: Roboflow Object Detection (~$0.001/request)
- Aggressive timeout: 3s max latency with fallback

This agent protects the pipeline from abuse and reduces costs by filtering
out non-waste images before expensive classification.
"""

from __future__ import annotations

import asyncio
import base64
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from app.core.config import settings
from app.core.logging import logger
from app.schemas.classification import ValidationReason, ValidationResult

if TYPE_CHECKING:
    from roboflow import Roboflow


class PreValidator:
    """
    PreValidator Agent V4 - Two-layer waste detection.

    Layer 1: Technical validations (format, size, dimensions)
    Layer 2: Roboflow Object Detection for waste presence

    Cost: ~$0.001 per request
    Timeout: 3s with fallback to allow processing

    Example:
        >>> validator = PreValidator()
        >>> result = await validator.validate(image_bytes, "trace-123")
        >>> if result.is_valid:
        ...     print(f"Waste detected: {result.reason}")
        ... else:
        ...     print(f"Rejected: {result.reason}")
    """

    # Roboflow config
    ROBOFLOW_CONFIDENCE_THRESHOLD = 0.4  # Permissive to avoid false negatives
    ROBOFLOW_OVERLAP_THRESHOLD = 0.5
    ROBOFLOW_TIMEOUT = 3.0  # 3 seconds timeout

    # Technical validation thresholds
    MAX_IMAGE_SIZE_MB = 10
    MIN_WIDTH = 224
    MIN_HEIGHT = 224
    ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

    def __init__(
        self,
        model_id: str | None = None,
        confidence_threshold: float | None = None,
        overlap_threshold: float | None = None,
    ):
        """
        Initialize PreValidator with Roboflow client.

        Args:
            model_id: Roboflow model ID (format: workspace/project/version)
            confidence_threshold: Detection confidence threshold (default: 0.4)
            overlap_threshold: Overlap threshold for NMS (default: 0.5)
        """
        # Lazy import to avoid loading Roboflow unless needed
        from roboflow import Roboflow

        self.model_id = model_id or settings.ROBOFLOW_MODEL_ID
        self.confidence_threshold = confidence_threshold or self.ROBOFLOW_CONFIDENCE_THRESHOLD
        self.overlap_threshold = overlap_threshold or self.ROBOFLOW_OVERLAP_THRESHOLD

        # Initialize Roboflow client
        try:
            workspace, project, version = self.model_id.split("/")
        except ValueError as exc:
            raise ValueError(
                f"Roboflow model_id must follow 'workspace/project/version' format, got: {self.model_id}"
            ) from exc

        client = Roboflow(api_key=settings.ROBOFLOW_API_KEY)
        project_ref = client.workspace(workspace).project(project)
        self.model = project_ref.version(version).model

        logger.info(
            "pre_validator_initialized",
            model_id=self.model_id,
            confidence_threshold=self.confidence_threshold,
            overlap_threshold=self.overlap_threshold,
        )

    async def validate(self, image_data: bytes, trace_id: str) -> ValidationResult:
        """
        Validate image using two-layer approach.

        Layer 1: Technical validations (format, size, dimensions)
        Layer 2: Roboflow Object Detection for waste presence

        Args:
            image_data: Image bytes (JPEG, PNG, WEBP)
            trace_id: Request trace ID for logging

        Returns:
            ValidationResult with is_valid, reason, metadata

        Raises:
            ValueError: If image fails Layer 1 validations
        """
        logger.info(
            "pre_validator_started",
            trace_id=trace_id,
            agent="PreValidator",
            model_id=self.model_id,
        )

        # Layer 1: Technical validations
        layer1_result = self._validate_technical(image_data, trace_id)
        if not layer1_result.is_valid:
            logger.info(
                "pre_validator_layer1_reject",
                trace_id=trace_id,
                reason=layer1_result.reason,
            )
            return layer1_result

        # Layer 2: Roboflow waste detection
        try:
            layer2_result = await asyncio.wait_for(
                self._detect_waste_roboflow(image_data, trace_id),
                timeout=self.ROBOFLOW_TIMEOUT,
            )

            logger.info(
                "pre_validator_complete",
                trace_id=trace_id,
                agent="PreValidator",
                is_valid=layer2_result.is_valid,
                reason=layer2_result.reason,
                detections_count=len(layer2_result.metadata.get("detections", [])),
            )

            return layer2_result

        except asyncio.TimeoutError:
            logger.warning(
                "pre_validator_roboflow_timeout",
                trace_id=trace_id,
                timeout_seconds=self.ROBOFLOW_TIMEOUT,
            )
            # Fallback: Allow image to pass to MaterialClassifier
            return ValidationResult(
                is_valid=True,
                reason=ValidationReason.WASTE_DETECTED,
                metadata={"fallback_reason": "roboflow_timeout"},
                cost=0.0,
                fallback_used=True,
            )

        except Exception as e:
            logger.error(
                "pre_validator_roboflow_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Fallback: Allow image to pass to MaterialClassifier
            return ValidationResult(
                is_valid=True,
                reason=ValidationReason.WASTE_DETECTED,
                metadata={"fallback_reason": "roboflow_error", "error": str(e)},
                cost=0.0,
                fallback_used=True,
            )

    def _validate_technical(self, image_data: bytes, trace_id: str) -> ValidationResult:
        """
        Layer 1: Technical validations.

        Validates:
        - Image not empty
        - Format is JPEG, PNG, or WEBP
        - Size < 10MB
        - Dimensions >= 224x224

        Args:
            image_data: Image bytes
            trace_id: Request trace ID

        Returns:
            ValidationResult (is_valid=True if all checks pass)
        """
        # Check if image is empty
        if not image_data or len(image_data) == 0:
            return ValidationResult(
                is_valid=False,
                reason=ValidationReason.EMPTY_IMAGE,
                metadata={"size_bytes": 0},
                cost=0.0,
            )

        # Check file size
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > self.MAX_IMAGE_SIZE_MB:
            return ValidationResult(
                is_valid=False,
                reason=ValidationReason.INVALID_SIZE,
                metadata={"size_mb": size_mb, "max_size_mb": self.MAX_IMAGE_SIZE_MB},
                cost=0.0,
            )

        # Check format and dimensions
        try:
            image = Image.open(BytesIO(image_data))
            image_format = image.format
            width, height = image.size

            # Validate format
            if image_format not in self.ALLOWED_FORMATS:
                return ValidationResult(
                    is_valid=False,
                    reason=ValidationReason.INVALID_FORMAT,
                    metadata={
                        "format": image_format,
                        "allowed_formats": list(self.ALLOWED_FORMATS),
                    },
                    cost=0.0,
                )

            # Validate dimensions
            if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                return ValidationResult(
                    is_valid=False,
                    reason=ValidationReason.INVALID_DIMENSIONS,
                    metadata={
                        "width": width,
                        "height": height,
                        "min_width": self.MIN_WIDTH,
                        "min_height": self.MIN_HEIGHT,
                    },
                    cost=0.0,
                )

            logger.debug(
                "pre_validator_layer1_pass",
                trace_id=trace_id,
                format=image_format,
                width=width,
                height=height,
                size_mb=round(size_mb, 2),
            )

            # All technical validations passed
            return ValidationResult(
                is_valid=True,
                reason=ValidationReason.WASTE_DETECTED,  # Temporary, will be overridden by Layer 2
                metadata={
                    "format": image_format,
                    "width": width,
                    "height": height,
                    "size_mb": round(size_mb, 2),
                },
                cost=0.0,
            )

        except Exception as e:
            logger.warning(
                "pre_validator_layer1_image_error",
                trace_id=trace_id,
                error=str(e),
            )
            return ValidationResult(
                is_valid=False,
                reason=ValidationReason.INVALID_FORMAT,
                metadata={"error": str(e)},
                cost=0.0,
            )

    async def _detect_waste_roboflow(
        self, image_data: bytes, trace_id: str
    ) -> ValidationResult:
        """
        Layer 2: Roboflow Object Detection for waste presence.

        Uses Roboflow Object Detection model to detect waste objects.
        Expected classes: plastic, paper, cardboard, metal, glass, biodegradable

        Args:
            image_data: Image bytes
            trace_id: Request trace ID

        Returns:
            ValidationResult with detections metadata
        """
        # Encode image to base64 for Roboflow
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Call Roboflow API
        try:
            # Run in thread pool since Roboflow SDK is synchronous
            prediction = await asyncio.to_thread(
                self.model.predict,
                image_base64,
                confidence=self.confidence_threshold,
                overlap=self.overlap_threshold,
                hosted=False,  # We're passing base64 data
            )

            # Extract predictions
            predictions = getattr(prediction, "predictions", None) or []

            # Parse detections
            detections = []
            for pred in predictions:
                detections.append({
                    "class": getattr(pred, "class_name", "unknown"),
                    "confidence": float(getattr(pred, "confidence", 0.0)),
                    "x": float(getattr(pred, "x", 0)),
                    "y": float(getattr(pred, "y", 0)),
                    "width": float(getattr(pred, "width", 0)),
                    "height": float(getattr(pred, "height", 0)),
                })

            # Log detections for analysis
            logger.info(
                "pre_validator_roboflow_detections",
                trace_id=trace_id,
                num_detections=len(detections),
                classes=[d["class"] for d in detections],
                confidences=[d["confidence"] for d in detections],
            )

            # Determine if waste was detected
            if len(detections) == 0:
                return ValidationResult(
                    is_valid=False,
                    reason=ValidationReason.NO_WASTE_DETECTED,
                    metadata={
                        "detections": [],
                        "num_detections": 0,
                    },
                    cost=0.001,  # Roboflow API cost
                    fallback_used=False,
                )
            else:
                return ValidationResult(
                    is_valid=True,
                    reason=ValidationReason.WASTE_DETECTED,
                    metadata={
                        "detections": detections,
                        "num_detections": len(detections),
                        "classes": list(set(d["class"] for d in detections)),
                    },
                    cost=0.001,  # Roboflow API cost
                    fallback_used=False,
                )

        except Exception as e:
            logger.error(
                "pre_validator_roboflow_api_error",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


# Legacy function for backward compatibility
def validate_payload(payload: dict[str, object]) -> bool:
    """
    Placeholder validation logic for incoming payloads.

    DEPRECATED: Use PreValidator class instead.

    Args:
        payload: Request payload data

    Returns:
        bool: True if payload passes placeholder validation
    """
    return bool(payload)
