"""Integration tests for MaterialClassifier with Google Gemini adapter.

These tests exercise the full MaterialClassifier V4 pipeline using the
real Gemini Vision models when RUN_INTEGRATION_TESTS=1 and GOOGLE_API_KEY
is configured.

They are skipped by default to avoid hitting external services in
regular CI runs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.google_adapter import GoogleClassifierAdapter  # noqa: E402
from app.agents.material_classifier import MaterialClassifier  # noqa: E402
from app.schemas.classification import Material  # noqa: E402

pytestmark = pytest.mark.integration

IMAGES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "images"


def _load_image_bytes(name: str) -> bytes:
    path = IMAGES_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing fixture image for MaterialClassifier Gemini test: {path}. "
            "Add a representative PET bottle image (e.g. plastic bottle)."
        )
    return path.read_bytes()


requires_integration = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS") or not os.getenv("GOOGLE_API_KEY"),
    reason="Integration tests disabled or GOOGLE_API_KEY not set",
)


@requires_integration
@pytest.mark.asyncio
async def test_material_classifier_gemini_pet_bottle() -> None:
    """
    End-to-end test: PET bottle classified as PLASTIC with reasonable confidence.
    """
    image_bytes = _load_image_bytes("pet_bottle.jpg")

    adapter = GoogleClassifierAdapter()
    classifier = MaterialClassifier(adapter)

    result = await classifier.classify(image_bytes, "trace-gemini-integration")

    assert result.material.material_type == Material.PLASTIC
    assert result.material.confidence >= 0.7
    assert result.reasoning

