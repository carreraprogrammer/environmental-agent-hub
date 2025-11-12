"""
Unit tests for Classifier Agent.

Tests cover:
- High confidence classification (>0.6) → Use classified material
- Medium confidence classification (0.3-0.6) → Map to OTHER
- Low confidence classification (<0.3) → Raise ValueError
- Different materials (PLASTIC, PAPER, GLASS, METAL, ORGANIC, OTHER)
- Adapter failures and error handling
- Logging verification
- Threshold configuration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.agents.classifier import Classifier
from app.schemas.domain import ClassificationResult, WasteMaterial


class TestClassificationResultSchema:
    """Test ClassificationResult schema."""

    def test_classification_result_valid(self):
        """Test ClassificationResult with valid data."""
        result = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.95,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Botella de plástico transparente",
        )

        assert result.material == WasteMaterial.PLASTIC
        assert result.confidence == 0.95
        assert result.model_used == "openai/gpt-4o"
        assert result.model_provider == "openai"
        assert result.reasoning == "Botella de plástico transparente"

    def test_classification_result_all_materials(self):
        """Test ClassificationResult with all material types."""
        materials = [
            WasteMaterial.PLASTIC,
            WasteMaterial.PAPER,
            WasteMaterial.GLASS,
            WasteMaterial.METAL,
            WasteMaterial.ORGANIC,
            WasteMaterial.OTHER,
        ]

        for material in materials:
            result = ClassificationResult(
                material=material,
                confidence=0.9,
                model_used="test/model",
                model_provider="test",
            )
            assert result.material == material

    def test_classification_result_as_dict(self):
        """Test ClassificationResult.as_dict() includes reasoning."""
        result = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.85,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Test reasoning",
        )

        result_dict = result.as_dict()

        assert result_dict["material"] == "PLASTIC"
        assert result_dict["confidence"] == 0.85
        assert result_dict["model_used"] == "openai/gpt-4o"
        assert result_dict["model_provider"] == "openai"
        assert result_dict["reasoning"] == "Test reasoning"


class TestClassifierHighConfidence:
    """Test Classifier with high confidence (>0.6)."""

    @pytest.mark.asyncio
    async def test_classify_plastic_high_confidence(self):
        """Test successful PLASTIC classification with high confidence."""
        classifier = Classifier()
        trace_id = str(uuid4())

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.89,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Botella de plástico transparente",
        )

        result = await classifier.classify(
            "https://example.com/bottle.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.PLASTIC
        assert result.confidence == 0.89
        assert result.reasoning == "Botella de plástico transparente"
        mock_adapter.classify.assert_called_once_with(
            "https://example.com/bottle.jpg", trace_id=trace_id
        )

    @pytest.mark.asyncio
    async def test_classify_paper_high_confidence(self):
        """Test successful PAPER classification with high confidence."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PAPER,
            confidence=0.92,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Caja de cartón corrugado",
        )

        result = await classifier.classify(
            "https://example.com/cardboard.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.PAPER
        assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_classify_glass_high_confidence(self):
        """Test successful GLASS classification with high confidence."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.GLASS,
            confidence=0.95,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Botella de vidrio verde",
        )

        result = await classifier.classify(
            "https://example.com/glass.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.GLASS
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_classify_metal_high_confidence(self):
        """Test successful METAL classification with high confidence."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.METAL,
            confidence=0.88,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Lata de aluminio",
        )

        result = await classifier.classify(
            "https://example.com/can.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.METAL
        assert result.confidence == 0.88

    @pytest.mark.asyncio
    async def test_classify_organic_high_confidence(self):
        """Test successful ORGANIC classification with high confidence."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.ORGANIC,
            confidence=0.87,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Restos de comida",
        )

        result = await classifier.classify(
            "https://example.com/food.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.ORGANIC
        assert result.confidence == 0.87


class TestClassifierMediumConfidence:
    """Test Classifier with medium confidence (0.3-0.6) → Maps to OTHER."""

    @pytest.mark.asyncio
    async def test_classify_medium_confidence_maps_to_other(self):
        """Test that medium confidence (0.45) maps to OTHER."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.45,  # Medium confidence
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Objeto parcialmente visible",
        )

        result = await classifier.classify(
            "https://example.com/unclear.jpg", mock_adapter, trace_id
        )

        # Should be mapped to OTHER
        assert result.material == WasteMaterial.OTHER
        assert result.confidence == 0.45  # Confidence preserved
        assert result.reasoning == "Objeto parcialmente visible"  # Reasoning preserved

    @pytest.mark.asyncio
    async def test_classify_medium_confidence_boundary_low(self):
        """Test medium confidence at lower boundary (0.3)."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PAPER,
            confidence=0.3,  # Exactly at lower threshold
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Imagen borrosa",
        )

        result = await classifier.classify(
            "https://example.com/blurry.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.OTHER
        assert result.confidence == 0.3

    @pytest.mark.asyncio
    async def test_classify_medium_confidence_boundary_high(self):
        """Test medium confidence just below upper boundary (0.59)."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.METAL,
            confidence=0.59,  # Just below 0.6
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="No estoy completamente seguro",
        )

        result = await classifier.classify(
            "https://example.com/unsure.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.OTHER
        assert result.confidence == 0.59

    @pytest.mark.asyncio
    async def test_classify_high_confidence_boundary(self):
        """Test that exactly 0.6 confidence uses classified material."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.GLASS,
            confidence=0.6,  # Exactly at threshold
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Botella de vidrio",
        )

        result = await classifier.classify(
            "https://example.com/glass.jpg", mock_adapter, trace_id
        )

        # Should NOT be mapped to OTHER (>= 0.6)
        assert result.material == WasteMaterial.GLASS
        assert result.confidence == 0.6


class TestClassifierLowConfidence:
    """Test Classifier with low confidence (<0.3) → Raises ValueError."""

    @pytest.mark.asyncio
    async def test_classify_low_confidence_raises_error(self):
        """Test that low confidence (<0.3) raises ValueError."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.2,  # Too low
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Imagen muy borrosa",
        )

        with pytest.raises(ValueError, match="Confidence too low"):
            await classifier.classify(
                "https://example.com/blurry.jpg", mock_adapter, trace_id
            )

    @pytest.mark.asyncio
    async def test_classify_very_low_confidence_raises_error(self):
        """Test that very low confidence (0.05) raises ValueError."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.OTHER,
            confidence=0.05,  # Very low
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="No puedo determinar",
        )

        with pytest.raises(ValueError, match="Confidence too low: 0.05 < 0.30"):
            await classifier.classify(
                "https://example.com/unclear.jpg", mock_adapter, trace_id
            )

    @pytest.mark.asyncio
    async def test_classify_zero_confidence_raises_error(self):
        """Test that zero confidence raises ValueError."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.OTHER,
            confidence=0.0,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Completamente incierto",
        )

        with pytest.raises(ValueError, match="Confidence too low"):
            await classifier.classify(
                "https://example.com/unknown.jpg", mock_adapter, trace_id
            )


class TestClassifierAdapterErrors:
    """Test Classifier error handling when adapter fails."""

    @pytest.mark.asyncio
    async def test_classify_adapter_timeout_raises_error(self):
        """Test that adapter timeout raises ValueError."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.side_effect = TimeoutError("OpenAI timeout")

        with pytest.raises(ValueError, match="Classification failed"):
            await classifier.classify(
                "https://example.com/image.jpg", mock_adapter, trace_id
            )

    @pytest.mark.asyncio
    async def test_classify_adapter_api_error_raises_error(self):
        """Test that adapter API error raises ValueError."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(ValueError, match="Classification failed"):
            await classifier.classify(
                "https://example.com/image.jpg", mock_adapter, trace_id
            )

    @pytest.mark.asyncio
    async def test_classify_adapter_invalid_response_raises_error(self):
        """Test that invalid adapter response raises ValueError."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.side_effect = ValueError("Invalid response format")

        with pytest.raises(ValueError, match="Classification failed"):
            await classifier.classify(
                "https://example.com/image.jpg", mock_adapter, trace_id
            )


class TestClassifierLogging:
    """Test Classifier logging behavior."""

    @pytest.mark.asyncio
    async def test_logging_on_success(self):
        """Test that logs are emitted on successful classification."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.95,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Botella de plástico",
        )

        with patch("app.agents.classifier.logger") as mock_logger:
            await classifier.classify(
                "https://example.com/bottle.jpg", mock_adapter, trace_id
            )

            # Check classifier_started log
            mock_logger.info.assert_any_call(
                "classifier_started",
                trace_id=trace_id,
                agent="Classifier",
                model="openai/gpt-4o",
                provider="openai",
            )

            # Check classifier_complete log
            mock_logger.info.assert_any_call(
                "classifier_complete",
                trace_id=trace_id,
                agent="Classifier",
                material="PLASTIC",
                confidence=0.95,
                model="openai/gpt-4o",
            )

    @pytest.mark.asyncio
    async def test_logging_on_medium_confidence(self):
        """Test that info log is emitted when mapping to OTHER."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.45,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Objeto parcialmente visible",
        )

        with patch("app.agents.classifier.logger") as mock_logger:
            await classifier.classify(
                "https://example.com/unclear.jpg", mock_adapter, trace_id
            )

            # Check classifier_medium_confidence_mapped_to_other log
            mock_logger.info.assert_any_call(
                "classifier_medium_confidence_mapped_to_other",
                trace_id=trace_id,
                agent="Classifier",
                original_material="PLASTIC",
                confidence=0.45,
                threshold=0.6,
            )

    @pytest.mark.asyncio
    async def test_logging_on_low_confidence(self):
        """Test that warning log is emitted on low confidence."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.2,
            model_used="openai/gpt-4o",
            model_provider="openai",
            reasoning="Muy borroso",
        )

        with patch("app.agents.classifier.logger") as mock_logger:
            with pytest.raises(ValueError):
                await classifier.classify(
                    "https://example.com/blurry.jpg", mock_adapter, trace_id
                )

            # Check classifier_low_confidence warning log
            mock_logger.warning.assert_any_call(
                "classifier_low_confidence",
                trace_id=trace_id,
                agent="Classifier",
                confidence=0.2,
                threshold=0.3,
                material="PLASTIC",
            )

    @pytest.mark.asyncio
    async def test_logging_on_adapter_error(self):
        """Test that error log is emitted on adapter failure."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "openai/gpt-4o"
        mock_adapter.model_provider = "openai"
        mock_adapter.classify.side_effect = Exception("API error")

        with patch("app.agents.classifier.logger") as mock_logger:
            with pytest.raises(ValueError):
                await classifier.classify(
                    "https://example.com/image.jpg", mock_adapter, trace_id
                )

            # Check classifier_error log
            error_calls = [
                call
                for call in mock_logger.error.call_args_list
                if call[0][0] == "classifier_error"
            ]
            assert len(error_calls) > 0


class TestClassifierConfiguration:
    """Test Classifier threshold configuration."""

    @pytest.mark.asyncio
    async def test_custom_threshold_low(self):
        """Test custom low threshold (0.4)."""
        classifier = Classifier(confidence_threshold_low=0.4)
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "test/model"
        mock_adapter.model_provider = "test"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.35,  # Below custom threshold
            model_used="test/model",
            model_provider="test",
        )

        with pytest.raises(ValueError, match="Confidence too low: 0.35 < 0.40"):
            await classifier.classify("https://example.com/image.jpg", mock_adapter, trace_id)

    @pytest.mark.asyncio
    async def test_custom_threshold_medium(self):
        """Test custom medium threshold (0.7)."""
        classifier = Classifier(confidence_threshold_medium=0.7)
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "test/model"
        mock_adapter.model_provider = "test"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PLASTIC,
            confidence=0.65,  # Below custom medium threshold
            model_used="test/model",
            model_provider="test",
        )

        result = await classifier.classify("https://example.com/image.jpg", mock_adapter, trace_id)

        # Should be mapped to OTHER with custom threshold
        assert result.material == WasteMaterial.OTHER
        assert result.confidence == 0.65

    @pytest.mark.asyncio
    async def test_default_thresholds(self):
        """Test that default thresholds are 0.3 and 0.6."""
        classifier = Classifier()

        assert classifier.confidence_threshold_low == 0.3
        assert classifier.confidence_threshold_medium == 0.6


class TestClassifierMultipleProviders:
    """Test Classifier with different model providers."""

    @pytest.mark.asyncio
    async def test_classify_with_claude_adapter(self):
        """Test classification with Claude adapter."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "anthropic/claude-3-sonnet"
        mock_adapter.model_provider = "anthropic"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.PAPER,
            confidence=0.87,
            model_used="anthropic/claude-3-sonnet",
            model_provider="anthropic",
            reasoning="Caja de cartón",
        )

        result = await classifier.classify(
            "https://example.com/box.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.PAPER
        assert result.confidence == 0.87

    @pytest.mark.asyncio
    async def test_classify_with_roboflow_adapter(self):
        """Test classification with Roboflow adapter."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "roboflow/waste-classifier"
        mock_adapter.model_provider = "roboflow"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.METAL,
            confidence=0.93,
            model_used="roboflow/waste-classifier",
            model_provider="roboflow",
            reasoning="Lata de aluminio detectada",
        )

        result = await classifier.classify(
            "https://example.com/can.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.METAL
        assert result.confidence == 0.93

    @pytest.mark.asyncio
    async def test_classify_with_gemini_adapter(self):
        """Test classification with Gemini adapter."""
        classifier = Classifier()
        trace_id = str(uuid4())

        mock_adapter = AsyncMock()
        mock_adapter.model_name = "google/gemini-pro-vision"
        mock_adapter.model_provider = "google"
        mock_adapter.classify.return_value = ClassificationResult(
            material=WasteMaterial.GLASS,
            confidence=0.91,
            model_used="google/gemini-pro-vision",
            model_provider="google",
            reasoning="Botella de vidrio",
        )

        result = await classifier.classify(
            "https://example.com/glass.jpg", mock_adapter, trace_id
        )

        assert result.material == WasteMaterial.GLASS
        assert result.confidence == 0.91
