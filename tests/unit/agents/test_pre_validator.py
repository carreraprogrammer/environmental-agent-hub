from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.pre_validator import PreValidator
from app.schemas.validation import ValidationResult


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


@pytest.mark.asyncio
async def test_validate_returns_true_for_waste(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    async def mock_call(*args, **kwargs) -> ValidationResult:  # type: ignore[no-untyped-def]
        return ValidationResult(has_waste=True, confidence=0.92, reason="Botella plástica visible")

    monkeypatch.setattr(validator, "_call_gpt4o_mini", mock_call)

    result = await validator.validate(b"fake_image_bytes", "trace-1")
    assert result.has_waste is True
    assert result.confidence == pytest.approx(0.92)
    assert "Botella" in result.reason


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason",
    [
        "Selfie de una persona",
        "Paisaje sin basura",
    ],
)
async def test_validate_returns_false_for_non_waste(reason: str, monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    async def mock_call(*args, **kwargs) -> ValidationResult:  # type: ignore[no-untyped-def]
        return ValidationResult(has_waste=False, confidence=0.15, reason=reason)

    monkeypatch.setattr(validator, "_call_gpt4o_mini", mock_call)

    result = await validator.validate(b"fake_image_bytes", "trace-2")
    assert result.has_waste is False
    assert result.confidence == pytest.approx(0.15)
    assert reason in result.reason


@pytest.mark.asyncio
async def test_validate_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    async def slow_response(*args, **kwargs) -> ValidationResult:  # type: ignore[no-untyped-def]
        await asyncio.sleep(1.0)  # exceed 500ms
        return ValidationResult(has_waste=True, confidence=0.9, reason="Test slow")

    monkeypatch.setattr(validator, "_call_gpt4o_mini", slow_response)

    with pytest.raises(TimeoutError):
        await validator.validate(b"fake_image", "trace-timeout")


@pytest.mark.asyncio
async def test_validate_api_error_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    async def failing_call(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("API failure")

    monkeypatch.setattr(validator, "_call_gpt4o_mini", failing_call)

    with pytest.raises(ValueError) as exc:
        await validator.validate(b"fake_image", "trace-error")
    assert "PreValidator failed" in str(exc.value)


@pytest.mark.asyncio
async def test_call_gpt4o_mini_parses_plain_json(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    # Build fake nested client with AsyncMock
    validator.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace())
    )

    content = (
        '{"has_waste": true, "confidence": 0.88, "reason": "Lata y envolturas"}'
    )
    validator.client.chat.completions.create = AsyncMock(
        return_value=FakeResponse(content)
    )

    result = await validator._call_gpt4o_mini(b"img", "trace-json")
    assert result.has_waste is True
    assert result.confidence == pytest.approx(0.88)
    assert "Lata" in result.reason


@pytest.mark.asyncio
async def test_call_gpt4o_mini_parses_markdown_json(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    validator.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace())
    )

    content = (
        "```json\n{\n  \"has_waste\": false,\n  \"confidence\": 0.2,\n  \"reason\": \"Selfie sin residuos\"\n}\n```"
    )
    validator.client.chat.completions.create = AsyncMock(
        return_value=FakeResponse(content)
    )

    result = await validator._call_gpt4o_mini(b"img", "trace-md")
    assert result.has_waste is False
    assert result.confidence == pytest.approx(0.2)
    assert "Selfie" in result.reason


@pytest.mark.asyncio
async def test_call_gpt4o_mini_parsing_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = PreValidator()

    validator.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace())
    )

    # Invalid JSON should trigger fallback
    content = "not-json-response"
    validator.client.chat.completions.create = AsyncMock(
        return_value=FakeResponse(content)
    )

    result = await validator._call_gpt4o_mini(b"img", "trace-fallback")
    assert result.has_waste is True
    assert result.confidence == pytest.approx(0.5)
    assert "Error parsing" in result.reason

