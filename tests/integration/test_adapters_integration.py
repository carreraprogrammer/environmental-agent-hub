"""Integration-style tests for classifier adapters."""

from __future__ import annotations

import os

import pytest

from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.schemas.domain import WasteMaterial

pytestmark = pytest.mark.integration

TEST_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3f/Plastic_bottle.jpg"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled"
)
async def test_openai_adapter_real_api():
    adapter = OpenAIClassifierAdapter("gpt-4o")
    result = await adapter.classify(TEST_IMAGE_URL)

    assert result.material in WasteMaterial
    assert 0.0 <= result.confidence <= 1.0
    assert result.model_provider == "openai"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled"
)
async def test_google_adapter_real_api():
    adapter = GoogleClassifierAdapter()
    result = await adapter.classify(TEST_IMAGE_URL)

    assert result.material in WasteMaterial
    assert result.model_provider == "google"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled"
)
async def test_roboflow_adapter_real_api():
    adapter = RoboflowClassifierAdapter()
    result = await adapter.classify(TEST_IMAGE_URL)

    assert result.material in WasteMaterial
    assert result.model_provider == "roboflow"


@pytest.mark.asyncio
async def test_all_adapters_consistent_schema(monkeypatch):
    async def fake_classify(self, image_url: str, *, trace_id: str | None = None):
        from app.schemas.domain import ClassificationResult, WasteMaterial

        return ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.9,
            model_used=self.model_name,
            model_provider=self.model_provider,
            raw_response="PLASTIC",
        )

    monkeypatch.setattr(OpenAIClassifierAdapter, "classify", fake_classify)
    monkeypatch.setattr(GoogleClassifierAdapter, "classify", fake_classify)
    monkeypatch.setattr(RoboflowClassifierAdapter, "classify", fake_classify)

    adapters = [
        OpenAIClassifierAdapter(),
        GoogleClassifierAdapter(),
        RoboflowClassifierAdapter(),
    ]

    results = []
    for adapter in adapters:
        results.append(await adapter.classify(TEST_IMAGE_URL))

    for result in results:
        assert hasattr(result, "material")
        assert hasattr(result, "confidence")
        assert hasattr(result, "model_used")
        assert hasattr(result, "model_provider")
