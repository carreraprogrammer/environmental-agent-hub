"""
Unit tests for MaterialClassifier Agent V4.

Covers:
- Complete unified classification in one call
- Per-field confidence handling and partial success
- Rejection on low material confidence
- Prompt structure for unified classification
- Structured logging with per-field metrics
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from app.agents.material_classifier import (
    MaterialClassifier,
    build_classification_prompt,
)
from app.adapters.base import ClassifierAdapter
from app.schemas.classification import (
    Material,
    MaterialClassificationResult,
    PhysicalCondition,
    Recyclability,
    VolumeSource,
)


class DummyAdapter(ClassifierAdapter):
    """Simple adapter stub for testing MaterialClassifier."""

    def __init__(self, result_dict: dict[str, Any]) -> None:
        self._result_dict = result_dict

    async def classify(self, image_url: str, *, trace_id: str | None = None):  # type: ignore[override]
        raise NotImplementedError("V3 classify() not used in tests")

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        return dict(self._result_dict)

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return "dummy/model"

    @property
    def model_provider(self) -> str:  # type: ignore[override]
        return "dummy"

    @property
    def cost_per_request(self) -> float:  # type: ignore[override]
        return 0.010


def _base_result_dict() -> dict[str, Any]:
    """Base result dict for full classification."""
    return {
        "material": {"type": "PLASTIC", "confidence": 0.9},
        "subtype": {"value": "PET", "recycling_code": "#1", "confidence": 0.85},
        "condition": {"value": "CLEAN", "confidence": 0.8},
        "volume": {"liters": 0.5, "source": "LABEL_READ", "confidence": 0.8},
        "recyclability": {"value": "RECYCLABLE", "confidence": 0.9},
        "reasoning": "Botella PET de 500ml limpia.",
        "cost": 0.010,
        "model_used": "openai/gpt-4o",
        "model_provider": "openai",
        "metadata": {"raw": "test"},
    }


@pytest.mark.asyncio
async def test_complete_classification() -> None:
    """MaterialClassifier returns full classification with all fields."""
    adapter = DummyAdapter(_base_result_dict())
    classifier = MaterialClassifier(adapter)

    result = await classifier.classify(b"fake-bytes", "trace-complete")

    assert isinstance(result, MaterialClassificationResult)
    assert result.material.material_type == Material.PLASTIC
    assert result.material.confidence == pytest.approx(0.9)
    assert result.subtype.value == "PET"
    assert result.subtype.recycling_code == "#1"
    assert result.condition.value == PhysicalCondition.CLEAN
    assert result.volume.liters == pytest.approx(0.5)
    assert result.volume.source == VolumeSource.LABEL_READ
    assert result.recyclability.value == Recyclability.RECYCLABLE
    assert result.reasoning
    assert result.cost == pytest.approx(0.010)
    assert result.model_used == "openai/gpt-4o"
    assert result.model_provider == "openai"
    assert result.partial_success is False


@pytest.mark.asyncio
async def test_confidence_per_field() -> None:
    """MaterialClassifier handles per-field confidences and partial success."""
    data = _base_result_dict()
    # Force low subtype and volume confidences to trigger partial success
    data["subtype"]["confidence"] = 0.4  # < MIN_SUBTYPE_CONFIDENCE
    data["volume"]["confidence"] = 0.3  # < MIN_VOLUME_CONFIDENCE

    adapter = DummyAdapter(data)
    classifier = MaterialClassifier(adapter)

    result = await classifier.classify(b"fake-bytes", "trace-partial")

    # Material remains valid
    assert result.material.material_type == Material.PLASTIC

    # Subtype becomes None due to low confidence
    assert result.subtype.confidence == pytest.approx(0.4)
    assert result.subtype.value is None
    assert result.subtype.recycling_code is None

    # Volume liters becomes None due to low confidence
    assert result.volume.confidence == pytest.approx(0.3)
    assert result.volume.liters is None

    # Partial success flag should be True
    assert result.partial_success is True


@pytest.mark.asyncio
async def test_reject_low_material_confidence() -> None:
    """MaterialClassifier rejects classification if material confidence too low."""
    data = _base_result_dict()
    data["material"]["confidence"] = 0.2  # < MIN_MATERIAL_CONFIDENCE

    adapter = DummyAdapter(data)
    classifier = MaterialClassifier(adapter)

    with pytest.raises(ValueError):
        await classifier.classify(b"fake-bytes", "trace-low-material")


def test_prompt_structure() -> None:
    """Unified prompt contains key sections and JSON schema."""
    prompt = build_classification_prompt()

    # Key sections
    assert "Material Base" in prompt
    assert "Subtipo Específico" in prompt
    assert "Condición Física" in prompt
    assert "Volumen" in prompt
    assert "Reciclabilidad" in prompt

    # JSON structure hints
    assert '"material": {' in prompt
    assert '"subtype": {' in prompt
    assert '"volume": {' in prompt
    assert '"recyclability": {' in prompt
    assert '"reasoning":' in prompt


@pytest.mark.asyncio
async def test_structured_logging() -> None:
    """MaterialClassifier emits structured logs with per-field metrics."""
    data = _base_result_dict()
    adapter = DummyAdapter(data)
    classifier = MaterialClassifier(adapter)

    with patch("app.agents.material_classifier.logger") as mock_logger:
        result = await classifier.classify(b"fake-bytes", "trace-logging")

        # Verify started log
        start_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "material_classifier_started"
        ]
        assert start_calls, "Expected material_classifier_started log entry"

        # Verify complete log with key fields
        complete_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "material_classifier_complete"
        ]
        assert complete_calls, "Expected material_classifier_complete log entry"

        _, fields = complete_calls[0]
        assert fields["trace_id"] == "trace-logging"
        assert fields["material"] == result.material.material_type.value
        assert fields["material_confidence"] == result.material.confidence
        assert fields["subtype"] == result.subtype.value
        assert fields["volume_liters"] == result.volume.liters
        assert fields["partial_success"] == result.partial_success
        assert fields["cost_usd"] == result.cost
        assert fields["model_used"] == result.model_used
