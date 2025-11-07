"""Unit tests for the OpenAI classifier adapter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.schemas.domain import WasteMaterial


@pytest.fixture(autouse=True)
def reset_openai_settings():
    from app.core.config import settings

    settings.OPENAI_MAX_RETRIES = 3
    settings.OPENAI_TIMEOUT = 5
    settings.OPENAI_MODEL = "gpt-4o"
    yield


@pytest.fixture
def mock_openai_client():
    client = AsyncMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def adapter(mock_openai_client):
    with patch("app.adapters.openai_adapter.AsyncOpenAI", return_value=mock_openai_client):
        instance = OpenAIClassifierAdapter("gpt-4o")
        instance.client = mock_openai_client
        return instance


@pytest.mark.asyncio
async def test_classify_plastic_success(adapter, mock_openai_client):
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="PLASTIC"))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    result = await adapter.classify("https://example.com/plastic.jpg")

    assert result.material == WasteMaterial.PLASTIC
    assert result.confidence == 0.85
    assert result.model_provider == "openai"
    assert "gpt-4o" in result.model_used


@pytest.mark.asyncio
async def test_classify_fuzzy_match(adapter, mock_openai_client):
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="This is PLASTIC material"))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    result = await adapter.classify("https://example.com/plastic.jpg")

    assert result.material == WasteMaterial.PLASTIC
    assert result.confidence == 0.70


@pytest.mark.asyncio
async def test_classify_timeout(adapter, mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = asyncio.TimeoutError()

    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        await adapter.classify("https://example.com/test.jpg")


@pytest.mark.asyncio
async def test_retry_logic(adapter, mock_openai_client, monkeypatch):
    monkeypatch.setattr(
        "app.adapters.openai_adapter.RateLimitError", RateLimitErrorMock
    )

    responses = [RateLimitErrorMock(), RateLimitErrorMock(), Mock()]  # type: ignore[var-annotated]

    async def side_effect(*args, **kwargs):  # type: ignore[override]
        result = responses.pop(0)
        if isinstance(result, RateLimitErrorMock):
            raise result
        mock = Mock()
        mock.choices = [Mock(message=Mock(content="PLASTIC"))]
        return mock

    mock_openai_client.chat.completions.create.side_effect = side_effect

    sleep_calls = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.adapters.openai_adapter.asyncio.sleep", fake_sleep)

    result = await adapter.classify("https://example.com/plastic.jpg")

    assert result.material == WasteMaterial.PLASTIC
    assert sleep_calls == [1, 2]


@pytest.mark.asyncio
async def test_parse_material_edge_cases(adapter):
    assert adapter._parse_material("PLASTIC") == WasteMaterial.PLASTIC
    assert adapter._parse_material("plastic bottle") == WasteMaterial.PLASTIC
    assert adapter._parse_material("PLÁSTICO") == WasteMaterial.PLASTIC
    assert adapter._parse_material("unknown") == WasteMaterial.OTHER
    assert adapter._parse_material("") == WasteMaterial.OTHER


def test_model_name_property(adapter):
    assert adapter.model_name == "openai/gpt-4o"


def test_cost_per_request(adapter):
    assert adapter.cost_per_request == 0.005


class RateLimitErrorMock(Exception):
    """Simple mock to mimic OpenAI RateLimitError without importing class."""

    pass
