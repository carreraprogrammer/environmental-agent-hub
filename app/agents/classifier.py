"""
Classifier Agent - Classifies waste material using active adapter.

Responsibilities:
- Classify waste material (PLASTIC, PAPER, GLASS, METAL, ORGANIC, OTHER)
- Use adapter from ClassifierFactory (supports multiple models)
- Apply confidence thresholds (0.3 and 0.6)
- Return material, confidence, and reasoning

This agent enables scientific comparison between models (OpenAI, Claude, Roboflow)
for thesis research by using the adapter pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import logger
from app.schemas.domain import ClassificationResult, WasteMaterial

if TYPE_CHECKING:
    from app.adapters.base import ClassifierAdapter


class Classifier:
    """
    Classifier Agent - Classifies waste material using active adapter.

    Uses adapter pattern to support multiple models:
    - OpenAI GPT-4 Vision
    - Anthropic Claude
    - Google Gemini
    - Roboflow (specialized)

    Example:
        >>> from app.factories.classifier_factory import ClassifierFactory
        >>> classifier = Classifier()
        >>> adapter = ClassifierFactory.create("openai-gpt4o")
        >>> result = await classifier.classify(
        ...     "https://example.com/image.jpg",
        ...     adapter,
        ...     "trace-123"
        ... )
        >>> print(f"Material: {result.material.value}, Confidence: {result.confidence}")
    """

    def __init__(
        self,
        confidence_threshold_low: float = 0.3,
        confidence_threshold_medium: float = 0.6,
    ):
        """
        Initialize Classifier with confidence thresholds.

        Args:
            confidence_threshold_low: Minimum acceptable confidence (default: 0.3)
            confidence_threshold_medium: Threshold for mapping to OTHER (default: 0.6)
        """
        self.confidence_threshold_low = confidence_threshold_low
        self.confidence_threshold_medium = confidence_threshold_medium

    async def classify(
        self, image_url: str, adapter: ClassifierAdapter, trace_id: str
    ) -> ClassificationResult:
        """
        Classify waste material using provided adapter.

        Args:
            image_url: URL or data URI of the image to classify
            adapter: ClassifierAdapter instance (from ClassifierFactory)
            trace_id: Request trace ID for logging

        Returns:
            ClassificationResult with material, confidence, reasoning

        Raises:
            ValueError: If confidence too low (<0.3) or classification fails

        Example:
            >>> classifier = Classifier()
            >>> adapter = ClassifierFactory.create("openai-gpt4o")
            >>> result = await classifier.classify(
            ...     "https://example.com/bottle.jpg",
            ...     adapter,
            ...     "trace-abc123"
            ... )
            >>> if result.material == WasteMaterial.PLASTIC:
            ...     print("Plastic detected!")
        """
        logger.info(
            "classifier_started",
            trace_id=trace_id,
            agent="Classifier",
            model=adapter.model_name,
            provider=adapter.model_provider,
        )

        try:
            # Call adapter to classify
            result = await adapter.classify(image_url, trace_id=trace_id)

            logger.info(
                "classifier_complete",
                trace_id=trace_id,
                agent="Classifier",
                material=result.material.value,
                confidence=result.confidence,
                model=result.model_used,
            )

            # Apply confidence thresholds
            return self._apply_thresholds(result, trace_id)

        except Exception as e:
            logger.error(
                "classifier_error",
                trace_id=trace_id,
                agent="Classifier",
                error=str(e),
                error_type=type(e).__name__,
                model=adapter.model_name,
            )
            raise ValueError(f"Classification failed: {str(e)}")

    def _apply_thresholds(
        self, result: ClassificationResult, trace_id: str
    ) -> ClassificationResult:
        """
        Apply confidence thresholds to classification result.

        Thresholds:
        - <0.3: Reject (raise ValueError)
        - 0.3-0.6: Map to OTHER (medium confidence)
        - >0.6: Use classified material (high confidence)

        Args:
            result: Classification result from adapter
            trace_id: Request trace ID for logging

        Returns:
            ClassificationResult with thresholds applied

        Raises:
            ValueError: If confidence < 0.3
        """
        # Threshold 1: Very low confidence (<0.3) → Reject
        if result.confidence < self.confidence_threshold_low:
            logger.warning(
                "classifier_low_confidence",
                trace_id=trace_id,
                agent="Classifier",
                confidence=result.confidence,
                threshold=self.confidence_threshold_low,
                material=result.material.value,
            )
            raise ValueError(
                f"Confidence too low: {result.confidence:.2f} < {self.confidence_threshold_low:.2f}"
            )

        # Threshold 2: Medium confidence (0.3-0.6) → Map to OTHER
        if result.confidence < self.confidence_threshold_medium:
            logger.info(
                "classifier_medium_confidence_mapped_to_other",
                trace_id=trace_id,
                agent="Classifier",
                original_material=result.material.value,
                confidence=result.confidence,
                threshold=self.confidence_threshold_medium,
            )
            # Map to OTHER but preserve original confidence and reasoning
            result.material = WasteMaterial.OTHER

        return result
