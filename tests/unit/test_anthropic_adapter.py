"""Unit tests for the Anthropic classifier adapter."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from app.adapters.anthropic_adapter import AnthropicAdapter


@pytest.fixture
def adapter(monkeypatch):
    """Create Anthropic adapter instance with mocked client."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key", raising=False)
    
    with patch("app.adapters.anthropic_adapter.AsyncAnthropic"):
        instance = AnthropicAdapter("claude-3-5-sonnet-20241022")
        return instance


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
    content = """Here's the classification:

```json
{
    "material": {"type": "PAPER", "confidence": 0.88},
    "subtype": {"value": "CARDBOARD", "recycling_code": null, "confidence": 0.75},
    "condition": {"value": "CLEAN", "confidence": 0.9},
    "volume": {"liters": null, "source": "ESTIMATED", "confidence": 0.4},
    "recyclability": {"value": "RECYCLABLE", "confidence": 0.95},
    "reasoning": "Caja de cartón limpia"
}
```

Based on the image analysis..."""

    result = adapter._parse_material_classification(content, "test-trace")

    assert result["material"]["type"] == "PAPER"
    assert result["subtype"]["value"] == "CARDBOARD"
    assert result["volume"]["liters"] is None
    assert result["volume"]["confidence"] == 0.4


def test_parse_material_classification_partial_success(adapter):
    """Test parsing with null fields (partial success scenario)."""
    content = """{
        "material": {"type": "METAL", "confidence": 0.92},
        "subtype": {"value": null, "recycling_code": null, "confidence": 0.3},
        "condition": {"value": "DAMAGED", "confidence": 0.7},
        "volume": {"liters": null, "source": "ESTIMATED", "confidence": 0.2},
        "recyclability": {"value": "RECYCLABLE", "confidence": 0.85},
        "reasoning": "Lata metálica dañada, difícil determinar volumen exacto"
    }"""

    result = adapter._parse_material_classification(content, "test-trace")

    assert result["material"]["type"] == "METAL"
    assert result["material"]["confidence"] == 0.92
    assert result["subtype"]["value"] is None
    assert result["subtype"]["confidence"] == 0.3
    assert result["volume"]["liters"] is None
    assert result["volume"]["confidence"] == 0.2


def test_parse_material_classification_invalid_json(adapter):
    """Test fallback when JSON is invalid."""
    content = "I cannot classify this image properly because..."

    result = adapter._parse_material_classification(content, "test-trace")

    # Should return fallback structure
    assert result["material"]["type"] == "OTHER"
    assert result["material"]["confidence"] == 0.5
    assert "Error parsing response" in result["reasoning"]


def test_parse_material_classification_missing_required_fields(adapter):
    """Test fallback when required fields are missing."""
    content = """{
        "subtype": {"value": "PET"},
        "volume": {"liters": 0.5}
    }"""

    result = adapter._parse_material_classification(content, "test-trace")

    # Should return fallback structure
    assert result["material"]["type"] == "OTHER"
    assert result["material"]["confidence"] == 0.5
    assert "Error parsing response" in result["reasoning"]


def test_parse_material_classification_nested_markdown(adapter):
    """Test parsing with nested markdown formatting."""
    content = """```
{
    "material": {"type": "GLASS", "confidence": 0.95},
    "subtype": {"value": "CLEAR_GLASS", "recycling_code": null, "confidence": 0.8},
    "condition": {"value": "CLEAN", "confidence": 0.9},
    "volume": {"liters": 0.75, "source": "LABEL_READ", "confidence": 0.85},
    "recyclability": {"value": "RECYCLABLE", "confidence": 0.98},
    "reasoning": "Botella de vidrio transparente de 750ml"
}
```"""

    result = adapter._parse_material_classification(content, "test-trace")

    assert result["material"]["type"] == "GLASS"
    assert result["material"]["confidence"] == 0.95
    assert result["volume"]["liters"] == 0.75


def test_model_name_property(adapter):
    """Test model_name property returns correct format."""
    assert adapter.model_name == "anthropic/claude-3-5-sonnet-20241022"


def test_model_provider_property(adapter):
    """Test model_provider property."""
    assert adapter.model_provider == "anthropic"


def test_cost_per_request(adapter):
    """Test cost_per_request property."""
    # Claude Sonnet 4.5 cost
    assert adapter.cost_per_request == 0.003
