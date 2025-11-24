"""Integration tests for PreValidator V4 anti-troll behaviour.

These tests exercise the full two-layer validation using different
image scenarios (person, landscape, meme, food) and a stubbed
Roboflow client to avoid real network calls.

If real fixture images are available, place them under:
    tests/fixtures/images/
with names:
    - person.jpg
    - landscape.jpg
    - meme.jpg
    - food.jpg

If files are missing, the tests fall back to generating simple
in-memory images (256x256 JPEG) so they still run deterministically.
"""

from __future__ import annotations

import pytest

pytest.skip(
    "PreValidator eliminado del pipeline backend; detección de waste vive en MaterialClassifier",
    allow_module_level=True,
)

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

from app.agents.pre_validator import PreValidator  # noqa: E402
from app.schemas.classification import ValidationReason  # noqa: E402

pytestmark = pytest.mark.integration

IMAGES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "images"


def _load_image_bytes(name: str) -> bytes:
    """
    Load fixture image bytes for the given filename.

    These tests are meant to be realistic integration checks, so they
    require explicit fixture images to be present. If an image is
    missing, the test should FAIL and explain which file is needed.
    """
    path = IMAGES_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing fixture image for anti-troll test: {path}. "
            "Add a representative JPEG image for this scenario "
            "(person, landscape, meme, or food on a plate)."
        )
    return path.read_bytes()


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Roboflow settings for integration tests."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROBOFLOW_MODEL_ID", "workspace/project/1", raising=False)
    monkeypatch.setattr(settings, "ROBOFLOW_API_KEY", "test-key", raising=False)


@pytest.fixture
def prevalidator_with_stub(monkeypatch: pytest.MonkeyPatch) -> tuple[PreValidator, Any]:
    """
    PreValidator instance with a stubbed Roboflow model (no network).

    Each test can customise `dummy_model.predictions` to simulate different
    detection scenarios.
    """

    class DummyModel:
        def __init__(self) -> None:
            self.predictions: list[Any] = []

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

    # Patch Roboflow reference used by PreValidator
    monkeypatch.setattr("app.agents.pre_validator.Roboflow", DummyRoboflow, raising=False)

    # Ensure asyncio.to_thread does not introduce extra overhead or threads
    async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
        return func(*args, **kwargs)

    monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

    validator = PreValidator(model_id="workspace/project/1")
    validator.model = dummy_model
    return validator, dummy_model


@pytest.mark.asyncio
async def test_person_image_rejected(prevalidator_with_stub: tuple[PreValidator, Any]) -> None:
    """Person/face image (selfie) should be rejected (no waste)."""
    validator, dummy_model = prevalidator_with_stub

    # No detections for person image
    dummy_model.predictions = []

    image_bytes = _load_image_bytes("person.jpg")
    result = await validator.validate(image_bytes, "trace-person")

    assert result.is_valid is False
    assert result.reason == ValidationReason.NO_WASTE_DETECTED
    assert result.metadata.get("num_detections") == 0


@pytest.mark.asyncio
async def test_landscape_image_rejected(prevalidator_with_stub: tuple[PreValidator, Any]) -> None:
    """Landscape image should be rejected (no waste)."""
    validator, dummy_model = prevalidator_with_stub

    dummy_model.predictions = []

    image_bytes = _load_image_bytes("landscape.jpg")
    result = await validator.validate(image_bytes, "trace-landscape")

    assert result.is_valid is False
    assert result.reason == ValidationReason.NO_WASTE_DETECTED
    assert result.metadata.get("num_detections") == 0


@pytest.mark.asyncio
async def test_meme_image_rejected(prevalidator_with_stub: tuple[PreValidator, Any]) -> None:
    """Meme/text image should be rejected (no waste)."""
    validator, dummy_model = prevalidator_with_stub

    dummy_model.predictions = []

    image_bytes = _load_image_bytes("meme.jpg")
    result = await validator.validate(image_bytes, "trace-meme")

    assert result.is_valid is False
    assert result.reason == ValidationReason.NO_WASTE_DETECTED
    assert result.metadata.get("num_detections") == 0


@pytest.mark.asyncio
async def test_food_image_accepted(prevalidator_with_stub: tuple[PreValidator, Any]) -> None:
    """Food-on-plate image should be accepted as biodegradable waste."""
    validator, dummy_model = prevalidator_with_stub

    # Simulate detection of biodegradable waste
    dummy_model.predictions = [
        SimpleNamespace(
            class_name="biodegradable",
            confidence=0.9,
            x=10,
            y=20,
            width=30,
            height=40,
        )
    ]

    image_bytes = _load_image_bytes("food.jpg")
    result = await validator.validate(image_bytes, "trace-food")

    assert result.is_valid is True
    assert result.reason == ValidationReason.WASTE_DETECTED
    assert result.metadata.get("num_detections") == 1
    classes = result.metadata.get("classes") or []
    assert "biodegradable" in classes
