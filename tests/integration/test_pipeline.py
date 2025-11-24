"""Integration tests for Pipeline Orchestrator V4.

Tests the complete pipeline flow including all 6 agents:
1. MaterialClassifier
2. VolumeEstimator
3. Mapper
4. WasteTypeMapper
5. FeedbackCoach
6. Assembler

Note: Waste detection moved to client-side.
Plus BackendIntegration (post-response).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.orchestrator.pipeline import (
    BackendIntegration,
    ClassificationError,
    FeedbackCoach,
    Pipeline,
    ValidationError,
    VolumeEstimator,
)
from app.schemas.bin_color import BinColor
from app.schemas.classification import (
    ConditionField,
    Material,
    MaterialClassificationResult,
    MaterialField,
    PhysicalCondition,
    Recyclability,
    RecyclabilityField,
    SubtypeField,
    VolumeField,
    VolumeSource,
)
from app.schemas.requests import ClassifyRequestForm
from app.schemas.responses import ClassifyResponse


@pytest.fixture
def mock_request() -> ClassifyRequestForm:
    """Create a mock classification request with bytes."""
    return ClassifyRequestForm(
        scan_id=uuid4(),
        station_id="TEST-STATION-01",
        image_bytes=b"fake_plastic_bottle_image_data",
        tenant_id="test-tenant",
        trace_id=uuid4(),
        idempotency_key=uuid4(),
    )


@pytest.fixture
def mock_classification_result() -> MaterialClassificationResult:
    """Create a mock classification result (plastic bottle)."""
    from datetime import datetime

    return MaterialClassificationResult(
        material=MaterialField(material_type=Material.PLASTIC, confidence=0.89),
        subtype=SubtypeField(value="PET", recycling_code="#1", confidence=0.85),
        condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.90),
        volume=VolumeField(liters=0.5, source=VolumeSource.LABEL_READ, confidence=0.88),
        recyclability=RecyclabilityField(value=Recyclability.RECYCLABLE, confidence=0.92),
        reasoning="Plastic PET bottle with #1 recycling code, 500ml, clean condition",
        timestamp=datetime.now(),
        cost=0.010,
        model_used="gpt-4o",
        model_provider="openai",
        partial_success=False,
        metadata={},
    )


class TestVolumeEstimator:
    """Test VolumeEstimator agent."""

    def test_estimate_with_classifier_volume(self):
        """Test volume estimation when classifier provides volume."""
        estimator = VolumeEstimator()

        volume_ml, weight_g, method = estimator.estimate(
            material=Material.PLASTIC,
            volume_from_classifier=500.0,  # 500ml from classifier
            trace_id="test-trace",
        )

        assert volume_ml == 500.0
        assert weight_g == pytest.approx(15.0, rel=0.1)  # 500ml * 0.03 g/ml
        assert method == "classifier_volume"

    def test_estimate_with_lookup_fallback(self):
        """Test volume estimation with lookup fallback."""
        estimator = VolumeEstimator()

        volume_ml, weight_g, method = estimator.estimate(
            material=Material.METAL,
            volume_from_classifier=None,  # No volume from classifier
            trace_id="test-trace",
        )

        # Should use lookup defaults for METAL
        assert volume_ml == 355.0
        assert weight_g == 13.0
        assert method == "lookup_default"

    def test_estimate_all_materials(self):
        """Test volume estimation for all material types."""
        estimator = VolumeEstimator()

        materials = [
            Material.PLASTIC,
            Material.METAL,
            Material.GLASS,
            Material.PAPER,
            Material.CARDBOARD,
            Material.ORGANIC,
            Material.TETRAPAK,
            Material.OTHER,
        ]

        for material in materials:
            volume_ml, weight_g, method = estimator.estimate(
                material=material,
                volume_from_classifier=None,
                trace_id="test-trace",
            )

            # Should return valid values
            assert volume_ml >= 0
            assert weight_g >= 0
            assert method == "lookup_default"


class TestFeedbackCoach:
    """Test FeedbackCoach agent."""

    def test_generate_feedback_for_all_materials(self):
        """Test feedback generation for all material types."""
        coach = FeedbackCoach()

        materials = [
            Material.PLASTIC,
            Material.METAL,
            Material.GLASS,
            Material.PAPER,
            Material.CARDBOARD,
            Material.ORGANIC,
            Material.TETRAPAK,
            Material.OTHER,
        ]

        for material in materials:
            message = coach.generate(
                material=material,
                confidence=0.89,
                trace_id="test-trace",
            )

            # Should return valid message
            assert isinstance(message, str)
            assert len(message) > 0
            assert len(message) <= 240  # Response schema limit

    def test_message_truncation(self):
        """Test that long messages are truncated to 240 characters."""
        coach = FeedbackCoach()

        # Override message with a very long one
        coach.MESSAGES[Material.PLASTIC] = "A" * 300

        message = coach.generate(
            material=Material.PLASTIC,
            confidence=0.89,
            trace_id="test-trace",
        )

        assert len(message) <= 240


class TestBackendIntegration:
    """Test BackendIntegration agent."""

    @pytest.mark.asyncio
    async def test_send_classification(self, mock_request: ClassifyRequestForm):
        """Test sending classification to backend."""
        integration = BackendIntegration()

        # Create a mock response
        response = MagicMock(spec=ClassifyResponse)
        response.material = Material.PLASTIC
        response.confidence = 0.89
        response.waste_type_code = "PET_BOTTLE_500ML"
        response.volume_ml = 500.0
        response.weight_g = 15.0
        response.color = BinColor.WHITE

        result = await integration.send(
            response=response,
            request=mock_request,
            trace_id="test-trace",
        )

        # Should return result (currently placeholder)
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_send_with_backend_error(self, mock_request: ClassifyRequestForm):
        """Test backend integration with error (should not raise)."""
        integration = BackendIntegration()

        # Mock backend client to raise error
        integration.client.send_classification = MagicMock(
            side_effect=Exception("Backend unavailable")
        )

        response = MagicMock(spec=ClassifyResponse)
        response.material = Material.PLASTIC
        response.confidence = 0.89
        response.waste_type_code = "PET_BOTTLE_500ML"
        response.volume_ml = 500.0
        response.weight_g = 15.0
        response.color = BinColor.WHITE

        # Should return None on error (not raise)
        result = await integration.send(
            response=response,
            request=mock_request,
            trace_id="test-trace",
        )

        assert result is None


class TestPipeline:
    """Test Pipeline Orchestrator V4."""

    @pytest.mark.asyncio
    def test_pipeline_initialization(self):
        """Test that Pipeline initializes all 6 agents correctly."""
        pipeline = Pipeline()

        # Check all 6 agents are initialized (PreValidator moved to client-side)
        assert pipeline.classifier is not None
        assert pipeline.volume_estimator is not None
        assert pipeline.mapper is not None
        assert pipeline.waste_type_mapper is not None
        assert pipeline.feedback_coach is not None
        assert pipeline.assembler is not None
        assert pipeline.backend_integration is not None

        # Check classifier adapter initialized
        assert pipeline.classifier_adapter is not None

        # Check metrics collector initialized
        assert pipeline.metrics is not None

    @pytest.mark.asyncio
    async def test_pipeline_complete_flow(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test complete pipeline flow with all 6 agents."""
        pipeline = Pipeline()

        # Mock MaterialClassifier (no PreValidator needed - client-side validation)
        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification_result

            # Mock WasteTypeMapper initialization (to avoid backend call)
            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                # Execute pipeline
                response = await pipeline.process(mock_request)

                # Verify response structure
                assert isinstance(response, ClassifyResponse)
                assert response.material == Material.PLASTIC
                assert response.confidence == 0.89
                assert response.color == BinColor.WHITE
                assert response.volume_ml > 0
                assert response.weight_g > 0
                assert response.waste_type_code is not None
                assert len(response.message) > 0

                # Verify meta
                assert response.meta.latency_ms >= 0  # Can be 0 with mocks
                assert response.meta.cost_usd > 0
                assert response.meta.input_format == "bytes"
                assert len(response.meta.agents_executed) == 5  # 5 processing agents (Assembler not included in list)

                # Verify all 5 processing agents executed (PreValidator moved to client-side)
                # Note: Assembler is not included in agents_executed list
                expected_agents = [
                    "MaterialClassifier",
                    "VolumeEstimator",
                    "Mapper",
                    "WasteTypeMapper",
                    "FeedbackCoach",
                ]
                for agent in expected_agents:
                    assert agent in response.meta.agents_executed

    @pytest.mark.asyncio
    async def test_pipeline_low_confidence_classification(
        self,
        mock_request: ClassifyRequestForm,
    ):
        """Test pipeline with low confidence classification (downgrade to OTHER)."""
        pipeline = Pipeline()

        # Mock MaterialClassifier with low confidence (0.5 - between 0.3 and 0.6)
        low_conf_result = MaterialClassificationResult(
            material=MaterialField(material_type=Material.PLASTIC, confidence=0.5),
            subtype=SubtypeField(value="PET", recycling_code="#1", confidence=0.4),
            condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.6),
            volume=VolumeField(liters=0.5, source=VolumeSource.LABEL_READ, confidence=0.5),
            recyclability=RecyclabilityField(value=Recyclability.RECYCLABLE, confidence=0.6),
            reasoning="Low confidence classification",
            timestamp=MagicMock(),
            cost=0.010,
            model_used="gpt-4o",
            model_provider="openai",
            partial_success=False,
            metadata={},
        )

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = low_conf_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                # Execute pipeline - should downgrade to OTHER
                response = await pipeline.process(mock_request)

                # Material should be downgraded to OTHER (confidence < 0.6)
                assert response.material == Material.OTHER
                assert response.confidence == 0.5

    @pytest.mark.asyncio
    async def test_pipeline_very_low_confidence(
        self,
        mock_request: ClassifyRequestForm,
    ):
        """Test pipeline with very low confidence (<0.3)."""
        pipeline = Pipeline()

        # Create low-confidence classification result
        from datetime import datetime

        low_confidence_result = MaterialClassificationResult(
            material=MaterialField(
                material_type=Material.OTHER, confidence=0.25  # TOO LOW
            ),
            subtype=SubtypeField(value=None, recycling_code=None, confidence=0.2),
            condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.5),
            volume=VolumeField(liters=None, source=VolumeSource.ESTIMATED, confidence=0.3),
            recyclability=RecyclabilityField(
                value=Recyclability.RECYCLABLE, confidence=0.4
            ),
            reasoning="Low confidence due to poor image quality",
            timestamp=datetime.now(),
            cost=0.010,
            model_used="gpt-4o",
            model_provider="openai",
            partial_success=True,
            metadata={},
        )

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = low_confidence_result

            # Should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                await pipeline.process(mock_request)

            assert exc_info.value.error_code == "LOW_CONFIDENCE"
            assert "confianza" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_pipeline_no_waste_short_circuits(
        self,
        mock_request: ClassifyRequestForm,
    ):
        """Pipeline debe abortar si el clasificador devuelve NO_WASTE."""
        pipeline = Pipeline()

        from datetime import datetime

        no_waste_result = MaterialClassificationResult(
            material=MaterialField(material_type=Material.NO_WASTE, confidence=0.95),
            subtype=SubtypeField(value=None, recycling_code=None, confidence=0.0),
            condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.0),
            volume=VolumeField(liters=None, source=VolumeSource.ESTIMATED, confidence=0.0),
            recyclability=RecyclabilityField(value=Recyclability.NON_RECYCLABLE, confidence=0.0),
            reasoning="No waste detected in image",
            timestamp=datetime.now(),
            cost=0.010,
            model_used="gpt-4o",
            model_provider="openai",
            partial_success=False,
            metadata={},
        )

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = no_waste_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                with pytest.raises(ValidationError) as excinfo:
                    await pipeline.process(mock_request)

        assert excinfo.value.error_code == "NO_WASTE_DETECTED"

    @pytest.mark.asyncio
    async def test_pipeline_medium_confidence_downgrades_to_other(
        self,
        mock_request: ClassifyRequestForm,
    ):
        """Test pipeline with medium confidence (0.3-0.6) downgrades to OTHER."""
        pipeline = Pipeline()

        # Create medium-confidence classification result
        from datetime import datetime

        medium_confidence_result = MaterialClassificationResult(
            material=MaterialField(
                material_type=Material.PLASTIC, confidence=0.45  # Medium
            ),
            subtype=SubtypeField(value="PET", recycling_code="#1", confidence=0.5),
            condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.6),
            volume=VolumeField(liters=0.5, source=VolumeSource.ESTIMATED, confidence=0.5),
            recyclability=RecyclabilityField(
                value=Recyclability.RECYCLABLE, confidence=0.6
            ),
            reasoning="Medium confidence",
            timestamp=datetime.now(),
            cost=0.010,
            model_used="gpt-4o",
            model_provider="openai",
            partial_success=False,
            metadata={},
        )

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = medium_confidence_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                response = await pipeline.process(mock_request)

                # Should downgrade to OTHER
                assert response.material == Material.OTHER
                assert response.confidence == 0.45

    @pytest.mark.asyncio
    async def test_pipeline_timeout(
        self,
        mock_request: ClassifyRequestForm,
    ):
        """Test pipeline timeout (5 seconds)."""
        pipeline = Pipeline()

        # Mock PreValidator to take forever
        # Mock MaterialClassifier to take forever
        async def slow_classify(*args: Any, **kwargs: Any) -> MaterialClassificationResult:
            await asyncio.sleep(10)  # Exceed 5s timeout
            return mock_classification_result

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.side_effect = slow_classify

            # Should raise TimeoutError
            with pytest.raises(TimeoutError) as exc_info:
                await pipeline.process(mock_request)

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_pipeline_trace_id_propagation(
        self,
        mock_request: ClassifyRequestForm,
        mock_classification_result: MaterialClassificationResult,
    ):
        """Test that trace_id is propagated to all agents."""
        pipeline = Pipeline()

        trace_id = str(mock_request.trace_id)

        with patch.object(
            pipeline.classifier, "classify", new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification_result

            with patch.object(
                pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
            ):
                await pipeline.process(mock_request)

                # Verify trace_id passed to classifier
                mock_classify.assert_called_once()
                call_args = mock_classify.call_args
                assert trace_id in str(call_args)

    @pytest.mark.asyncio
    async def test_pipeline_with_all_materials(
        self,
        mock_request: ClassifyRequestForm,
    ):
        """Test pipeline with each material type."""
        from datetime import datetime

        materials = [
            Material.PLASTIC,
            Material.METAL,
            Material.GLASS,
            Material.PAPER,
            Material.CARDBOARD,
            Material.ORGANIC,
            Material.TETRAPAK,
            Material.OTHER,
        ]

        for material in materials:
            pipeline = Pipeline()

            # Create classification result for this material
            classification_result = MaterialClassificationResult(
                material=MaterialField(material_type=material, confidence=0.89),
                subtype=SubtypeField(value=None, recycling_code=None, confidence=0.7),
                condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.8),
                volume=VolumeField(
                    liters=0.5, source=VolumeSource.ESTIMATED, confidence=0.7
                ),
                recyclability=RecyclabilityField(
                    value=Recyclability.RECYCLABLE, confidence=0.8
                ),
                reasoning=f"Classification for {material.value}",
                timestamp=datetime.now(),
                cost=0.010,
                model_used="gpt-4o",
                model_provider="openai",
                partial_success=False,
                metadata={},
            )

            with patch.object(
                pipeline.classifier, "classify", new_callable=AsyncMock
            ) as mock_classify:
                mock_classify.return_value = classification_result

                with patch.object(
                    pipeline.waste_type_mapper, "initialize", new_callable=AsyncMock
                ):
                    response = await pipeline.process(mock_request)

                    # Verify correct material
                    assert response.material == material
                    assert response.confidence == 0.89

                # Verify correct bin color
                if material == Material.ORGANIC:
                    assert response.color == BinColor.GREEN
                elif material == Material.OTHER:
                    assert response.color == BinColor.BLACK
                else:
                    assert response.color == BinColor.WHITE

    @pytest.mark.asyncio
    async def test_pipeline_cost_calculation(self):
        """Test pipeline cost calculation."""
        pipeline = Pipeline()

        cost = pipeline._calculate_total_cost()

        # V4 cost should be MaterialClassifier only (PreValidator moved to client-side)
        # = $0.010
        assert cost == pytest.approx(0.010, rel=0.01)
        assert cost < 0.012  # Within reasonable bounds

    @pytest.mark.asyncio
    async def test_pipeline_with_invalid_input(self):
        """Test pipeline with invalid input."""
        pipeline = Pipeline()

        # Create request without image data
        invalid_request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-STATION-01",
            image_bytes=None,
            tenant_id="test-tenant",
            trace_id=uuid4(),
            idempotency_key=uuid4(),
        )

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await pipeline.process(invalid_request)

        assert exc_info.value.error_code == "INVALID_INPUT"
