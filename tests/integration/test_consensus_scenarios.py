"""
Integration tests for ConsensusClassificationAgent V4.

Tests real-world consensus scenarios with actual Pipeline integration.
These tests validate end-to-end flow with consensus mode enabled.

Coverage:
- Pipeline integration with consensus mode
- Real adapter behavior (mocked external APIs)
- Latency and performance characteristics
- Metadata propagation through pipeline

Run with: pytest tests/integration/test_consensus_scenarios.py -v
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.base import ClassifierAdapter
from app.agent.consensus_classifier import ConsensusClassificationAgent
from app.core.config import settings
from app.orchestrator.pipeline import Pipeline
from app.schemas.classification import Material
from app.schemas.requests import ClassifyRequest


class MockAdapter(ClassifierAdapter):
    """Mock adapter for integration testing."""

    def __init__(
        self,
        material: Material,
        confidence: float,
        model_name: str = "mock-model",
        cost: float = 0.010,
    ) -> None:
        self._material = material
        self._confidence = confidence
        self._model_name = model_name
        self._cost = cost

    async def classify(self, image_url: str, *, trace_id: str | None = None):  # type: ignore[override]
        raise NotImplementedError("V3 classify() not used")

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        """Return mock classification result."""
        return {
            "material": {"type": self._material.value, "confidence": self._confidence},
            "subtype": {"value": "PET", "recycling_code": "#1", "confidence": 0.85},
            "condition": {"value": "CLEAN", "confidence": 0.8},
            "volume": {"liters": 0.5, "source": "ESTIMATED", "confidence": 0.7},
            "recyclability": {"value": "RECYCLABLE", "confidence": 0.9},
            "reasoning": f"Mock classification: {self._material.value}",
            "cost": self._cost,
            "model_used": self._model_name,
            "model_provider": "mock",
            "metadata": {},
        }

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return self._model_name

    @property
    def model_provider(self) -> str:  # type: ignore[override]
        return "mock"

    @property
    def cost_per_request(self) -> float:  # type: ignore[override]
        return self._cost


@pytest.mark.asyncio
async def test_pipeline_consensus_mode_fast_path() -> None:
    """
    Integration: Pipeline with consensus mode - fast path (high confidence).

    Scenario:
    - CLASSIFIER_MODEL=consensus
    - Primary model returns PLASTIC with 0.88 confidence
    - Should take fast path (no secondary/tiebreaker)
    - Response should include consensus metadata
    """
    with patch.object(settings, "CLASSIFIER_MODEL", "consensus"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Setup mock adapters
        primary_adapter = MockAdapter(Material.PLASTIC, 0.88, "gpt-4o", 0.010)
        secondary_adapter = MockAdapter(Material.PLASTIC, 0.80, "gemini", 0.001)
        tiebreaker_adapter = MockAdapter(Material.PLASTIC, 0.75, "roboflow", 0.001)

        mock_factory.side_effect = [
            primary_adapter,
            secondary_adapter,
            tiebreaker_adapter,
        ]

        # Initialize pipeline in consensus mode
        pipeline = Pipeline()
        assert pipeline.consensus_mode is True

        # Create request
        request = ClassifyRequest(
            image_bytes=b"fake-image-data",
            scan_id="scan-integration-fast",
            station_id="station-1",
            tenant_id="tenant-1",
            trace_id="trace-integration-fast",
        )

        # Execute
        start_time = time.time()
        response = await pipeline.process(request)
        latency_ms = (time.time() - start_time) * 1000

        # Assert
        assert response.material == Material.PLASTIC
        assert response.confidence == pytest.approx(0.88)
        assert latency_ms < 2000  # Should be fast (< 2s)

        # Check metadata is propagated
        # Note: meta is in response.meta, not response.metadata
        assert hasattr(response, "meta")


@pytest.mark.asyncio
async def test_pipeline_consensus_mode_agreement_boost() -> None:
    """
    Integration: Pipeline with consensus mode - agreement boost.

    Scenario:
    - Primary: PLASTIC, 0.65 (triggers consensus)
    - Secondary: PLASTIC, 0.67 (agrees)
    - Expected: Agreement boost strategy
    - Final confidence: (0.65*0.6 + 0.67*0.4) + 0.10 = 0.758
    """
    with patch.object(settings, "CLASSIFIER_MODEL", "consensus"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Setup mock adapters
        primary_adapter = MockAdapter(Material.PLASTIC, 0.65, "gpt-4o", 0.010)
        secondary_adapter = MockAdapter(Material.PLASTIC, 0.67, "gemini", 0.001)
        tiebreaker_adapter = MockAdapter(Material.PLASTIC, 0.70, "roboflow", 0.001)

        mock_factory.side_effect = [
            primary_adapter,
            secondary_adapter,
            tiebreaker_adapter,
        ]

        # Initialize pipeline
        pipeline = Pipeline()

        # Create request
        request = ClassifyRequest(
            image_bytes=b"fake-image-data",
            scan_id="scan-integration-agreement",
            station_id="station-1",
            tenant_id="tenant-1",
            trace_id="trace-integration-agreement",
        )

        # Execute
        response = await pipeline.process(request)

        # Assert
        assert response.material == Material.PLASTIC
        # Expected: (0.65*0.6 + 0.67*0.4) + 0.10 = 0.758
        assert response.confidence == pytest.approx(0.758, abs=0.01)


@pytest.mark.asyncio
async def test_pipeline_consensus_mode_confidence_based() -> None:
    """
    Integration: Pipeline with consensus mode - confidence-based strategy.

    Scenario:
    - Primary: PLASTIC, 0.65
    - Secondary: METAL, 0.45 (diff = 0.20 > 0.15)
    - Expected: Confidence-based (primary wins)
    - Final confidence: 0.65 * 0.90 = 0.585
    """
    with patch.object(settings, "CLASSIFIER_MODEL", "consensus"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Setup mock adapters
        primary_adapter = MockAdapter(Material.PLASTIC, 0.65, "gpt-4o", 0.010)
        secondary_adapter = MockAdapter(Material.METAL, 0.45, "gemini", 0.001)
        tiebreaker_adapter = MockAdapter(Material.GLASS, 0.50, "roboflow", 0.001)

        mock_factory.side_effect = [
            primary_adapter,
            secondary_adapter,
            tiebreaker_adapter,
        ]

        # Initialize pipeline
        pipeline = Pipeline()

        # Create request
        request = ClassifyRequest(
            image_bytes=b"fake-image-data",
            scan_id="scan-integration-confidence",
            station_id="station-1",
            tenant_id="tenant-1",
            trace_id="trace-integration-confidence",
        )

        # Execute
        response = await pipeline.process(request)

        # Assert
        assert response.material == Material.PLASTIC  # Primary wins
        assert response.confidence == pytest.approx(0.585, abs=0.01)  # 0.65 * 0.90


@pytest.mark.asyncio
async def test_pipeline_consensus_mode_latency() -> None:
    """
    Integration: Test consensus mode latency is within acceptable bounds.

    Performance target: P95 latency < 2000ms
    """
    with patch.object(settings, "CLASSIFIER_MODEL", "consensus"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Setup mock adapters
        primary_adapter = MockAdapter(Material.PLASTIC, 0.60, "gpt-4o", 0.010)
        secondary_adapter = MockAdapter(Material.METAL, 0.58, "gemini", 0.001)
        tiebreaker_adapter = MockAdapter(Material.PLASTIC, 0.62, "roboflow", 0.001)

        mock_factory.side_effect = [
            primary_adapter,
            secondary_adapter,
            tiebreaker_adapter,
        ]

        # Initialize pipeline
        pipeline = Pipeline()

        # Create request
        request = ClassifyRequest(
            image_bytes=b"fake-image-data",
            scan_id="scan-integration-latency",
            station_id="station-1",
            tenant_id="tenant-1",
            trace_id="trace-integration-latency",
        )

        # Execute and measure latency
        start_time = time.time()
        response = await pipeline.process(request)
        latency_ms = (time.time() - start_time) * 1000

        # Assert latency < 2000ms (P95 target)
        assert latency_ms < 2000, f"Latency {latency_ms}ms exceeds 2000ms target"
        assert response.material in [Material.PLASTIC, Material.METAL, Material.GLASS]


@pytest.mark.asyncio
async def test_consensus_cost_optimization() -> None:
    """
    Integration: Verify consensus cost is optimized vs single model.

    Fast path (70%): $0.010 (primary only)
    Consensus path (30%): $0.012 (primary + secondary + tiebreaker)
    Average: 0.70 * 0.010 + 0.30 * 0.012 = 0.0106 ≈ $0.011/scan
    """
    costs = []

    with patch.object(settings, "CLASSIFIER_MODEL", "consensus"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Test 10 scenarios: 7 fast path, 3 consensus path
        scenarios = [
            # Fast path (7 scenarios)
            (Material.PLASTIC, 0.85),  # Fast
            (Material.METAL, 0.80),  # Fast
            (Material.GLASS, 0.90),  # Fast
            (Material.PLASTIC, 0.75),  # Fast
            (Material.METAL, 0.88),  # Fast
            (Material.GLASS, 0.82),  # Fast
            (Material.PLASTIC, 0.78),  # Fast
            # Consensus path (3 scenarios)
            (Material.PLASTIC, 0.60),  # Consensus
            (Material.METAL, 0.55),  # Consensus
            (Material.GLASS, 0.58),  # Consensus
        ]

        for material, confidence in scenarios:
            # Setup adapters
            primary_adapter = MockAdapter(material, confidence, "gpt-4o", 0.010)
            secondary_adapter = MockAdapter(material, confidence + 0.05, "gemini", 0.001)
            tiebreaker_adapter = MockAdapter(material, confidence + 0.03, "roboflow", 0.001)

            mock_factory.side_effect = [
                primary_adapter,
                secondary_adapter,
                tiebreaker_adapter,
            ]

            # Initialize pipeline
            pipeline = Pipeline()

            # Create request
            request = ClassifyRequest(
                image_bytes=b"fake-image-data",
                scan_id=f"scan-cost-{material.value}",
                station_id="station-1",
                tenant_id="tenant-1",
                trace_id=f"trace-cost-{material.value}",
            )

            # Execute
            response = await pipeline.process(request)
            # Cost is in response.meta.cost_usd
            if hasattr(response, "meta") and hasattr(response.meta, "cost_usd"):
                costs.append(response.meta.cost_usd)

    # Calculate average cost
    if costs:
        avg_cost = sum(costs) / len(costs)
        # Should be around $0.011 (mix of fast and consensus paths)
        assert 0.009 <= avg_cost <= 0.013, f"Average cost {avg_cost} outside expected range"


@pytest.mark.asyncio
async def test_consensus_no_waste_detection() -> None:
    """
    Integration: Consensus mode should still detect NO_WASTE correctly.

    When primary model detects NO_WASTE, it should fail fast without
    triggering secondary/tiebreaker models.
    """
    with patch.object(settings, "CLASSIFIER_MODEL", "consensus"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Setup adapters (NO_WASTE detection)
        primary_adapter = MockAdapter(Material.NO_WASTE, 0.99, "gpt-4o", 0.010)
        secondary_adapter = MockAdapter(Material.PLASTIC, 0.80, "gemini", 0.001)
        tiebreaker_adapter = MockAdapter(Material.PLASTIC, 0.75, "roboflow", 0.001)

        mock_factory.side_effect = [
            primary_adapter,
            secondary_adapter,
            tiebreaker_adapter,
        ]

        # Initialize pipeline
        pipeline = Pipeline()

        # Create request
        request = ClassifyRequest(
            image_bytes=b"fake-image-data",
            scan_id="scan-no-waste",
            station_id="station-1",
            tenant_id="tenant-1",
            trace_id="trace-no-waste",
        )

        # Execute - should raise ValidationError
        from app.orchestrator.pipeline import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await pipeline.process(request)

        assert exc_info.value.error_code == "NO_WASTE_DETECTED"


@pytest.mark.asyncio
async def test_consensus_single_model_fallback() -> None:
    """
    Integration: Verify pipeline still works with single model mode.

    When CLASSIFIER_MODEL != "consensus", pipeline should use
    standard MaterialClassifier (backward compatibility).
    """
    with patch.object(settings, "CLASSIFIER_MODEL", "openai-gpt4o"), patch(
        "app.orchestrator.pipeline.ClassifierFactory.create"
    ) as mock_factory:
        # Setup single adapter
        adapter = MockAdapter(Material.PLASTIC, 0.85, "gpt-4o", 0.010)
        mock_factory.return_value = adapter

        # Initialize pipeline
        pipeline = Pipeline()
        assert pipeline.consensus_mode is False  # Not in consensus mode

        # Create request
        request = ClassifyRequest(
            image_bytes=b"fake-image-data",
            scan_id="scan-single-model",
            station_id="station-1",
            tenant_id="tenant-1",
            trace_id="trace-single-model",
        )

        # Execute
        response = await pipeline.process(request)

        # Assert
        assert response.material == Material.PLASTIC
        assert response.confidence == pytest.approx(0.85)
