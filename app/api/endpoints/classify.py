"""
Classification endpoint for waste material detection.

This endpoint receives requests from the Frontend, executes the 10-agent pipeline,
and returns classification results. Supports two input formats:
1. multipart/form-data (preferred - 60% faster with bytes)
2. JSON with image_url (legacy - backward compatible)

Key Features:
- Automatic format detection (bytes vs URL)
- Background S3 upload (non-blocking)
- Dependency injection for testing
- Comprehensive error handling
- Detailed logging with trace_id
- Response headers (X-Trace-Id, X-Request-Duration)

Performance:
- Multipart/form-data: ~600ms (preferred)
- JSON with URL: ~1500ms (legacy)
- Timeout: 10 seconds
"""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from fastapi import Response
from pydantic import ValidationError as PydanticValidationError

from app.agents.fast_classifier import FastClassifier
from app.api.dependencies import get_pipeline, get_s3_service
from app.core.config import settings
from app.core.logging import logger
from app.factories.classifier_factory import ClassifierFactory
from app.orchestrator.fast_pipeline import ValidationPipeline
from app.orchestrator.pipeline import ClassificationError, Pipeline, ValidationError
from app.schemas.requests import ClassifyRequest, ClassifyRequestForm
from app.schemas.responses import ClassifyResponse
from app.services.s3_service import S3Service
from app.utils.classification.response_assembler import ResponseAssembler

router = APIRouter(prefix="/api/v1", tags=["classification"])

# Initialize Fast Path components (lazy loaded)
_fast_classifier: FastClassifier | None = None
_validation_pipeline: ValidationPipeline | None = None


def get_fast_classifier() -> FastClassifier:
    """Get or create FastClassifier instance."""
    global _fast_classifier
    if _fast_classifier is None:
        roboflow_adapter = ClassifierFactory.create("roboflow")
        _fast_classifier = FastClassifier(roboflow_adapter)
    return _fast_classifier


def get_validation_pipeline(main_pipeline: Pipeline) -> ValidationPipeline:
    """Get or create ValidationPipeline instance."""
    global _validation_pipeline
    if _validation_pipeline is None:
        _validation_pipeline = ValidationPipeline(main_pipeline)
    return _validation_pipeline


@router.post("/classify", response_model=ClassifyResponse)
async def classify_waste(
    fastapi_request: FastAPIRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    pipeline: Pipeline = Depends(get_pipeline),
    s3_service: S3Service = Depends(get_s3_service),
) -> ClassifyResponse:
    """
    Classify waste material from image.

    Supports two input formats:
    1. **multipart/form-data** (PREFERRED - 60% faster):
       - image: Binary image file
       - scan_id: Unique scan identifier (UUID)
       - station_id: Station identifier (1-50 chars)
       - tenant_id: Tenant identifier (1-50 chars)
       - trace_id: Optional tracing ID (UUID)
       - idempotency_key: Optional idempotency key (UUID)

    2. **JSON** (LEGACY - backward compatible):
       - scan_id: Unique scan identifier (UUID)
       - station_id: Station identifier (1-50 chars)
       - image_url: S3 or public image URL
       - tenant_id: Tenant identifier (1-50 chars)
       - trace_id: Optional tracing ID (UUID)
       - idempotency_key: Optional idempotency key (UUID)

    Args:
        response: FastAPI response object for setting headers
        background_tasks: FastAPI background tasks for S3 upload
        image: Uploaded image file (multipart only)
        scan_id: Scan identifier (multipart only)
        station_id: Station identifier (multipart only)
        tenant_id: Tenant identifier (multipart only)
        trace_id: Optional tracing ID (multipart only)
        idempotency_key: Optional idempotency key (multipart only)
        request: JSON request body (legacy only)
        pipeline: Injected Pipeline orchestrator
        s3_service: Injected S3 service

    Returns:
        ClassifyResponse: Complete classification result with material, confidence,
                         color, volume, weight, waste_type_code, and metadata

    Raises:
        HTTPException 400: Validation error (no waste detected, low confidence, etc.)
        HTTPException 504: Pipeline timeout (>10 seconds)
        HTTPException 500: Internal server error

    Examples:
        Multipart request (curl):
        ```bash
        curl -X POST http://localhost:8000/api/v1/classify \\
          -F "image=@waste.jpg" \\
          -F "scan_id=123e4567-e89b-12d3-a456-426614174000" \\
          -F "station_id=FAC-ING-01" \\
          -F "tenant_id=unarino"
        ```

        JSON request (curl):
        ```bash
        curl -X POST http://localhost:8000/api/v1/classify \\
          -H "Content-Type: application/json" \\
          -d '{
            "scan_id": "123e4567-e89b-12d3-a456-426614174000",
            "station_id": "FAC-ING-01",
            "image_url": "https://s3.amazonaws.com/.../waste.jpg",
            "tenant_id": "unarino"
          }'
        ```
    """
    start_time = time.time()

    try:
        # STEP 1: Detect input format and build request
        # Check content-type to determine format
        content_type = fastapi_request.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            # MULTIPART FORMAT (preferred)
            form_data = await fastapi_request.form()
            image_file = form_data.get("image")
            scan_id = form_data.get("scan_id")
            station_id = form_data.get("station_id")
            tenant_id = form_data.get("tenant_id")
            trace_id = form_data.get("trace_id")
            idempotency_key = form_data.get("idempotency_key")

            if not image_file or not scan_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "INVALID_INPUT",
                        "message": "Multipart request must include 'image' and 'scan_id'",
                        "suggestion": "Provide both image file and scan_id",
                    },
                )

            logger.info(
                "classify_request_received",
                input_format="multipart",
                scan_id=scan_id,
                station_id=station_id,
                trace_id=trace_id or "auto-generated",
            )

            image_bytes = await image_file.read()

            try:
                form_kwargs = {
                    "station_id": station_id,  # type: ignore
                    "image_bytes": image_bytes,
                    "tenant_id": tenant_id,  # type: ignore
                }

                if scan_id:
                    form_kwargs["scan_id"] = UUID(scan_id)
                if trace_id:
                    form_kwargs["trace_id"] = UUID(trace_id)
                if idempotency_key:
                    form_kwargs["idempotency_key"] = UUID(idempotency_key)

                request_data = ClassifyRequestForm(**form_kwargs)
            except (ValueError, PydanticValidationError) as e:
                logger.warning(
                    "classify_request_validation_failed",
                    error=str(e),
                    input_format="multipart",
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "VALIDATION_ERROR",
                        "message": "Invalid request parameters",
                        "details": str(e),
                    },
                ) from e

            input_format = "bytes"
            request_trace_id = str(request_data.trace_id)

            background_tasks.add_task(
                s3_service.upload_image,
                image_bytes,
                request_data.tenant_id,
                request_trace_id,
            )

        elif "application/json" in content_type:
            # JSON FORMAT (legacy)
            try:
                json_body = await fastapi_request.json()
                request_data = ClassifyRequest(**json_body)

                logger.info(
                    "classify_request_received",
                    input_format="json",
                    scan_id=str(request_data.scan_id),
                    station_id=request_data.station_id,
                    trace_id=str(request_data.trace_id),
                )

                input_format = "url"
                request_trace_id = str(request_data.trace_id)

            except (ValueError, PydanticValidationError) as e:
                logger.warning(
                    "classify_request_validation_failed",
                    error=str(e),
                    input_format="json",
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "VALIDATION_ERROR",
                        "message": "Invalid JSON request",
                        "details": str(e),
                    },
                ) from e

        else:
            logger.warning(
                "classify_request_rejected",
                reason="missing_input",
                message="Must provide either multipart form data or JSON request",
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_INPUT",
                    "message": "Must provide either multipart form data or JSON request",
                    "suggestion": (
                        "Send image as multipart/form-data (preferred) "
                        "or JSON with image_url (legacy)"
                    ),
                },
            )

        # STEP 2: Execute pipeline (Fast Path or Full Path)
        logger.info(
            "pipeline_execution_started",
            trace_id=request_trace_id,
            input_format=input_format,
            fast_path_enabled=settings.ENABLE_FAST_PATH,
        )

        # Check if fast path should be used
        if settings.ENABLE_FAST_PATH and input_format == "bytes":
            # FAST PATH: Roboflow fast response + background validation
            try:
                fast_classifier = get_fast_classifier()
                fast_result = await fast_classifier.classify_fast(
                    image_data=image_bytes,
                    trace_id=request_trace_id,
                )
                
                # If confidence is high, return fast response and validate in background
                if not fast_result["should_validate"]:
                    logger.info(
                        "fast_path_selected",
                        trace_id=request_trace_id,
                        confidence=fast_result["confidence"],
                        latency_ms=fast_result["latency_ms"],
                    )
                    
                    # Build fast response
                    assembler = ResponseAssembler()
                    result = assembler.build_response(
                        material=fast_result["material"],
                        confidence=fast_result["confidence"],
                        characteristics=None,
                        volume_ml=500.0,  # Default
                        weight_g=15.0,  # Default
                        estimation_method="fast_default",
                        color=fast_result["color"],
                        waste_type_code="PENDING",  # Will be updated in background
                        message=fast_result["message"],
                        model_used=fast_result["model_used"],
                        model_provider=fast_result["model_provider"],
                        trace_id=request_trace_id,
                        start_time=start_time,
                        cost_usd=0.001,  # Roboflow cost
                        input_format=input_format,
                        agents_executed=["FastClassifier"],
                    )
                    
                    # Schedule background validation
                    validation_pipeline = get_validation_pipeline(pipeline)
                    background_tasks.add_task(
                        validation_pipeline.validate_and_sync,
                        request=request_data,
                        fast_result=fast_result,
                        trace_id=request_trace_id,
                    )
                    
                    result.meta.fast_mode = True
                    result.meta.validation_status = "pending"
                    
                else:
                    # Low confidence - use full pipeline
                    logger.info(
                        "fast_path_fallback_to_full",
                        trace_id=request_trace_id,
                        confidence=fast_result["confidence"],
                        threshold=settings.FAST_PATH_CONFIDENCE_THRESHOLD,
                    )
                    result = await pipeline.process(request_data)
                    
            except Exception as e:
                # If fast path fails, fallback to full pipeline
                logger.warning(
                    "fast_path_failed_fallback_to_full",
                    trace_id=request_trace_id,
                    error=str(e),
                )
                result = await pipeline.process(request_data)
        else:
            # FULL PATH: Traditional pipeline
            result = await pipeline.process(request_data)

        # STEP 3: Add metadata
        result.meta.input_format = input_format
        if input_format == "bytes":
            result.meta.s3_upload_status = "pending"

        # STEP 4: Calculate latency and set response headers
        elapsed_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Trace-Id"] = request_trace_id
        response.headers["X-Request-Duration"] = f"{elapsed_ms}ms"

        # STEP 5: Log success
        logger.info(
            "classify_request_completed",
            trace_id=request_trace_id,
            material=result.material.value,
            confidence=result.confidence,
            latency_ms=elapsed_ms,
            cost_usd=result.meta.cost_usd,
            input_format=input_format,
            s3_upload_status=result.meta.s3_upload_status,
        )

        return result

    except ValidationError as e:
        # Pipeline validation errors (400-level)
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.warning(
            "classify_request_rejected",
            error_code=e.error_code,
            message=e.message,
            suggestion=e.suggestion,
            latency_ms=elapsed_ms,
        )

        raise HTTPException(
            status_code=400,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "suggestion": e.suggestion,
            },
        ) from e

    except TimeoutError as e:
        # Pipeline timeout (504)
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "classify_request_timeout",
            latency_ms=elapsed_ms,
            error=str(e),
        )

        raise HTTPException(
            status_code=504,
            detail={
                "error_code": "TIMEOUT",
                "message": "Classification request timeout exceeded",
                "suggestion": "Please try again with a clearer image",
            },
        ) from e

    except HTTPException:
        # Re-raise HTTPException without modification
        raise

    except ClassificationError as e:
        # Pipeline classification errors (500-level)
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.exception(
            "classify_request_failed",
            latency_ms=elapsed_ms,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "CLASSIFICATION_ERROR",
                "message": "Classification failed due to internal error",
                "suggestion": "Please try again later or contact support",
            },
        ) from e

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Unexpected errors (500)
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.exception(
            "classify_request_failed",
            latency_ms=elapsed_ms,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Internal server error occurred",
                "suggestion": "Please try again later or contact support",
            },
        ) from e
