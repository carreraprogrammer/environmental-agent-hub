"""Integration tests for ClassifierFactory with real adapters.

Tests without RUN_INTEGRATION_TESTS must not hit external services.
We patch the Roboflow client to avoid network on instantiation.
"""

from __future__ import annotations

import os

import pytest
from unittest.mock import patch

from app.factories.classifier_factory import ClassifierFactory
from app.schemas.domain import WasteMaterial

pytestmark = pytest.mark.integration

TEST_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3f/Plastic_bottle.jpg"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled"
)
async def test_factory_roboflow_integration():
    """Test ClassifierFactory with Roboflow adapter using real API."""
    adapter = ClassifierFactory.create(model_override="roboflow")

    result = await adapter.classify(TEST_IMAGE_URL)

    assert result.material in WasteMaterial
    assert 0.0 <= result.confidence <= 1.0
    assert result.model_provider == "roboflow"
    assert "roboflow" in result.model_used


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled"
)
async def test_factory_openai_integration():
    """Test ClassifierFactory with OpenAI adapter using real API."""
    adapter = ClassifierFactory.create(model_override="openai-gpt4o")

    result = await adapter.classify(TEST_IMAGE_URL)

    assert result.material in WasteMaterial
    assert 0.0 <= result.confidence <= 1.0
    assert result.model_provider == "openai"
    assert "gpt-4o" in result.model_used


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled"
)
async def test_factory_gemini_integration():
    """Test ClassifierFactory with Gemini adapter using real API."""
    adapter = ClassifierFactory.create(model_override="gemini")

    result = await adapter.classify(TEST_IMAGE_URL)

    assert result.material in WasteMaterial
    assert 0.0 <= result.confidence <= 1.0
    assert result.model_provider == "google"


@pytest.mark.asyncio
@patch("app.adapters.roboflow_adapter.InferenceHTTPClient")
async def test_factory_model_switching(mock_inference_client):
    """Test that factory can switch between different models without code changes."""
    from app.core.config import settings

    # Test switching via settings
    settings.CLASSIFIER_MODEL = "openai-gpt4"
    adapter1 = ClassifierFactory.create()
    assert "openai" in adapter1.model_provider

    # Test switching via override
    adapter2 = ClassifierFactory.create(model_override="gemini")
    assert "google" in adapter2.model_provider

    # Mock InferenceHTTPClient to avoid network
    mock_client = mock_inference_client.return_value
    mock_client.infer.return_value = {"predictions": []}

    adapter3 = ClassifierFactory.create(model_override="roboflow")
    assert "roboflow" in adapter3.model_provider


@pytest.mark.asyncio
@patch("app.adapters.roboflow_adapter.InferenceHTTPClient")
async def test_factory_all_adapters_consistent_interface(mock_inference_client):
    """Test that all adapters created by factory have consistent interface."""
    model_ids = ClassifierFactory.list_available()

    for model_id in model_ids:
        if model_id == "claude":
            # Skip claude as it's not fully implemented
            continue

        # Mock InferenceHTTPClient to avoid network
        mock_client = mock_inference_client.return_value
        mock_client.infer.return_value = {"predictions": []}

        adapter = ClassifierFactory.create(model_override=model_id)

        # Verify all adapters have required properties
        assert hasattr(adapter, "model_name")
        assert hasattr(adapter, "model_provider")
        assert hasattr(adapter, "cost_per_request")
        assert hasattr(adapter, "classify")

        # Verify properties return expected types
        assert isinstance(adapter.model_name, str)
        assert isinstance(adapter.model_provider, str)
        assert isinstance(adapter.cost_per_request, float)
