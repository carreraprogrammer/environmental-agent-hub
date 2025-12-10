"""
Discrepancy tracking service for Fast Path vs Full Pipeline comparison.

Tracks classification discrepancies between Fast Path (Roboflow) and
Full Pipeline (Gemini/GPT-4o) to build datasets for model retraining.

Flow:
1. Fast Path returns "PLASTIC" (0.85)
2. Full Pipeline validates with "METAL" (0.92)
3. DiscrepancyTracker detects mismatch
4. Sends correction to Backend API
5. Backend stores for retraining workflow

Key Design Decisions:
- Fire-and-forget: Backend failures are logged but don't block flow
- No retries: Simplicity over complexity for MVP
- Gemini/GPT = Ground Truth: We assume advanced models are correct
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.schemas.classification import Material
from app.schemas.discrepancy import CorrectionPayload, DiscrepancyRecord


class DiscrepancyTracker:
    """
    Service for tracking discrepancies between Fast Path and Full Pipeline.

    Responsibilities:
    1. Detect when Fast Path (Roboflow) differs from Ground Truth (Gemini/GPT)
    2. Create structured record of the discrepancy
    3. Send correction to backend for persistence
    4. Log metrics for observability

    Attributes:
        backend_url: Base URL for Backend Rails API
        corrections_endpoint: Full URL for corrections endpoint
        _client: HTTP client for backend communication (lazy initialized)
    """

    def __init__(self, backend_url: Optional[str] = None) -> None:
        """
        Initialize DiscrepancyTracker.

        Args:
            backend_url: Backend API base URL (defaults to settings.BACKEND_API_URL)
        """
        self.backend_url = backend_url or settings.BACKEND_API_URL
        self.corrections_endpoint = (
            f"{self.backend_url}/classification_corrections"
        )
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            "discrepancy_tracker_initialized",
            component="DiscrepancyTracker",
            corrections_endpoint=self.corrections_endpoint,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for backend communication.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    def has_discrepancy(
        self,
        fast_path_material: Material,
        ground_truth_material: Material,
    ) -> bool:
        """
        Determine if there's a discrepancy between Fast Path and Ground Truth.

        Args:
            fast_path_material: Material classified by Roboflow
            ground_truth_material: Material from Gemini/GPT

        Returns:
            True if materials differ, False if they match
        """
        return fast_path_material != ground_truth_material

    def create_record(
        self,
        trace_id: str,
        fast_path_material: Material,
        fast_path_confidence: float,
        fast_path_model: str,
        ground_truth_material: Material,
        ground_truth_confidence: float,
        ground_truth_model: str,
        scan_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        station_id: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> DiscrepancyRecord:
        """
        Create structured record of discrepancy.

        Args:
            trace_id: Request trace identifier
            fast_path_material: Material from Roboflow
            fast_path_confidence: Roboflow confidence
            fast_path_model: Roboflow model identifier
            ground_truth_material: Material from Gemini/GPT
            ground_truth_confidence: Gemini/GPT confidence
            ground_truth_model: Gemini/GPT model identifier
            scan_id: Scan identifier (optional)
            tenant_id: Tenant identifier (optional)
            station_id: Station identifier (optional)
            image_url: S3 URL for retraining (optional)

        Returns:
            DiscrepancyRecord with all fields populated
        """
        return DiscrepancyRecord(
            trace_id=trace_id,
            scan_id=scan_id,
            tenant_id=tenant_id,
            station_id=station_id,
            fast_path_material=fast_path_material,
            fast_path_confidence=fast_path_confidence,
            fast_path_model=fast_path_model,
            ground_truth_material=ground_truth_material,
            ground_truth_confidence=ground_truth_confidence,
            ground_truth_model=ground_truth_model,
            image_url=image_url,
            timestamp=datetime.utcnow(),
            confidence_delta=ground_truth_confidence - fast_path_confidence,
        )

    async def send_correction_to_backend(
        self,
        record: DiscrepancyRecord,
    ) -> bool:
        """
        Send correction to Backend Rails API for persistence.

        This is a fire-and-forget operation: failures are logged but
        don't block the main flow. No retries for simplicity.

        Args:
            record: DiscrepancyRecord to send

        Returns:
            True if sent successfully, False if failed
        """
        payload = CorrectionPayload(
            trace_id=record.trace_id,
            scan_id=record.scan_id,
            tenant_id=record.tenant_id,
            station_id=record.station_id,
            incorrect_material=record.fast_path_material.value,
            incorrect_confidence=record.fast_path_confidence,
            incorrect_model=record.fast_path_model,
            correct_material=record.ground_truth_material.value,
            correct_confidence=record.ground_truth_confidence,
            correct_model=record.ground_truth_model,
            image_url=record.image_url,
            timestamp=record.timestamp,
        )

        try:
            client = await self._get_client()
            response = await client.post(
                self.corrections_endpoint,
                json=payload.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in (200, 201):
                logger.info(
                    "correction_sent_to_backend",
                    trace_id=record.trace_id,
                    incorrect=record.fast_path_material.value,
                    correct=record.ground_truth_material.value,
                    endpoint=self.corrections_endpoint,
                )
                return True
            else:
                logger.warning(
                    "backend_rejected_correction",
                    trace_id=record.trace_id,
                    status_code=response.status_code,
                    response_preview=response.text[:200],
                )
                return False

        except httpx.TimeoutException:
            logger.warning(
                "backend_correction_timeout",
                trace_id=record.trace_id,
                endpoint=self.corrections_endpoint,
            )
            return False
        except Exception as e:
            logger.error(
                "backend_correction_error",
                trace_id=record.trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def track(
        self,
        trace_id: str,
        fast_path_material: Material,
        fast_path_confidence: float,
        fast_path_model: str,
        ground_truth_material: Material,
        ground_truth_confidence: float,
        ground_truth_model: str,
        scan_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        station_id: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Optional[DiscrepancyRecord]:
        """
        Main method: detect discrepancy and send correction if applicable.

        This is the primary public method that orchestrates the full flow:
        1. Check if materials differ
        2. If not, log agreement and return None
        3. If yes, create record, log discrepancy, send to backend

        Args:
            trace_id: Request trace identifier
            fast_path_material: Material from Roboflow
            fast_path_confidence: Roboflow confidence
            fast_path_model: Roboflow model identifier
            ground_truth_material: Material from Gemini/GPT
            ground_truth_confidence: Gemini/GPT confidence
            ground_truth_model: Gemini/GPT model identifier
            scan_id: Scan identifier (optional)
            tenant_id: Tenant identifier (optional)
            station_id: Station identifier (optional)
            image_url: S3 URL for retraining (optional)

        Returns:
            DiscrepancyRecord if discrepancy detected, None if materials match
        """
        # 1. Check for discrepancy
        if not self.has_discrepancy(fast_path_material, ground_truth_material):
            logger.debug(
                "classification_agreement",
                trace_id=trace_id,
                material=fast_path_material.value,
                fast_path_confidence=fast_path_confidence,
                ground_truth_confidence=ground_truth_confidence,
            )
            return None

        # 2. Create record
        record = self.create_record(
            trace_id=trace_id,
            fast_path_material=fast_path_material,
            fast_path_confidence=fast_path_confidence,
            fast_path_model=fast_path_model,
            ground_truth_material=ground_truth_material,
            ground_truth_confidence=ground_truth_confidence,
            ground_truth_model=ground_truth_model,
            scan_id=scan_id,
            tenant_id=tenant_id,
            station_id=station_id,
            image_url=image_url,
        )

        # 3. Log discrepancy (always, for metrics/monitoring)
        logger.warning(
            "classification_discrepancy_detected",
            trace_id=trace_id,
            fast_path_material=fast_path_material.value,
            fast_path_confidence=fast_path_confidence,
            ground_truth_material=ground_truth_material.value,
            ground_truth_confidence=ground_truth_confidence,
            confidence_delta=record.confidence_delta,
            scan_id=scan_id,
        )

        # 4. Send to backend (fire-and-forget)
        await self.send_correction_to_backend(record)

        return record

    async def close(self) -> None:
        """
        Close HTTP client and cleanup resources.

        Call this when shutting down the application or when
        the tracker is no longer needed.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("discrepancy_tracker_closed", component="DiscrepancyTracker")
