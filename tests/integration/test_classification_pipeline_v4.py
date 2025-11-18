"""
Integration test for Classification Pipeline V4.

Tests the complete flow: PreValidator → MaterialClassifier

This validates that the two main agents work correctly together
and that data flows properly between them.
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

# Ensure project root is on sys.path for imports
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.pre_validator import PreValidator
from app.agents.material_classifier import MaterialClassifier
from app.adapters.base import ClassifierAdapter
from app.schemas.classification import ValidationReason


pytestmark = pytest.mark.integration


def _make_image_bytes(width: int = 256, height: int = 256, fmt: str = "JPEG") -> bytes:
    """Create a simple in-memory image and return its bytes."""
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure test settings."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROBOFLOW_MODEL_ID", "workspace/project/1", raising=False)
    monkeypatch.setattr(settings, "ROBOFLOW_API_KEY", "test-key", raising=False)


@pytest.fixture
def prevalidator_with_stub(monkeypatch: pytest.MonkeyPatch):
    """
    PreValidator with stubbed Roboflow that always detects waste.
    """

    class DummyModel:
        def __init__(self) -> None:
            self.predictions: list[Any] = [
                SimpleNamespace(
                    class_name="plastic_bottle",
                    confidence=0.9,
                    x=10,
                    y=20,
                    width=30,
                    height=40,
                )
            ]

        def predict(self, *_args: Any, **_kwargs: Any) -> Any:
            return SimpleNamespace(predictions=self.predictions)

    dummy_model = DummyModel()

    class DummyVersion:
        def __init__(self) -> None:
            self.model = dummy_model

    class DummyProject:
        def version(self, _version: str) -> DummyVersion:
            return DummyVersion()

    class DummyWorkspace:
        def project(self, _project: str) -> DummyProject:
            return DummyProject()

    class DummyRoboflow:
        def __init__(self, api_key: str) -> None:  # noqa: ARG002
            self._workspace = DummyWorkspace()

        def workspace(self, _workspace: str) -> DummyWorkspace:
            return self._workspace

    monkeypatch.setattr("app.agents.pre_validator.Roboflow", DummyRoboflow, raising=False)

    async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
        return func(*args, **kwargs)

    monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

    validator = PreValidator(model_id="workspace/project/1")
    validator.model = dummy_model
    return validator


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
async def test_pipeline_prevalidator_to_material_classifier_success(
    prevalidator_with_stub,
    classifier_with_mock_adapter,
):
    """
    Test complete pipeline flow: PreValidator → MaterialClassifier.

    Validates:
    1. PreValidator accepts valid waste image
    2. MaterialClassifier processes the same image
    3. Data flows correctly between agents
    4. Total latency < 1500ms
    """
    image_bytes = _make_image_bytes()
    trace_id = "test-pipeline-e2e"

    # Step 1: PreValidator
    validation_result = await prevalidator_with_stub.validate(image_bytes, trace_id)

    assert validation_result.is_valid is True
    assert validation_result.reason == ValidationReason.WASTE_DETECTED
    assert validation_result.metadata.get("num_detections") == 1

    # Step 2: MaterialClassifier (only if validation passed)
    if validation_result.is_valid:
        classification_result = await classifier_with_mock_adapter.classify(
            image_bytes, trace_id
        )

        assert classification_result.material.material_type.value == "PLASTIC"
        assert classification_result.material.confidence >= 0.7
        assert classification_result.subtype.value == "PET"
        assert classification_result.volume.liters == 0.5
        assert classification_result.partial_success is False


@pytest.mark.asyncio
async def test_pipeline_rejects_invalid_image(
    prevalidator_with_stub,
    classifier_with_mock_adapter,
):
    """
    Test pipeline rejects invalid images at PreValidator stage.

    MaterialClassifier should not be called if PreValidator rejects.
    """
    invalid_image = b"not-a-valid-image"
    trace_id = "test-pipeline-invalid"

    # Step 1: PreValidator should reject
    validation_result = await prevalidator_with_stub.validate(invalid_image, trace_id)

    assert validation_result.is_valid is False
    assert validation_result.reason == ValidationReason.INVALID_FORMAT

    # Step 2: MaterialClassifier should NOT be called
    # (this is a behavior test - in production, orchestrator would stop here)


@pytest.mark.asyncio
async def test_pipeline_no_waste_detected(prevalidator_with_stub, monkeypatch):
    """
    Test pipeline when PreValidator detects no waste.

    MaterialClassifier should not be called if no waste is detected.
    """
    # Modify stub to return no detections
    prevalidator_with_stub.model.predictions = []

    image_bytes = _make_image_bytes()
    trace_id = "test-pipeline-no-waste"

    # Step 1: PreValidator should reject (no waste)
    validation_result = await prevalidator_with_stub.validate(image_bytes, trace_id)

    assert validation_result.is_valid is False
    assert validation_result.reason == ValidationReason.NO_WASTE_DETECTED
    assert validation_result.metadata.get("num_detections") == 0


@pytest.mark.asyncio
async def test_pipeline_with_partial_success(
    prevalidator_with_stub,
    classifier_with_mock_adapter,
    monkeypatch,
):
    """
    Test pipeline handles partial success in MaterialClassifier.

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

    monkeypatch.setattr(
        classifier_with_mock_adapter.adapter,
        "classify_material",
        classify_material_partial,
    )

    image_bytes = _make_image_bytes()
    trace_id = "test-pipeline-partial"

    # Step 1: PreValidator
    validation_result = await prevalidator_with_stub.validate(image_bytes, trace_id)
    assert validation_result.is_valid is True

    # Step 2: MaterialClassifier with partial success
    classification_result = await classifier_with_mock_adapter.classify(image_bytes, trace_id)

    assert classification_result.material.material_type.value == "GLASS"
    assert classification_result.subtype.value is None  # Low confidence
    assert classification_result.volume.liters is None  # Low confidence
    assert classification_result.partial_success is True


@pytest.mark.asyncio
async def test_pipeline_latency_under_1600ms(
    prevalidator_with_stub,
    classifier_with_mock_adapter,
):
    """
    Test total pipeline latency is under 1600ms.

    Target breakdown:
    - PreValidator: <500ms (EDV-51 requirement)
    - MaterialClassifier: <1500ms (EDV-51 requirement)
    - Buffer: 100ms
    - Total: <1600ms
    """
    import time

    image_bytes = _make_image_bytes()
    trace_id = "test-pipeline-latency"

    start = time.perf_counter()

    # Step 1: PreValidator
    validation_result = await prevalidator_with_stub.validate(image_bytes, trace_id)
    assert validation_result.is_valid is True

    # Step 2: MaterialClassifier
    classification_result = await classifier_with_mock_adapter.classify(image_bytes, trace_id)
    assert classification_result.material.material_type is not None

    end = time.perf_counter()
    latency_ms = (end - start) * 1000.0

    print(f"\nPipeline E2E Latency: {latency_ms:.2f}ms")

    # With mocks, should be very fast (<50ms)
    # In production with real APIs, target is <1600ms
    assert latency_ms < 1600.0, f"Pipeline E2E latency too high: {latency_ms:.2f}ms"
