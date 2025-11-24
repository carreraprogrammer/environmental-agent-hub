"""
Performance tests for Pipeline Orchestrator V4.

Tests latency and cost targets:
- Latency: <1000ms (p95), <600ms (p50)
- Cost: $0.010 per request
- Individual agent latencies within bounds

Note: PreValidator moved to client-side (6 backend agents).

These tests use mocks to avoid actual API calls and focus on
orchestration performance.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.orchestrator.pipeline import Pipeline
from app.schemas.classification import (
    ConditionField,
    Material,
    MaterialClassificationResult,
    MaterialField,
    PhysicalCondition,
    Recyclability,
    RecyclabilityField,
    SubtypeField,
    VolumeField,
    VolumeSource,
)
from app.schemas.requests import ClassifyRequestForm


@pytest.fixture
def mock_request() -> ClassifyRequestForm:
    """Create a mock classification request."""
    return ClassifyRequestForm(
        scan_id=uuid4(),
        station_id="PERF-TEST-01",
        image_bytes=b"performance_test_image_data" * 1000,  # ~27KB
        tenant_id="perf-tenant",
        trace_id=uuid4(),
        idempotency_key=uuid4(),
    )


@pytest.fixture
def mock_classification_result() -> MaterialClassificationResult:
    """Create a fast mock classification result."""
    return MaterialClassificationResult(
        material=MaterialField(material_type=Material.PLASTIC, confidence=0.91),
        subtype=SubtypeField(value="PET", recycling_code="#1", confidence=0.88),
        condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.90),
        volume=VolumeField(liters=0.5, source=VolumeSource.LABEL_READ, confidence=0.85),
        recyclability=RecyclabilityField(value=Recyclability.RECYCLABLE, confidence=0.92),
        reasoning="PET bottle 500ml",
        timestamp=datetime.now(),
        cost=0.010,
        model_used="gpt-4o",
        model_provider="openai",
        partial_success=False,
        metadata={},
    )


class TestPipelineLatency:
    """Test pipeline latency performance."""

    @pytest.mark.asyncio
    async def test_total_latency_within_target(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test total pipeline latency is <1000ms (p95 target)."""
        pipeline = Pipeline()

        # Create fast mock agents (no PreValidator - client-side validation)
        async def fast_classify(*args: Any, **kwargs: Any) -> MaterialClassificationResult:
            await asyncio.sleep(0.02)  # 20ms
            return mock_classification_result

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.side_effect = fast_classify

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                start = time.time()
                response = await pipeline.process(mock_request)
                elapsed_ms = (time.time() - start) * 1000

                # Verify latency target (p95 < 1000ms)
                assert elapsed_ms < 1000, f"Latency {elapsed_ms}ms exceeds 1000ms target"

                # Verify response includes latency
                assert response.meta.latency_ms >= 0
                assert response.meta.latency_ms < 1000

    @pytest.mark.asyncio
    async def test_p50_latency_within_target(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test p50 latency is <600ms."""
        pipeline = Pipeline()

        async def fast_classify(*args: Any, **kwargs: Any) -> MaterialClassificationResult:
            await asyncio.sleep(0.01)  # 10ms
            return mock_classification_result

        latencies = []

        for _ in range(10):  # Run 10 times to get p50
            with patch.object(
                pipeline.classifier, "classify", new_callable=AsyncMock
            ) as mock_classify:
                mock_classify.side_effect = fast_classify

                with patch.object(
                    pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
                ):
                    start = time.time()
                    await pipeline.process(mock_request)
                    elapsed_ms = (time.time() - start) * 1000
                    latencies.append(elapsed_ms)

        # Calculate p50
        latencies.sort()
        p50 = latencies[len(latencies) // 2]

        assert p50 < 600, f"P50 latency {p50}ms exceeds 600ms target"

    @pytest.mark.asyncio
    async def test_cost_within_target(self):
        """Test pipeline cost is $0.010 per request (MaterialClassifier only)."""
        pipeline = Pipeline()

        cost = pipeline._calculate_total_cost()

        # V4 cost: $0.010 (MaterialClassifier only, PreValidator moved to client-side)
        assert cost == pytest.approx(0.010, rel=0.01), f"Cost ${cost} not equal to $0.010"
        assert cost < 0.012, f"Cost ${cost} exceeds reasonable bounds"

        # Document current cost
        print(f"\nCurrent V4 cost: ${cost}")
        print(f"Target cost: $0.008")
        print(f"Difference: ${cost - 0.008}")

    @pytest.mark.asyncio
    async def test_agent_latency_breakdown(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test individual agent latencies are within bounds."""
        pipeline = Pipeline()

        # Track agent timings
        timings: dict[str, float] = {}

        # Mock MaterialClassifier with timing
        async def timed_classify(*args: Any, **kwargs: Any) -> MaterialClassificationResult:
            start = time.time()
            await asyncio.sleep(0.02)  # 20ms (fast mock)
            timings["MaterialClassifier"] = (time.time() - start) * 1000
            return mock_classification_result

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.side_effect = timed_classify

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                await pipeline.process(mock_request)

                # Verify MaterialClassifier latency (primary AI agent)
                # Note: This is mocked fast time
                assert (
                    timings["MaterialClassifier"] < 500
                ), f"MaterialClassifier {timings['MaterialClassifier']}ms exceeds 500ms"

                # Print timing breakdown
                print("\n=== Agent Latency Breakdown (Mocked) ===")
                for agent, latency in timings.items():
                    print(f"{agent}: {latency:.2f}ms")

    @pytest.mark.asyncio
    async def test_agents_executed_count(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test that all 5 processing agents are executed."""
        pipeline = Pipeline()

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                response = await pipeline.process(mock_request)

                # V4 should execute exactly 5 processing agents
                # (Assembler not included in agents_executed list)
                assert (
                    len(response.meta.agents_executed) == 5
                ), f"Expected 5 agents, got {len(response.meta.agents_executed)}"

                # Verify specific agents (PreValidator moved to client-side)
                expected_agents = [
                    "MaterialClassifier",
                    "VolumeEstimator",
                    "Mapper",
                    "WasteTypeMapper",
                    "FeedbackCoach",
                ]

                for agent in expected_agents:
                    assert (
                        agent in response.meta.agents_executed
                    ), f"Agent {agent} not executed"

    @pytest.mark.asyncio
    async def test_memory_usage(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test pipeline memory usage is reasonable."""
        import sys

        pipeline = Pipeline()

        # Get pipeline size
        pipeline_size = sys.getsizeof(pipeline)

        # Should be reasonable (< 10KB for the object itself)
        assert pipeline_size < 10_000, f"Pipeline object too large: {pipeline_size} bytes"

        # Process a request
        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                response = await pipeline.process(mock_request)

                # Response size should be reasonable (< 50KB)
                response_size = sys.getsizeof(response)
                assert (
                    response_size < 50_000
                ), f"Response too large: {response_size} bytes"

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test pipeline handles concurrent requests efficiently."""
        pipeline = Pipeline()

        async def fast_classify(*args: Any, **kwargs: Any) -> MaterialClassificationResult:
            await asyncio.sleep(0.02)
            return mock_classification_result

        # Patch at the class level, outside the loop
        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.side_effect = fast_classify

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                # Process 5 concurrent requests
                tasks = []
                start = time.time()

                for i in range(5):
                    # Create unique request for each
                    request = ClassifyRequestForm(
                        scan_id=uuid4(),
                        station_id=f"PERF-{i}",
                        image_bytes=b"test_image",
                        tenant_id="perf-tenant",
                        trace_id=uuid4(),
                        idempotency_key=uuid4(),
                    )
                    task = asyncio.create_task(pipeline.process(request))
                    tasks.append(task)

                # Wait for all to complete
                responses = await asyncio.gather(*tasks)
                elapsed_ms = (time.time() - start) * 1000

                # All should complete
                assert len(responses) == 5

                # Total time should be less than 5x sequential (shows concurrency benefit)
                # With mocking, this should be very fast
                assert elapsed_ms < 500, f"Concurrent processing too slow: {elapsed_ms}ms"

    @pytest.mark.asyncio
    async def test_input_format_detection_performance(
        self,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test input format detection doesn't add significant overhead."""
        pipeline = Pipeline()

        # Test with bytes
        request_bytes = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="PERF-BYTES",
            image_bytes=b"test_image_bytes",
            tenant_id="perf-tenant",
            trace_id=uuid4(),
            idempotency_key=uuid4(),
        )

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                start = time.time()
                response = await pipeline.process(request_bytes)
                elapsed_ms = (time.time() - start) * 1000

                # Should be very fast (< 1000ms target)
                assert elapsed_ms < 1000

                # Should detect bytes format
                assert response.meta.input_format == "bytes"


class TestPipelineStressTest:
    """Stress tests for pipeline under load."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Slow stress test - run manually")
    async def test_rapid_sequential_requests(
        self,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test pipeline handles rapid sequential requests."""
        pipeline = Pipeline()

        successes = 0

        for i in range(20):
            request = ClassifyRequestForm(
                scan_id=uuid4(),
                station_id=f"STRESS-{i}",
                image_bytes=b"test_image",
                tenant_id="stress-tenant",
                trace_id=uuid4(),
                idempotency_key=uuid4(),
            )

            with patch.object(
                pipeline.classifier, "classify", new_callable=AsyncMock
            ) as mock_classify:
                mock_classify.return_value = mock_classification_result

                with patch.object(
                    pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
                ):
                    try:
                        await pipeline.process(request)
                        successes += 1
                    except Exception as e:
                        print(f"Request {i} failed: {e}")

        # At least 95% should succeed
        assert successes >= 19, f"Only {successes}/20 requests succeeded"
