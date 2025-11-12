"""
Unit tests for PreValidator Agent.

Tests cover:
- Successful waste detection (has_waste=True)
- Successful non-waste detection (has_waste=False)
- Timeout handling (500ms limit)
- API error handling
- JSON parsing (plain JSON, markdown code blocks, invalid JSON)
- Fallback behavior on parsing errors
- Logging verification
- Context manager support
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.agents.pre_validator import PreValidator
from app.schemas.validation import ValidationResult


class TestValidationResultSchema:
    """Test ValidationResult schema."""

    def test_validation_result_valid(self):
        """Test ValidationResult with valid data."""
        result = ValidationResult(
            has_waste=True,
            confidence=0.95,
            reason="Botella de plástico detectada",
        )

        assert result.has_waste is True
        assert result.confidence == 0.95
        assert result.reason == "Botella de plástico detectada"

    def test_validation_result_confidence_bounds(self):
        """Test ValidationResult confidence must be between 0.0 and 1.0."""
        # Valid bounds
        ValidationResult(has_waste=True, confidence=0.0, reason="Test")
        ValidationResult(has_waste=True, confidence=1.0, reason="Test")

        # Invalid bounds
        with pytest.raises(ValueError):
            ValidationResult(has_waste=True, confidence=-0.1, reason="Test")

        with pytest.raises(ValueError):
            ValidationResult(has_waste=True, confidence=1.1, reason="Test")

    def test_validation_result_reason_min_length(self):
        """Test ValidationResult reason must not be empty."""
        with pytest.raises(ValueError):
            ValidationResult(has_waste=True, confidence=0.95, reason="")

    def test_validation_result_reason_max_length(self):
        """Test ValidationResult reason must not exceed 500 chars."""
        # Valid length
        ValidationResult(has_waste=True, confidence=0.95, reason="x" * 500)

        # Invalid length
        with pytest.raises(ValueError):
            ValidationResult(has_waste=True, confidence=0.95, reason="x" * 501)


class TestPreValidatorWasteDetection:
    """Test PreValidator with waste images."""

    @pytest.mark.asyncio
    async def test_validate_with_waste_success(self):
        """Test successful waste detection."""
        validator = PreValidator(timeout=2.0)  # Higher timeout for tests
        trace_id = str(uuid4())

        # Mock OpenAI response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """```json
{
  "has_waste": true,
  "confidence": 0.95,
  "reason": "Botella de plástico detectada en el suelo"
}
```"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            assert isinstance(result, ValidationResult)
            assert result.has_waste is True
            assert result.confidence == 0.95
            assert "Botella de plástico" in result.reason

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_with_waste_plain_json(self):
        """Test waste detection with plain JSON response (no markdown)."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        # Mock OpenAI response with plain JSON
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": true,
  "confidence": 0.88,
  "reason": "Lata de aluminio en la imagen"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            assert result.has_waste is True
            assert result.confidence == 0.88
            assert "Lata de aluminio" in result.reason

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_with_multiple_waste_items(self):
        """Test waste detection with multiple items."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": true,
  "confidence": 0.92,
  "reason": "Múltiples residuos: botella, lata y papel"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            assert result.has_waste is True
            assert result.confidence == 0.92

        await validator.close()


class TestPreValidatorNonWasteDetection:
    """Test PreValidator with non-waste images (trolls)."""

    @pytest.mark.asyncio
    async def test_validate_selfie_rejected(self):
        """Test that selfies are rejected (has_waste=False)."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": false,
  "confidence": 0.99,
  "reason": "Selfie de una persona, no contiene residuos"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_selfie_data", trace_id)

            assert result.has_waste is False
            assert result.confidence == 0.99
            assert "Selfie" in result.reason or "persona" in result.reason

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_landscape_rejected(self):
        """Test that landscapes are rejected (has_waste=False)."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": false,
  "confidence": 0.95,
  "reason": "Paisaje de montaña, sin residuos visibles"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_landscape_data", trace_id)

            assert result.has_waste is False
            assert result.confidence == 0.95

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_blurry_image_rejected(self):
        """Test that blurry images are rejected with low confidence."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": false,
  "confidence": 0.3,
  "reason": "Imagen borrosa, no se puede determinar contenido"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_blurry_data", trace_id)

            assert result.has_waste is False
            assert result.confidence == 0.3

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_animal_rejected(self):
        """Test that animal images are rejected."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": false,
  "confidence": 0.98,
  "reason": "Imagen de un perro, no contiene residuos"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_animal_data", trace_id)

            assert result.has_waste is False
            assert result.confidence == 0.98

        await validator.close()


class TestPreValidatorTimeout:
    """Test PreValidator timeout handling."""

    @pytest.mark.asyncio
    async def test_validate_timeout_raises_error(self):
        """Test that timeout raises TimeoutError."""
        validator = PreValidator(timeout=0.1)  # Very short timeout
        trace_id = str(uuid4())

        # Mock slow response (exceeds timeout)
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms - exceeds 100ms timeout
            return Mock()

        mock_create = AsyncMock(side_effect=slow_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            with pytest.raises(TimeoutError, match="PreValidator timeout"):
                await validator.validate(b"fake_image_data", trace_id)

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_timeout_default_500ms(self):
        """Test that default timeout is 500ms."""
        validator = PreValidator()

        assert validator.timeout == 0.5

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_timeout_custom(self):
        """Test that custom timeout can be set."""
        validator = PreValidator(timeout=2.0)

        assert validator.timeout == 2.0

        await validator.close()


class TestPreValidatorAPIErrors:
    """Test PreValidator API error handling."""

    @pytest.mark.asyncio
    async def test_validate_api_error_raises_value_error(self):
        """Test that API errors raise ValueError."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        # Mock API error
        mock_create = AsyncMock(side_effect=Exception("API rate limit exceeded"))

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            with pytest.raises(ValueError, match="PreValidator failed"):
                await validator.validate(b"fake_image_data", trace_id)

        await validator.close()

    @pytest.mark.asyncio
    async def test_validate_empty_response_raises_error(self):
        """Test that empty response raises ValueError."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        # Mock empty response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = None  # Empty content
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            with pytest.raises(ValueError, match="PreValidator failed"):
                await validator.validate(b"fake_image_data", trace_id)

        await validator.close()


class TestPreValidatorParsing:
    """Test PreValidator JSON parsing."""

    @pytest.mark.asyncio
    async def test_parse_markdown_json_block(self):
        """Test parsing JSON inside markdown code blocks."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """Here's the result:

```json
{
  "has_waste": true,
  "confidence": 0.9,
  "reason": "Test"
}
```

Hope this helps!"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            assert result.has_waste is True
            assert result.confidence == 0.9

        await validator.close()

    @pytest.mark.asyncio
    async def test_parse_plain_markdown_block(self):
        """Test parsing JSON inside plain markdown code blocks (no json tag)."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """```
{
  "has_waste": false,
  "confidence": 0.85,
  "reason": "No waste found"
}
```"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            assert result.has_waste is False
            assert result.confidence == 0.85

        await validator.close()

    @pytest.mark.asyncio
    async def test_parse_invalid_json_uses_fallback(self):
        """Test that invalid JSON triggers fallback (has_waste=True for safety)."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "This is not valid JSON at all"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            # Fallback behavior: assume waste for safety
            assert result.has_waste is True
            assert result.confidence == 0.5
            assert "Error parsing response" in result.reason

        await validator.close()

    @pytest.mark.asyncio
    async def test_parse_missing_fields_uses_fallback(self):
        """Test that missing required fields trigger fallback."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        # Missing 'reason' field
        mock_message.content = """{
  "has_waste": true,
  "confidence": 0.9
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch.object(
            validator.client.chat.completions, "create", mock_create
        ):
            result = await validator.validate(b"fake_image_data", trace_id)

            # Fallback behavior
            assert result.has_waste is True
            assert result.confidence == 0.5

        await validator.close()


class TestPreValidatorLogging:
    """Test PreValidator logging behavior."""

    @pytest.mark.asyncio
    async def test_logging_on_success(self):
        """Test that logs are emitted on successful validation."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": true,
  "confidence": 0.95,
  "reason": "Botella detectada"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch("app.agents.pre_validator.logger") as mock_logger:
            with patch.object(
                validator.client.chat.completions, "create", mock_create
            ):
                await validator.validate(b"fake_image_data", trace_id)

                # Check pre_validator_started log
                mock_logger.info.assert_any_call(
                    "pre_validator_started",
                    trace_id=trace_id,
                    agent="PreValidator",
                    model="gpt-4o-mini",
                    timeout_ms=2000.0,
                )

                # Check pre_validator_complete log
                mock_logger.info.assert_any_call(
                    "pre_validator_complete",
                    trace_id=trace_id,
                    agent="PreValidator",
                    has_waste=True,
                    confidence=0.95,
                    reason="Botella detectada",
                )

        await validator.close()

    @pytest.mark.asyncio
    async def test_logging_on_timeout(self):
        """Test that error log is emitted on timeout."""
        validator = PreValidator(timeout=0.1)
        trace_id = str(uuid4())

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.5)
            return Mock()

        mock_create = AsyncMock(side_effect=slow_response)

        with patch("app.agents.pre_validator.logger") as mock_logger:
            with patch.object(
                validator.client.chat.completions, "create", mock_create
            ):
                with pytest.raises(TimeoutError):
                    await validator.validate(b"fake_image_data", trace_id)

                # Check error log
                mock_logger.error.assert_any_call(
                    "pre_validator_timeout",
                    trace_id=trace_id,
                    agent="PreValidator",
                    timeout_ms=100.0,
                )

        await validator.close()

    @pytest.mark.asyncio
    async def test_logging_on_api_error(self):
        """Test that error log is emitted on API failure."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_create = AsyncMock(side_effect=Exception("API error"))

        with patch("app.agents.pre_validator.logger") as mock_logger:
            with patch.object(
                validator.client.chat.completions, "create", mock_create
            ):
                with pytest.raises(ValueError):
                    await validator.validate(b"fake_image_data", trace_id)

                # Check error log
                error_calls = [
                    call
                    for call in mock_logger.error.call_args_list
                    if call[0][0] == "pre_validator_error"
                ]
                assert len(error_calls) > 0

        await validator.close()

    @pytest.mark.asyncio
    async def test_logging_on_parse_error(self):
        """Test that warning log is emitted on parse error."""
        validator = PreValidator(timeout=2.0)
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Invalid JSON"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_create = AsyncMock(return_value=mock_response)

        with patch("app.agents.pre_validator.logger") as mock_logger:
            with patch.object(
                validator.client.chat.completions, "create", mock_create
            ):
                await validator.validate(b"fake_image_data", trace_id)

                # Check warning log for parse error
                warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if call[0][0] == "pre_validator_parse_error"
                ]
                assert len(warning_calls) > 0

        await validator.close()


class TestPreValidatorContextManager:
    """Test PreValidator async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test PreValidator can be used as async context manager."""
        trace_id = str(uuid4())

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = """{
  "has_waste": true,
  "confidence": 0.9,
  "reason": "Test"
}"""
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        async with PreValidator(timeout=2.0) as validator:
            mock_create = AsyncMock(return_value=mock_response)

            with patch.object(
                validator.client.chat.completions, "create", mock_create
            ):
                result = await validator.validate(b"fake_image_data", trace_id)

                assert result.has_waste is True


class TestPreValidatorConfiguration:
    """Test PreValidator configuration."""

    @pytest.mark.asyncio
    async def test_uses_gpt4o_mini_model(self):
        """Test that PreValidator uses gpt-4o-mini model."""
        validator = PreValidator()

        assert validator.model == "gpt-4o-mini"

        await validator.close()

    @pytest.mark.asyncio
    async def test_default_timeout_is_500ms(self):
        """Test that default timeout is 500ms."""
        validator = PreValidator()

        assert validator.timeout == 0.5

        await validator.close()


class TestLegacyFunction:
    """Test legacy validate_payload function."""

    def test_validate_payload_returns_true(self):
        """Test that legacy function returns True for non-empty payload."""
        from app.agents.pre_validator import validate_payload

        payload = {"key": "value"}
        result = validate_payload(payload)

        assert result is True

    def test_validate_payload_returns_false(self):
        """Test that legacy function returns False for empty payload."""
        from app.agents.pre_validator import validate_payload

        payload = {}
        result = validate_payload(payload)

        assert result is False
