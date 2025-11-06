"""Unit tests for the Google Gemini classifier adapter."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.adapters.google_adapter import GoogleClassifierAdapter
from app.schemas.domain import WasteMaterial


@pytest.fixture(autouse=True)
def reset_google_state():
    GoogleClassifierAdapter._request_timestamps.clear()
    GoogleClassifierAdapter._daily_requests = 0
    GoogleClassifierAdapter._daily_reset = datetime.now()
    from app.core.config import settings

    settings.GOOGLE_RATE_LIMIT_PER_MIN = 3
    settings.GOOGLE_DAILY_LIMIT = 5
    yield


@pytest.fixture
def adapter(monkeypatch):
    model_mock = MagicMock()
    model_mock.generate_content_async = AsyncMock()
    monkeypatch.setattr("app.adapters.google_adapter.genai.configure", lambda api_key: None)
    monkeypatch.setattr(
        "app.adapters.google_adapter.genai.GenerativeModel", lambda model_name: model_mock
    )
    instance = GoogleClassifierAdapter("gemini-pro-vision")
    instance.model = model_mock
    return instance


@pytest.mark.asyncio
async def test_classify_success(monkeypatch, adapter):
    adapter.model.generate_content_async.return_value = Mock(text="PLASTIC")
    monkeypatch.setattr(
        adapter,
        "_download_image",
        AsyncMock(return_value={"mime_type": "image/jpeg", "data": b"data"}),
    )

    result = await adapter.classify("https://example.com/image.jpg")

    assert result.material == WasteMaterial.PLASTIC
    assert result.model_provider == "google"
    assert result.confidence == 0.80


@pytest.mark.asyncio
async def test_rate_limit_wait(monkeypatch, adapter):
    now = datetime.now()
    GoogleClassifierAdapter._request_timestamps.extend(
        [now - timedelta(seconds=10), now - timedelta(seconds=5), now - timedelta(seconds=1)]
    )

    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.adapters.google_adapter.asyncio.sleep", fake_sleep)
    monkeypatch.setattr(
        adapter,
        "_download_image",
        AsyncMock(return_value={"mime_type": "image/jpeg", "data": b"data"}),
    )
    adapter.model.generate_content_async.return_value = Mock(text="PLASTIC")

    await adapter.classify("https://example.com/image.jpg")

    assert sleep_calls


@pytest.mark.asyncio
async def test_daily_limit_exceeded(monkeypatch, adapter):
    GoogleClassifierAdapter._daily_requests = 5
    GoogleClassifierAdapter._daily_reset = datetime.now()

    monkeypatch.setattr(
        adapter,
        "_download_image",
        AsyncMock(return_value={"mime_type": "image/jpeg", "data": b"data"}),
    )

    with pytest.raises(RuntimeError):
        await adapter.classify("https://example.com/image.jpg")


@pytest.mark.asyncio
async def test_download_image_too_large(monkeypatch, adapter):
    class MockResponse:
        def __init__(self):
            self.headers = {"content-length": str(15 * 1024 * 1024)}
            self.content = b""

        def raise_for_status(self) -> None:
            return None

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return MockResponse()

    monkeypatch.setattr("app.adapters.google_adapter.httpx.AsyncClient", MockAsyncClient)

    with pytest.raises(ValueError):
        await adapter._download_image("https://example.com/image.jpg", Mock())


@pytest.mark.asyncio
async def test_parse_material_variations(adapter):
    assert adapter._parse_material("PLASTIC") == WasteMaterial.PLASTIC
    assert adapter._parse_material("material de PAPEL") == WasteMaterial.PAPER
    assert adapter._parse_material("Vidrio reciclado") == WasteMaterial.GLASS
    assert adapter._parse_material("Metallic can") == WasteMaterial.METAL
    assert adapter._parse_material("Residuos orgánicos") == WasteMaterial.ORGANIC
    assert adapter._parse_material("Unknown item") == WasteMaterial.OTHER
