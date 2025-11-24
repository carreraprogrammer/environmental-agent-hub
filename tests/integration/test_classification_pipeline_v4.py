"""
Integration tests for the unified MaterialClassifier V4 (detección + clasificación).

Verifica que el modelo:
- Detecta NO_WASTE en una sola llamada (sin PreValidator)
- Entrega clasificación completa cuando hay residuo
- Maneja partial success en campos opcionales
"""

from __future__ import annotations

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
from app.schemas.classification import Material, VolumeSource


pytestmark = pytest.mark.integration


def _make_image_bytes(width: int = 256, height: int = 256, fmt: str = "JPEG") -> bytes:
    """Create a simple in-memory image and return its bytes."""
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


class MockClassifierAdapter(ClassifierAdapter):
    """Mock adapter for MaterialClassifier testing."""

    async def classify(self, image_url: str, *, trace_id: str | None = None):  # type: ignore[override]
        raise NotImplementedError("V3 classify() not used")

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        """Return a valid classification response."""
        return {
            "material": {"type": "PLASTIC", "confidence": 0.92},
            "subtype": {"value": "PET", "recycling_code": "#1", "confidence": 0.88},
            "condition": {"value": "CLEAN", "confidence": 0.85},
            "volume": {"liters": 0.5, "source": "LABEL_READ", "confidence": 0.80},
            "recyclability": {"value": "RECYCLABLE", "confidence": 0.95},
            "reasoning": "Botella PET de 500ml en buenas condiciones",
        }

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return "mock/test-adapter"

    @property
    def model_provider(self) -> str:  # type: ignore[override]
        return "mock"

    @property
    def cost_per_request(self) -> float:  # type: ignore[override]
        return 0.010


@pytest.fixture
def classifier_with_mock_adapter():
    """MaterialClassifier with mock adapter."""
    adapter = MockClassifierAdapter()
    return MaterialClassifier(adapter)


@pytest.mark.asyncio
async def test_material_classifier_success(classifier_with_mock_adapter):
    """Clasificación completa con residuo válido."""
    image_bytes = _make_image_bytes()
    trace_id = "test-classifier-success"

    classification_result = await classifier_with_mock_adapter.classify(image_bytes, trace_id)

    assert classification_result.material.material_type == Material.PLASTIC
    assert classification_result.material.confidence >= 0.7
    assert classification_result.subtype.value == "PET"
    assert classification_result.volume.liters == 0.5
    assert classification_result.volume.source == VolumeSource.LABEL_READ
    assert classification_result.partial_success is False


@pytest.mark.asyncio
async def test_material_classifier_no_waste_detection():
    """El modelo puede devolver NO_WASTE en una sola llamada."""

    class NoWasteAdapter(MockClassifierAdapter):
        async def classify_material(self, image_data: bytes, *, trace_id: str | None = None) -> dict[str, Any]:
            return {
                "material": {"type": "NO_WASTE", "confidence": 0.95},
                "subtype": {"value": None, "recycling_code": None, "confidence": 0.0},
                "condition": {"value": "CLEAN", "confidence": 0.0},
                "volume": {"liters": None, "source": "ESTIMATED", "confidence": 0.0},
                "recyclability": {"value": "NON_RECYCLABLE", "confidence": 0.0},
                "reasoning": "No se detecta residuo en la imagen",
            }

    classifier = MaterialClassifier(NoWasteAdapter())
    image_bytes = _make_image_bytes()
    result = await classifier.classify(image_bytes, "trace-no-waste")

    assert result.material.material_type == Material.NO_WASTE
    assert result.material.confidence == pytest.approx(0.95, rel=0.01)
    assert result.volume.liters is None
    assert result.partial_success is False


@pytest.mark.asyncio
async def test_pipeline_with_partial_success(
    classifier_with_mock_adapter,
    monkeypatch,
):
    """
    Test classifier handles partial success in campos opcionales.

    When some fields have low confidence, pipeline should continue
    with partial data.
    """
    # Mock adapter to return low confidence for volume
    async def classify_material_partial(image_data: bytes, *, trace_id: str | None = None):
        return {
            "material": {"type": "GLASS", "confidence": 0.90},
            "subtype": {"value": None, "recycling_code": None, "confidence": 0.3},
            "condition": {"value": "CLEAN", "confidence": 0.85},
            "volume": {"liters": None, "source": "ESTIMATED", "confidence": 0.2},
            "recyclability": {"value": "RECYCLABLE", "confidence": 0.88},
            "reasoning": "Botella de vidrio, difícil determinar subtipo y volumen exacto",
        }

    monkeypatch.setattr(classifier_with_mock_adapter.adapter, "classify_material", classify_material_partial)

    image_bytes = _make_image_bytes()
    trace_id = "test-pipeline-partial"

    classification_result = await classifier_with_mock_adapter.classify(image_bytes, trace_id)

    assert classification_result.material.material_type.value == "GLASS"
    assert classification_result.subtype.value is None  # Low confidence
    assert classification_result.volume.liters is None  # Low confidence
    assert classification_result.partial_success is True


@pytest.mark.asyncio
async def test_pipeline_latency_under_1600ms(
    classifier_with_mock_adapter,
):
    """
    Con mocks debe ser muy rápido; solo verificamos que no se dispare la latencia.
    """
    import time

    image_bytes = _make_image_bytes()
    trace_id = "test-pipeline-latency"

    start = time.perf_counter()
    classification_result = await classifier_with_mock_adapter.classify(image_bytes, trace_id)
    assert classification_result.material.material_type is not None

    end = time.perf_counter()
    latency_ms = (end - start) * 1000.0

    print(f"\nPipeline E2E Latency: {latency_ms:.2f}ms")

    assert latency_ms < 1600.0, f"Classifier latency too high: {latency_ms:.2f}ms"
