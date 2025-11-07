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
    model_instance = Mock()
    version = SimpleNamespace(model=model_instance)

    def project_fn(project: str):
        return SimpleNamespace(version=lambda version_id: version)

    def workspace_fn(workspace: str):
        return SimpleNamespace(project=project_fn)

    monkeypatch.setattr(
        "app.adapters.roboflow_adapter.Roboflow",
        lambda api_key: SimpleNamespace(workspace=workspace_fn),
    )

    adapter = RoboflowClassifierAdapter("workspace/project/1")
    adapter.model = model_instance
    return adapter, model_instance


@pytest.mark.asyncio
async def test_classify_with_prediction(monkeypatch, adapter_with_model):
    adapter, model = adapter_with_model

    prediction_response = SimpleNamespace(
        predictions=[SimpleNamespace(class_name="PET_bottle", confidence=0.92)]
    )
    model.predict.return_value = prediction_response

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("app.adapters.roboflow_adapter.asyncio.to_thread", fake_to_thread)

    result = await adapter.classify("https://example.com/plastic.jpg")

    assert result.material == WasteMaterial.PLASTIC
    assert result.confidence == 0.92
    assert result.model_provider == "roboflow"


@pytest.mark.asyncio
async def test_classify_no_predictions(monkeypatch, adapter_with_model):
    adapter, model = adapter_with_model
    model.predict.return_value = SimpleNamespace(predictions=[])

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("app.adapters.roboflow_adapter.asyncio.to_thread", fake_to_thread)

    result = await adapter.classify("https://example.com/unknown.jpg")

    assert result.material == WasteMaterial.OTHER
    assert result.confidence == 0.0


def test_map_roboflow_class(adapter_with_model):
    adapter, _ = adapter_with_model

    assert adapter._map_roboflow_class("plastic") == WasteMaterial.PLASTIC
    assert adapter._map_roboflow_class("cardboard") == WasteMaterial.PAPER
    assert adapter._map_roboflow_class("glass_bottle") == WasteMaterial.GLASS
    assert adapter._map_roboflow_class("aluminum_can") == WasteMaterial.METAL
    assert adapter._map_roboflow_class("food_scraps") == WasteMaterial.ORGANIC
    assert adapter._map_roboflow_class("mystery") == WasteMaterial.OTHER


def test_invalid_model_id(monkeypatch):
    with pytest.raises(ValueError):
        RoboflowClassifierAdapter("invalid")
