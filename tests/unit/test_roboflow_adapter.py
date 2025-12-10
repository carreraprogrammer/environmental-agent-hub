"""Unit tests for the Roboflow classifier adapter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.schemas.domain import WasteMaterial


@pytest.fixture(autouse=True)
def configure_settings():
    from app.core.config import settings

    settings.ROBOFLOW_MODEL_ID = "workspace/project/1"
    settings.ROBOFLOW_CONFIDENCE_THRESHOLD = 0.4
    yield


@pytest.fixture
def adapter_with_model(monkeypatch):
    """Mock the InferenceHTTPClient instead of old Roboflow SDK."""
    mock_client = Mock()

    # Mock InferenceHTTPClient constructor
    monkeypatch.setattr(
        "app.adapters.roboflow_adapter.InferenceHTTPClient",
        lambda api_url, api_key: mock_client,
    )

    adapter = RoboflowClassifierAdapter("workspace/project/1")
    return adapter, mock_client


@pytest.mark.asyncio
async def test_classify_with_prediction(monkeypatch, adapter_with_model):
    adapter, mock_client = adapter_with_model

    # Mock InferenceHTTPClient.infer response
    prediction_response = {
        "predictions": [
            {"class": "PET_bottle", "confidence": 0.92, "class_id": 0}
        ]
    }
    mock_client.infer.return_value = prediction_response

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("app.adapters.roboflow_adapter.asyncio.to_thread", fake_to_thread)

    result = await adapter.classify("https://example.com/plastic.jpg")

    assert result.material == WasteMaterial.PLASTIC
    assert result.confidence == 0.92
    assert result.model_provider == "roboflow"


@pytest.mark.asyncio
async def test_classify_no_predictions(monkeypatch, adapter_with_model):
    adapter, mock_client = adapter_with_model
    
    # Mock InferenceHTTPClient.infer response with no predictions
    mock_client.infer.return_value = {"predictions": []}

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("app.adapters.roboflow_adapter.asyncio.to_thread", fake_to_thread)

    result = await adapter.classify("https://example.com/unknown.jpg")

    assert result.material == WasteMaterial.OTHER
    assert result.confidence == 0.0


def test_map_roboflow_class(adapter_with_model):
    adapter, _ = adapter_with_model

    # Test direct mappings
    assert adapter._map_roboflow_class("plastic") == WasteMaterial.PLASTIC
    assert adapter._map_roboflow_class("paper") == WasteMaterial.PAPER
    assert adapter._map_roboflow_class("glass") == WasteMaterial.GLASS
    assert adapter._map_roboflow_class("metal") == WasteMaterial.METAL
    assert adapter._map_roboflow_class("organic") == WasteMaterial.ORGANIC
    assert adapter._map_roboflow_class("cardboard") == WasteMaterial.PAPER
    
    # Test heuristics
    assert adapter._map_roboflow_class("PET_bottle") == WasteMaterial.PLASTIC
    assert adapter._map_roboflow_class("aluminum_can") == WasteMaterial.METAL
    assert adapter._map_roboflow_class("food_scraps") == WasteMaterial.ORGANIC
    assert adapter._map_roboflow_class("mystery") == WasteMaterial.OTHER


def test_invalid_model_id(monkeypatch):
    """Test that invalid model_id format raises ValueError."""
    # Mock InferenceHTTPClient to prevent actual API calls
    monkeypatch.setattr(
        "app.adapters.roboflow_adapter.InferenceHTTPClient",
        lambda api_url, api_key: Mock(),
    )
    
    with pytest.raises(ValueError, match="workspace/project/version"):
        RoboflowClassifierAdapter("invalid")
