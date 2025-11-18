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


def test_parse_material_classification_valid_json(adapter):
    """Test parsing valid MaterialClassificationResult JSON."""
    content = """{
        "material": {"type": "PLASTIC", "confidence": 0.9},
        "subtype": {"value": "PET", "recycling_code": "#1", "confidence": 0.85},
        "condition": {"value": "CLEAN", "confidence": 0.8},
        "volume": {"liters": 0.5, "source": "LABEL_READ", "confidence": 0.8},
        "recyclability": {"value": "RECYCLABLE", "confidence": 0.9},
        "reasoning": "Botella PET de 500ml limpia"
    }"""

    result = adapter._parse_material_classification(content, "test-trace")

    assert result["material"]["type"] == "PLASTIC"
    assert result["material"]["confidence"] == 0.9
    assert result["subtype"]["value"] == "PET"
    assert result["subtype"]["recycling_code"] == "#1"
    assert result["volume"]["liters"] == 0.5
    assert result["volume"]["source"] == "LABEL_READ"


def test_parse_material_classification_with_markdown(adapter):
    """Test parsing JSON wrapped in markdown code blocks."""
    content = """```json
{
    "material": {"type": "PAPER", "confidence": 0.88},
    "subtype": {"value": "CARDBOARD", "recycling_code": null, "confidence": 0.75},
    "condition": {"value": "CLEAN", "confidence": 0.9},
    "volume": {"liters": null, "source": "ESTIMATED", "confidence": 0.4},
    "recyclability": {"value": "RECYCLABLE", "confidence": 0.95},
    "reasoning": "Caja de cartón limpia"
}
```"""

    result = adapter._parse_material_classification(content, "test-trace")

    assert result["material"]["type"] == "PAPER"
    assert result["subtype"]["value"] == "CARDBOARD"
    assert result["volume"]["liters"] is None


def test_parse_material_classification_partial_success(adapter):
    """Test parsing with null fields (partial success scenario)."""
    content = """{
        "material": {"type": "METAL", "confidence": 0.92},
        "subtype": {"value": null, "recycling_code": null, "confidence": 0.3},
        "condition": {"value": "DAMAGED", "confidence": 0.7},
        "volume": {"liters": null, "source": "ESTIMATED", "confidence": 0.2},
        "recyclability": {"value": "RECYCLABLE", "confidence": 0.85},
        "reasoning": "Lata metálica dañada, difícil determinar volumen"
    }"""

    result = adapter._parse_material_classification(content, "test-trace")

    assert result["material"]["type"] == "METAL"
    assert result["subtype"]["value"] is None
    assert result["subtype"]["confidence"] == 0.3
    assert result["volume"]["liters"] is None


def test_parse_material_classification_invalid_json(adapter):
    """Test fallback when JSON is invalid."""
    content = "This is not JSON at all"

    result = adapter._parse_material_classification(content, "test-trace")

    # Should return fallback structure
    assert result["material"]["type"] == "OTHER"
    assert result["material"]["confidence"] == 0.5
    assert "Error parsing response" in result["reasoning"]


def test_parse_material_classification_missing_fields(adapter):
    """Test fallback when required fields are missing."""
    content = """{"subtype": {"value": "PET"}}"""

    result = adapter._parse_material_classification(content, "test-trace")

    # Should return fallback structure
    assert result["material"]["type"] == "OTHER"
    assert "Error parsing response" in result["reasoning"]


class RateLimitErrorMock(Exception):
    """Simple mock to mimic OpenAI RateLimitError without importing class."""

    pass
