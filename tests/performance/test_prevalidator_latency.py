"""
Performance test for PreValidator V4 latency.

Validates that the two-layer validation (technical + Roboflow) runs
comfortably under 500ms p95 when Roboflow is responsive.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "PreValidator eliminado del pipeline backend; detección de waste vive en MaterialClassifier",
    allow_module_level=True,
)

import asyncio
import time
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image

# Ensure project root is on sys.path for imports
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _make_image_bytes(width: int = 256, height: int = 256, fmt: str = "JPEG") -> bytes:
    """Create a simple in-memory image and return its bytes."""
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Roboflow settings for performance tests."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROBOFLOW_MODEL_ID", "workspace/project/1", raising=False)
    monkeypatch.setattr(settings, "ROBOFLOW_API_KEY", "test-key", raising=False)


@pytest.fixture
def validator_fast_roboflow(monkeypatch: pytest.MonkeyPatch):
    """
    PreValidator instance with a fast, in-memory Roboflow stub (no network).

    This isolates PreValidator overhead from external latency and focuses
    on the internal two-layer validation cost.
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
            # Immediate in-memory prediction
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

    # Patch Roboflow reference used by PreValidator
    monkeypatch.setattr("app.agents.pre_validator.Roboflow", DummyRoboflow, raising=False)

    # Ensure asyncio.to_thread doesn't introduce extra overhead during tests
    async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
        return func(*args, **kwargs)

    monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

    from app.agents.pre_validator import PreValidator as _PreValidator

    return _PreValidator(model_id="workspace/project/1")


@pytest.mark.asyncio
async def test_prevalidator_latency_p95_under_500ms(validator_fast_roboflow) -> None:
    """
    Measure PreValidator latency and assert p95 < 500ms.

    Uses a fast in-memory Roboflow stub so this test is deterministic and
    reflects the internal overhead of the two-layer validation.
    """
    image_bytes = _make_image_bytes()

    latencies_ms: list[float] = []
    iterations = 20

    for i in range(iterations):
        start = time.perf_counter()
        _ = await validator_fast_roboflow.validate(image_bytes, f"trace-latency-{i}")
        end = time.perf_counter()

        latencies_ms.append((end - start) * 1000.0)

    latencies_ms.sort()
    # Simple p95 estimation
    index_95 = max(int(iterations * 0.95) - 1, 0)
    p95 = latencies_ms[index_95]

    # This threshold matches the EDV-51 requirement (<500ms)
    assert p95 < 500.0, f"PreValidator p95 latency too high: {p95:.2f}ms"
