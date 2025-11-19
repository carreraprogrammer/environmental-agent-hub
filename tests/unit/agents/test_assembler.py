"""
Unit tests for Assembler agent.

Tests cover:
- Response construction with all fields
- Characteristics handling (None and populated)
- Pydantic validation
- Latency calculation
- ResponseMeta construction
- All material types
- Logging behavior
"""

from __future__ import annotations

import inspect
import time
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.agents.assembler import Assembler
from app.schemas.bin_color import BinColor
from app.schemas.classification import Material
from app.schemas.responses import ClassifyResponse


class TestBasicConstruction:
    """Test basic response construction."""

    def test_build_response_returns_classify_response(self) -> None:
        """Test that build_response returns a ClassifyResponse instance."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics={"material_specific": "PET"},
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great job recycling!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=["router", "prevalidator", "classifier"],
        )

        assert isinstance(response, ClassifyResponse)

    def test_build_response_sets_all_fields(self) -> None:
        """Test that build_response sets all fields correctly."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics={"material_specific": "PET", "container_type": "bottle"},
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great job recycling!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=["router", "prevalidator", "classifier"],
        )

        assert response.material == Material.PLASTIC
        assert response.confidence == 0.89
        assert response.color == BinColor.WHITE
        assert response.volume_ml == 520.0
        assert response.weight_g == 15.2
        assert response.waste_type_code == "PET_BOTTLE_500ML"
        assert response.message == "Great job recycling!"
        assert response.characteristics == {
            "material_specific": "PET",
            "container_type": "bottle",
        }


class TestCharacteristics:
    """Test characteristics handling."""

    def test_characteristics_none_is_handled(self) -> None:
        """Test that None characteristics are handled correctly."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.ORGANIC,
            confidence=0.75,
            characteristics=None,
            volume_ml=0.0,
            weight_g=100.0,
            estimation_method="fallback",
            color=BinColor.GREEN,
            waste_type_code="FOOD_WASTE",
            message="Good composting!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.characteristics is None

    def test_characteristics_empty_dict_is_none(self) -> None:
        """Test that empty dict characteristics become None."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.METAL,
            confidence=0.92,
            characteristics={},
            volume_ml=355.0,
            weight_g=15.0,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="ALUMINUM_CAN",
            message="Metal recycling!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.characteristics is None

    def test_characteristics_with_values_is_preserved(self) -> None:
        """Test that characteristics with values are preserved."""
        assembler = Assembler()
        chars = {"material_specific": "PET", "size": "standard", "label": "Coca-Cola"}

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=chars,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.characteristics == chars


class TestResponseMeta:
    """Test ResponseMeta construction."""

    def test_response_meta_has_all_fields(self) -> None:
        """Test that ResponseMeta contains all required fields."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.GLASS,
            confidence=0.95,
            characteristics=None,
            volume_ml=330.0,
            weight_g=200.0,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="GLASS_BOTTLE_CLEAR",
            message="Glass recycling!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="url",
            agents_executed=["router", "prevalidator", "classifier", "mapper"],
        )

        meta = response.meta
        assert meta.model_used == "openai/gpt-4o"
        assert meta.model_provider == "openai"
        assert meta.cost_usd == 0.0122
        assert meta.validator_passed is True
        assert meta.estimation_method == "lookup"
        assert meta.input_format == "url"
        assert meta.s3_upload_status == "pending"
        assert meta.agents_executed == [
            "router",
            "prevalidator",
            "classifier",
            "mapper",
        ]
        assert meta.backend_integration is False

    def test_latency_ms_is_calculated(self) -> None:
        """Test that latency_ms is calculated from start_time."""
        assembler = Assembler()

        start = time.time()
        time.sleep(0.1)  # 100ms

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=start,
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        # Should be at least 100ms
        assert response.meta.latency_ms >= 100

    def test_latency_ms_is_integer(self) -> None:
        """Test that latency_ms is an integer."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert isinstance(response.meta.latency_ms, int)


class TestPydanticValidation:
    """Test Pydantic validation."""

    def test_invalid_confidence_above_one(self) -> None:
        """Test that confidence > 1.0 raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=1.5,  # Invalid
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "confidence" in str(exc_info.value)

    def test_invalid_confidence_below_zero(self) -> None:
        """Test that confidence < 0.0 raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=-0.1,  # Invalid
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "confidence" in str(exc_info.value)

    def test_invalid_volume_negative(self) -> None:
        """Test that negative volume raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=-100.0,  # Invalid
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "volume_ml" in str(exc_info.value)

    def test_invalid_weight_negative(self) -> None:
        """Test that negative weight raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=-10.0,  # Invalid
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "weight_g" in str(exc_info.value)

    def test_invalid_waste_type_code_empty(self) -> None:
        """Test that empty waste_type_code raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="",  # Invalid
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "waste_type_code" in str(exc_info.value)

    def test_invalid_message_empty(self) -> None:
        """Test that empty message raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="",  # Invalid
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "message" in str(exc_info.value)

    def test_invalid_message_too_long(self) -> None:
        """Test that message > 240 chars raises ValidationError."""
        assembler = Assembler()

        with pytest.raises(ValidationError) as exc_info:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="x" * 241,  # Invalid - too long
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

        assert "message" in str(exc_info.value)

    def test_valid_confidence_boundaries(self) -> None:
        """Test that confidence at boundaries (0.0 and 1.0) is valid."""
        assembler = Assembler()

        # Test 0.0
        response1 = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.0,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )
        assert response1.confidence == 0.0

        # Test 1.0
        response2 = assembler.build_response(
            material=Material.PLASTIC,
            confidence=1.0,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )
        assert response2.confidence == 1.0


class TestAllMaterials:
    """Test all material types."""

    @pytest.mark.parametrize(
        "material,color,waste_type_code",
        [
            (Material.PLASTIC, BinColor.WHITE, "PET_BOTTLE_500ML"),
            (Material.METAL, BinColor.WHITE, "ALUMINUM_CAN"),
            (Material.GLASS, BinColor.WHITE, "GLASS_BOTTLE_CLEAR"),
            (Material.PAPER, BinColor.BLUE, "PAPER_WHITE_A4"),
            (Material.CARDBOARD, BinColor.BLUE, "CARDBOARD_BOX"),
            (Material.ORGANIC, BinColor.GREEN, "FOOD_WASTE"),
            (Material.TETRAPAK, BinColor.WHITE, "PLASTIC_OTHER"),
            (Material.OTHER, BinColor.BLACK, "PLASTIC_OTHER"),
        ],
    )
    def test_all_materials_build_successfully(
        self, material: Material, color: BinColor, waste_type_code: str
    ) -> None:
        """Test that all material types build valid responses."""
        assembler = Assembler()

        response = assembler.build_response(
            material=material,
            confidence=0.85,
            characteristics=None,
            volume_ml=500.0,
            weight_g=50.0,
            estimation_method="lookup",
            color=color,
            waste_type_code=waste_type_code,
            message="Good recycling!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.material == material
        assert response.color == color
        assert response.waste_type_code == waste_type_code


class TestSynchronous:
    """Test that method is synchronous."""

    def test_build_response_is_not_coroutine(self) -> None:
        """Test that build_response is not an async coroutine."""
        assembler = Assembler()
        assert not inspect.iscoroutinefunction(assembler.build_response)

    def test_build_response_returns_immediately(self) -> None:
        """Test that build_response returns result immediately, not a coroutine."""
        assembler = Assembler()

        result = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        # Result should be ClassifyResponse, not a coroutine
        assert isinstance(result, ClassifyResponse)
        assert not inspect.iscoroutine(result)


class TestLogging:
    """Test logging behavior."""

    def test_logs_assembler_started(self) -> None:
        """Test that assembler_started event is logged."""
        assembler = Assembler()

        with patch("app.agents.assembler.logger") as mock_logger:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace-123",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

            mock_logger.info.assert_any_call(
                "assembler_started",
                trace_id="test-trace-123",
                agent="Assembler",
            )

    def test_logs_assembler_complete(self) -> None:
        """Test that assembler_complete event is logged."""
        assembler = Assembler()

        with patch("app.agents.assembler.logger") as mock_logger:
            assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace-456",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format="bytes",
                agents_executed=[],
            )

            # Find the assembler_complete call
            calls = mock_logger.info.call_args_list
            complete_call = None
            for call in calls:
                if call[0][0] == "assembler_complete":
                    complete_call = call
                    break

            assert complete_call is not None
            assert complete_call[1]["trace_id"] == "test-trace-456"
            assert complete_call[1]["agent"] == "Assembler"
            assert "latency_ms" in complete_call[1]
            assert "cost_usd" in complete_call[1]


class TestEnvironmentalImpact:
    """Test environmental impact handling."""

    def test_environmental_impact_is_none_by_default(self) -> None:
        """Test that environmental_impact is None by default."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.environmental_impact is None


class TestEdgeCases:
    """Test edge cases."""

    def test_zero_volume_and_weight(self) -> None:
        """Test that zero volume and weight are valid."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.ORGANIC,
            confidence=0.75,
            characteristics=None,
            volume_ml=0.0,
            weight_g=0.0,
            estimation_method="fallback",
            color=BinColor.GREEN,
            waste_type_code="FOOD_WASTE",
            message="Composting!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.volume_ml == 0.0
        assert response.weight_g == 0.0

    def test_empty_agents_executed(self) -> None:
        """Test that empty agents_executed list is valid."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert response.meta.agents_executed == []

    def test_long_agents_executed_list(self) -> None:
        """Test that long agents_executed list is valid."""
        assembler = Assembler()
        agents = [
            "router",
            "prevalidator",
            "classifier",
            "subtype_detector",
            "volume_estimator",
            "mapper",
            "waste_type_mapper",
            "feedback_coach",
            "assembler",
        ]

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="Great!",
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=agents,
        )

        assert response.meta.agents_executed == agents
        assert len(response.meta.agents_executed) == 9

    def test_message_at_max_length(self) -> None:
        """Test that message at exactly 240 chars is valid."""
        assembler = Assembler()

        response = assembler.build_response(
            material=Material.PLASTIC,
            confidence=0.89,
            characteristics=None,
            volume_ml=520.0,
            weight_g=15.2,
            estimation_method="lookup",
            color=BinColor.WHITE,
            waste_type_code="PET_BOTTLE_500ML",
            message="x" * 240,  # Exactly 240 chars
            model_used="openai/gpt-4o",
            model_provider="openai",
            trace_id="test-trace",
            start_time=time.time(),
            cost_usd=0.0122,
            input_format="bytes",
            agents_executed=[],
        )

        assert len(response.message) == 240

    def test_different_input_formats(self) -> None:
        """Test both input formats (bytes and url)."""
        assembler = Assembler()

        for input_format in ["bytes", "url"]:
            response = assembler.build_response(
                material=Material.PLASTIC,
                confidence=0.89,
                characteristics=None,
                volume_ml=520.0,
                weight_g=15.2,
                estimation_method="lookup",
                color=BinColor.WHITE,
                waste_type_code="PET_BOTTLE_500ML",
                message="Great!",
                model_used="openai/gpt-4o",
                model_provider="openai",
                trace_id="test-trace",
                start_time=time.time(),
                cost_usd=0.0122,
                input_format=input_format,
                agents_executed=[],
            )

            assert response.meta.input_format == input_format
