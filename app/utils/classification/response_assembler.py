"""
ResponseAssembler - Builds the final ClassifyResponse from pipeline outputs.

ARCHITECTURE NOTE: This is a UTILITY, not an AI agent.
Pure data consolidation with Pydantic validation.

Consolidates outputs from the classification pipeline into a single,
validated ClassifyResponse object.

Philosophy:
- Pure assembly: no business logic, just data consolidation
- Deterministic: no AI, no I/O
- Pydantic validation: ensures response contract compliance
- Synchronous: no async since there's no I/O

Cost: $0 per request (no external API calls)
Latency: <10ms p95

Example:
    >>> from app.utils.classification.response_assembler import ResponseAssembler
    >>> from app.schemas.classification import Material
    >>> from app.schemas.bin_color import BinColor
    >>> import time
    >>>
    >>> assembler = Assembler()
    >>> start_time = time.time()
    >>> response = assembler.build_response(
    ...     material=Material.PLASTIC,
    ...     confidence=0.89,
    ...     characteristics={"material_specific": "PET"},
    ...     volume_ml=520.0,
    ...     weight_g=15.2,
    ...     estimation_method="lookup",
    ...     color=BinColor.WHITE,
    ...     waste_type_code="PET_BOTTLE_500ML",
    ...     message="Great job recycling!",
    ...     model_used="openai/gpt-4o",
    ...     model_provider="openai",
    ...     trace_id="test-trace",
    ...     start_time=start_time,
    ...     cost_usd=0.0122,
    ...     input_format="bytes",
    ...     agents_executed=["router", "prevalidator", "classifier"]
    ... )
    >>> print(response.material)  # Material.PLASTIC
"""

from __future__ import annotations

import time
from typing import Any

from app.core.logging import logger
from app.schemas.bin_color import BinColor
from app.schemas.classification import Material
from app.schemas.responses import ClassifyResponse, ResponseMeta


class ResponseAssembler:
    """
    Utility for assembling the final ClassifyResponse from pipeline outputs.

    NOT AN AGENT: Pure data assembly, no AI/ML involved.

    Consolidates outputs from the classification pipeline into a single,
    validated response object. It performs no business logic - only data
    assembly and validation via Pydantic.

    Synchronous because it performs no I/O operations.
    All it does is construct Python objects in memory.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def build_response(
        self,
        material: Material,
        confidence: float,
        characteristics: dict[str, Any] | None,
        volume_ml: float,
        weight_g: float,
        estimation_method: str,
        color: BinColor,
        waste_type_code: str,
        message: str,
        model_used: str,
        model_provider: str,
        trace_id: str,
        start_time: float,
        cost_usd: float,
        input_format: str,
        agents_executed: list[str],
    ) -> ClassifyResponse:
        """
        Build the final ClassifyResponse from agent outputs.

        Consolidates all outputs from the classification pipeline agents
        into a single, validated response object. Calculates latency from
        start_time and constructs ResponseMeta with all pipeline metadata.

        Args:
            material: Material type from Classifier
            confidence: Confidence score from Classifier (0.0 to 1.0)
            characteristics: Material characteristics from SubtypeDetector
            volume_ml: Volume in milliliters from VolumeEstimator
            weight_g: Weight in grams from VolumeEstimator
            estimation_method: Volume estimation method used
            color: Bin color from Mapper
            waste_type_code: Backend waste type code from WasteTypeMapper
            message: Feedback message from FeedbackCoach
            model_used: Model identifier from Classifier
            model_provider: Model provider from Classifier
            trace_id: Request trace ID for logging
            start_time: Pipeline start time (from time.time())
            cost_usd: Total cost of all API calls
            input_format: Input format ("bytes" or "url")
            agents_executed: List of agents executed in pipeline

        Returns:
            ClassifyResponse: Validated response object ready for client

        Raises:
            pydantic.ValidationError: If any field fails Pydantic validation
        """
        logger.info(
            "assembler_started",
            trace_id=trace_id,
            agent="Assembler",
        )

        # Calculate latency in milliseconds
        latency_ms = int((time.time() - start_time) * 1000)

        # Construct ResponseMeta with all pipeline metadata
        meta = ResponseMeta(
            model_used=model_used,
            model_provider=model_provider,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            validator_passed=True,
            estimation_method=estimation_method,
            input_format=input_format,
            s3_upload_status="pending",
            agents_executed=agents_executed,
            backend_integration=False,
        )

        # Construct ClassifyResponse with all agent outputs
        # Pydantic validates all fields automatically
        response = ClassifyResponse(
            material=material,
            confidence=confidence,
            color=color,
            volume_ml=volume_ml,
            weight_g=weight_g,
            waste_type_code=waste_type_code,
            message=message,
            meta=meta,
            environmental_impact=None,
            characteristics=characteristics if characteristics else None,
        )

        logger.info(
            "assembler_complete",
            trace_id=trace_id,
            agent="Assembler",
            latency_ms=latency_ms,
            cost_usd=cost_usd,
        )

        return response
