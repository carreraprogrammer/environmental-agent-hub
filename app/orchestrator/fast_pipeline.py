"""
Fast Pipeline - Background validation and synchronization.

After fast response is sent to user, this pipeline validates the classification
with a high-precision model (Gemini/GPT-4o) and synchronizes complete data
with the Rails backend.

Flow:
1. User receives fast response (Roboflow)
2. Background: Full classification (Gemini/GPT-4o)
3. Compare results, flag mismatches
4. Calculate complete metadata (waste_type, volume, weight)
5. Sync with Rails backend

Performance:
- Runs asynchronously (non-blocking)
- Validates 100% of fast responses
- Tracks accuracy metrics
- Enables model improvement
"""

from __future__ import annotations

import time
from typing import Any

from app.core.logging import logger
from app.orchestrator.pipeline import Pipeline
from app.schemas.classification import Material
from app.schemas.requests import ClassifyRequestForm
from app.schemas.responses import ClassifyResponse
from app.services.discrepancy_tracker import DiscrepancyTracker


class ValidationPipeline:
    """
    Background pipeline for validating fast responses and syncing with backend.
    
    Responsibilities:
    1. Run full classification with high-precision model
    2. Compare with fast response
    3. Calculate complete metadata
    4. Sync with Rails backend
    5. Log discrepancies for monitoring
    """

    def __init__(self, main_pipeline: Pipeline) -> None:
        """
        Initialize validation pipeline.

        Args:
            main_pipeline: Main classification pipeline (Gemini/GPT-4o)
        """
        self.main_pipeline = main_pipeline
        self.discrepancy_tracker = DiscrepancyTracker()

        logger.info(
            "validation_pipeline_initialized",
            component="ValidationPipeline",
        )

    async def validate_and_sync(
        self,
        request: ClassifyRequestForm,
        fast_result: dict[str, Any],
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Validate fast response with full pipeline and sync to backend.
        
        Args:
            request: Original classification request
            fast_result: Result from FastClassifier
            trace_id: Request trace ID
            
        Returns:
            Validation result with comparison metrics
        """
        start_time = time.time()
        
        logger.info(
            "validation_pipeline_started",
            trace_id=trace_id,
            component="ValidationPipeline",
            fast_material=fast_result["material"].value,
            fast_confidence=fast_result["confidence"],
        )
        
        try:
            # 1. Run full classification pipeline
            full_response = await self.main_pipeline.process(request)

            # 2. Track discrepancy (sends to backend if materials differ)
            await self.discrepancy_tracker.track(
                trace_id=trace_id,
                fast_path_material=fast_result["material"],
                fast_path_confidence=fast_result["confidence"],
                fast_path_model="roboflow/waste-classifier-louut-b9sot",
                ground_truth_material=full_response.material,
                ground_truth_confidence=full_response.confidence,
                ground_truth_model=full_response.meta.model_used,
                scan_id=str(request.scan_id) if request.scan_id else None,
                tenant_id=request.tenant_id,
                station_id=request.station_id,
                image_url=None,  # TODO: Add S3 URL when available
            )

            # 3. Compare results
            comparison = self._compare_results(fast_result, full_response)

            # 4. Log if mismatch (legacy logging - kept for backward compatibility)
            if not comparison["agreement"]:
                logger.warning(
                    "classification_mismatch_detected",
                    trace_id=trace_id,
                    fast_material=fast_result["material"].value,
                    validated_material=full_response.material.value,
                    fast_confidence=fast_result["confidence"],
                    validated_confidence=full_response.confidence,
                    confidence_diff=comparison["confidence_diff"],
                )

            # 5. Update response metadata with validation info
            full_response.meta.fast_response_material = fast_result["material"].value
            full_response.meta.validation_agreement = comparison["agreement"]
            full_response.meta.confidence_diff = comparison["confidence_diff"]
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "validation_pipeline_complete",
                trace_id=trace_id,
                component="ValidationPipeline",
                agreement=comparison["agreement"],
                latency_ms=latency_ms,
            )
            
            return {
                "validation_result": full_response,
                "comparison": comparison,
                "latency_ms": latency_ms,
            }
            
        except Exception as e:
            logger.error(
                "validation_pipeline_failed",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            
            # Even if validation fails, fast response was already sent
            return {
                "validation_result": None,
                "comparison": None,
                "error": str(e),
            }

    def _compare_results(
        self,
        fast_result: dict[str, Any],
        full_response: ClassifyResponse,
    ) -> dict[str, Any]:
        """
        Compare fast and validated classification results.
        
        Args:
            fast_result: Fast classification result
            full_response: Full pipeline response
            
        Returns:
            Comparison metrics
        """
        fast_material = fast_result["material"]
        validated_material = full_response.material
        
        agreement = fast_material == validated_material
        confidence_diff = abs(
            fast_result["confidence"] - full_response.confidence
        )
        
        return {
            "agreement": agreement,
            "fast_material": fast_material.value,
            "validated_material": validated_material.value,
            "fast_confidence": fast_result["confidence"],
            "validated_confidence": full_response.confidence,
            "confidence_diff": round(confidence_diff, 3),
        }
