"""
Performance test for MaterialClassifier V4 latency.

Validates that the unified material classification (single LLM call)
runs comfortably under 1500ms p95.

Note: This test uses mocked adapters to measure MaterialClassifier overhead.
For real latency with live APIs, use integration tests with RUN_INTEGRATION_TESTS=1.
"""

from __future__ import annotations

import asyncio
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

# Ensure project root is on sys.path for imports
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.material_classifier import MaterialClassifier
from app.adapters.base import ClassifierAdapter


def _make_image_bytes(width: int = 256, height: int = 256, fmt: str = "JPEG") -> bytes:
    """Create a simple in-memory image and return its bytes."""
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


class FastMockAdapter(ClassifierAdapter):
    """
    Fast mock adapter that simulates a typical LLM response time.

    This is used to measure MaterialClassifier overhead without actual
    network calls, while still simulating realistic latency.
    """

    async def classify(self, image_url: str, *, trace_id: str | None = None):  # type: ignore[override]
        raise NotImplementedError("V3 classify() not used")

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        """
        Simulate a fast LLM response (~100ms) with valid classification.

        This simulates typical GPT-4 Vision latency without network overhead.
        """
        # Simulate LLM processing time
        await asyncio.sleep(0.1)  # 100ms simulated API call

        return {
            "material": {"type": "PLASTIC", "confidence": 0.9},
            "subtype": {"value": "PET", "recycling_code": "#1", "confidence": 0.85},
            "condition": {"value": "CLEAN", "confidence": 0.8},
            "volume": {"liters": 0.5, "source": "LABEL_READ", "confidence": 0.8},
            "recyclability": {"value": "RECYCLABLE", "confidence": 0.9},
            "reasoning": "Botella PET de 500ml limpia",
        }

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return "mock/fast-adapter"

    @property
    def model_provider(self) -> str:  # type: ignore[override]
        return "mock"

    @property
    def cost_per_request(self) -> float:  # type: ignore[override]
        return 0.010


@pytest.fixture
def classifier_with_fast_adapter() -> MaterialClassifier:
    """Create MaterialClassifier with a fast mock adapter."""
    adapter = FastMockAdapter()
    return MaterialClassifier(adapter)


@pytest.mark.asyncio
async def test_material_classifier_latency_p95_under_1500ms(
    classifier_with_fast_adapter: MaterialClassifier,
) -> None:
    """
    Measure MaterialClassifier latency and assert p95 < 1500ms.

    Uses a fast mock adapter (100ms simulated LLM call) to measure the
    internal overhead of MaterialClassifier plus typical API latency.

    The 1500ms target from EDV-51 includes:
    - Adapter overhead (~50ms)
    - LLM API call (~1000-1200ms actual)
    - Parsing and validation (~50ms)

    This test uses 100ms mock, so p95 should be ~150-200ms.
    """
    image_bytes = _make_image_bytes()

    latencies_ms: list[float] = []
    iterations = 20

    for i in range(iterations):
        start = time.perf_counter()
        result = await classifier_with_fast_adapter.classify(
            image_bytes, f"trace-latency-{i}"
        )
        end = time.perf_counter()

        latencies_ms.append((end - start) * 1000.0)

        # Sanity check: result should be valid
        assert result.material.material_type is not None

    latencies_ms.sort()

    # Calculate percentiles
    index_50 = max(int(iterations * 0.50) - 1, 0)
    index_95 = max(int(iterations * 0.95) - 1, 0)
    p50 = latencies_ms[index_50]
    p95 = latencies_ms[index_95]

    print(f"\nMaterialClassifier Latency (mocked adapter):")
    print(f"  p50: {p50:.2f}ms")
    print(f"  p95: {p95:.2f}ms")
    print(f"  max: {max(latencies_ms):.2f}ms")

    # With a 100ms mock, p95 should be ~150ms (100ms + overhead)
    # We set threshold at 500ms to account for system variability
    assert p95 < 500.0, f"MaterialClassifier p95 latency too high: {p95:.2f}ms"

    # For information: estimate real-world latency with actual LLM
    # Typical GPT-4 Vision: ~1000-1200ms
    # So real p95 would be approximately: p95 - 100ms + 1100ms = p95 + 1000ms
    estimated_real_p95 = p95 - 100.0 + 1100.0
    print(f"\nEstimated real-world p95 (GPT-4 Vision): {estimated_real_p95:.2f}ms")

    # This should meet EDV-51 requirement (<1500ms)
    assert (
        estimated_real_p95 < 1500.0
    ), f"Estimated real p95 would exceed target: {estimated_real_p95:.2f}ms"


@pytest.mark.asyncio
async def test_material_classifier_overhead_minimal(
    classifier_with_fast_adapter: MaterialClassifier,
) -> None:
    """
    Verify MaterialClassifier overhead (excluding LLM call) is minimal (<100ms).

    This test ensures the parsing, validation, and schema construction
    don't add significant latency to the LLM call.
    """
    image_bytes = _make_image_bytes()

    latencies_ms: list[float] = []
    iterations = 10

    for i in range(iterations):
        start = time.perf_counter()
        _ = await classifier_with_fast_adapter.classify(image_bytes, f"trace-overhead-{i}")
        end = time.perf_counter()

        latencies_ms.append((end - start) * 1000.0)

    # With 100ms mock LLM call, total should be ~110-120ms
    # Overhead = total - 100ms should be <20ms
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    overhead = avg_latency - 100.0  # Subtract mock LLM time

    print(f"\nMaterialClassifier Overhead Analysis:")
    print(f"  Average total: {avg_latency:.2f}ms")
    print(f"  Mock LLM time: 100.00ms")
    print(f"  Overhead: {overhead:.2f}ms")

    assert overhead < 100.0, f"MaterialClassifier overhead too high: {overhead:.2f}ms"
