"""Integration tests for MaterialClassifier with OpenAI adapter.

These tests exercise the full MaterialClassifier V4 pipeline using the
real OpenAI Vision API (GPT-4o or similar) when RUN_INTEGRATION_TESTS=1
and OPENAI_API_KEY is configured.

They are skipped by default to avoid hitting external services in
regular CI runs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Ensure project root is on sys.path for imports
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.openai_adapter import OpenAIClassifierAdapter  # noqa: E402
from app.agents.material_classifier import MaterialClassifier  # noqa: E402
from app.schemas.classification import Material  # noqa: E402

pytestmark = pytest.mark.integration

IMAGES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "images"


def _load_image_bytes(name: str) -> bytes:
    """
    Load fixture image bytes for the given filename.

    For integration tests we require explicit fixtures; if they are
    missing, the test should fail with a clear message.
    """
    path = IMAGES_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing fixture image for MaterialClassifier OpenAI test: {path}. "
            "Add a representative PET bottle image (e.g. plastic bottle)."
        )
    return path.read_bytes()


requires_integration = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS") or not os.getenv("OPENAI_API_KEY"),
    reason="Integration tests disabled or OPENAI_API_KEY not set",
)


@requires_integration
@pytest.mark.asyncio
async def test_material_classifier_openai_pet_bottle() -> None:
    """
    End-to-end test: PET bottle classified as PLASTIC with reasonable confidence.
    """
    # Load test image (should be a PET plastic bottle)
    image_bytes = _load_image_bytes("pet_bottle.jpg")

    # Create adapter and classifier
    adapter = OpenAIClassifierAdapter()
    classifier = MaterialClassifier(adapter)

    result = await classifier.classify(image_bytes, "trace-openai-integration")

    # Basic assertions: material classification works and confidences are reasonable
    assert result.material.material_type == Material.PLASTIC
    assert result.material.confidence >= 0.7
    assert result.volume.liters is not None or result.partial_success
    assert result.reasoning

