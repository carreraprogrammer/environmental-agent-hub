"""
Unit tests for Mapper Agent.

Tests cover:
- Material to color mapping for all materials
- Fallback behavior for unknown materials
- Logging verification
- Synchronous method verification (not async)

PHILOSOPHY: Simple direct mapping. Waste pickers handle cleaning.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

from app.agents.mapper import Mapper
from app.schemas.bin_color import BinColor
from app.schemas.classification import Material


class TestMaterialToColorMapping:
    """Test material to bin color mapping."""

    def test_plastic_maps_to_white(self):
        """Test PLASTIC material maps to WHITE bin."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.PLASTIC, "test-trace-001")
        assert color == BinColor.WHITE

    def test_glass_maps_to_white(self):
        """Test GLASS material maps to WHITE bin."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.GLASS, "test-trace-002")
        assert color == BinColor.WHITE

    def test_metal_maps_to_white(self):
        """Test METAL material maps to WHITE bin."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.METAL, "test-trace-003")
        assert color == BinColor.WHITE

    def test_tetrapak_maps_to_white(self):
        """Test TETRAPAK material maps to WHITE bin."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.TETRAPAK, "test-trace-004")
        assert color == BinColor.WHITE

    def test_paper_maps_to_white(self):
        """Test PAPER material maps to WHITE bin (university 3-color system)."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.PAPER, "test-trace-005")
        assert color == BinColor.WHITE

    def test_cardboard_maps_to_white(self):
        """Test CARDBOARD material maps to WHITE bin (university 3-color system)."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.CARDBOARD, "test-trace-006")
        assert color == BinColor.WHITE

    def test_organic_maps_to_green(self):
        """Test ORGANIC material maps to GREEN bin."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.ORGANIC, "test-trace-007")
        assert color == BinColor.GREEN

    def test_other_maps_to_black(self):
        """Test OTHER material maps to BLACK bin (university 3-color system)."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.OTHER, "test-trace-008")
        assert color == BinColor.BLACK


class TestAllMaterialsMapped:
    """Test that all materials have a mapping."""

    def test_all_materials_have_mapping(self):
        """Test that every Material enum value has a corresponding color mapping."""
        mapper = Mapper()

        for material in Material:
            # Should not raise exception
            color = mapper.map_to_color(material, f"test-trace-{material.value}")
            # Should return a valid BinColor
            assert isinstance(color, BinColor)
            # Color value should be a string
            assert isinstance(color.value, str)

    def test_mapping_dictionary_completeness(self):
        """Test that MATERIAL_TO_COLOR dict covers all Material values."""
        mapper = Mapper()

        # All materials should be in the dictionary
        for material in Material:
            assert material in mapper.MATERIAL_TO_COLOR, \
                f"Material {material.value} is not in MATERIAL_TO_COLOR"

    def test_mapping_is_deterministic(self):
        """Test that same material always maps to same color."""
        mapper = Mapper()

        for material in Material:
            first_result = mapper.map_to_color(material, "trace-1")
            second_result = mapper.map_to_color(material, "trace-2")
            assert first_result == second_result


class TestFallbackBehavior:
    """Test fallback behavior for unknown materials."""

    def test_fallback_to_black_for_unknown_material(self):
        """Test that .get() fallback returns BLACK for materials not in dict."""
        mapper = Mapper()

        # Create a mock Material that isn't in the dictionary
        # by temporarily removing a material from the dict
        original_dict = Mapper.MATERIAL_TO_COLOR.copy()

        # Remove PLASTIC from dict to simulate unknown material
        del Mapper.MATERIAL_TO_COLOR[Material.PLASTIC]

        try:
            color = mapper.map_to_color(Material.PLASTIC, "test-trace-fallback")
            assert color == BinColor.BLACK
        finally:
            # Restore the class-level dictionary
            Mapper.MATERIAL_TO_COLOR.clear()
            Mapper.MATERIAL_TO_COLOR.update(original_dict)

    def test_never_raises_exception(self):
        """Test that map_to_color never raises an exception for any input."""
        mapper = Mapper()

        # Should work for all Material values without exception
        for material in Material:
            try:
                color = mapper.map_to_color(material, "test-trace")
                assert color is not None
            except Exception as e:
                pytest.fail(f"map_to_color raised exception for {material}: {e}")


class TestSynchronousExecution:
    """Test that Mapper is synchronous (no async)."""

    def test_map_to_color_is_not_coroutine(self):
        """Test that map_to_color is not an async coroutine function."""
        mapper = Mapper()

        # Verify method is not a coroutine function
        assert not inspect.iscoroutinefunction(mapper.map_to_color), \
            "map_to_color should not be async"

    def test_can_call_without_await(self):
        """Test that map_to_color can be called directly without await."""
        mapper = Mapper()

        # Should be callable without await
        color = mapper.map_to_color(Material.PLASTIC, "test-trace")

        # Result should be BinColor, not a coroutine
        assert isinstance(color, BinColor)
        assert not inspect.iscoroutine(color)


class TestLogging:
    """Test Mapper logging behavior."""

    def test_logs_mapper_started(self):
        """Test that mapper_started log is emitted."""
        mapper = Mapper()

        with patch("app.agents.mapper.logger") as mock_logger:
            mapper.map_to_color(Material.PLASTIC, "test-trace-123")

            mock_logger.info.assert_any_call(
                "mapper_started",
                trace_id="test-trace-123",
                agent="Mapper",
                material="PLASTIC",
            )

    def test_logs_mapper_complete(self):
        """Test that mapper_complete log is emitted."""
        mapper = Mapper()

        with patch("app.agents.mapper.logger") as mock_logger:
            mapper.map_to_color(Material.PLASTIC, "test-trace-456")

            mock_logger.info.assert_any_call(
                "mapper_complete",
                trace_id="test-trace-456",
                material="PLASTIC",
                color="WHITE",
            )

    def test_logs_include_trace_id(self):
        """Test that all logs include trace_id."""
        mapper = Mapper()
        trace_id = "unique-trace-789"

        with patch("app.agents.mapper.logger") as mock_logger:
            mapper.map_to_color(Material.PAPER, trace_id)

            # Check all info calls include trace_id
            for call in mock_logger.info.call_args_list:
                kwargs = call[1]
                assert "trace_id" in kwargs
                assert kwargs["trace_id"] == trace_id

    def test_logs_correct_color_for_each_material(self):
        """Test that logs show correct color for each material."""
        mapper = Mapper()

        test_cases = [
            (Material.PLASTIC, "WHITE"),
            (Material.PAPER, "WHITE"),
            (Material.ORGANIC, "GREEN"),
            (Material.OTHER, "BLACK"),
        ]

        for material, expected_color in test_cases:
            with patch("app.agents.mapper.logger") as mock_logger:
                mapper.map_to_color(material, f"trace-{material.value}")

                # Find the mapper_complete call
                complete_calls = [
                    call for call in mock_logger.info.call_args_list
                    if call[0][0] == "mapper_complete"
                ]

                assert len(complete_calls) == 1
                assert complete_calls[0][1]["color"] == expected_color

    def test_no_error_logs(self):
        """Test that no error logs are emitted during normal operation."""
        mapper = Mapper()

        with patch("app.agents.mapper.logger") as mock_logger:
            # Test all materials
            for material in Material:
                mapper.map_to_color(material, f"trace-{material.value}")

            # No error or warning should be logged
            mock_logger.error.assert_not_called()
            mock_logger.warning.assert_not_called()


class TestBinColorEnum:
    """Test BinColor enum values."""

    def test_all_bin_colors_exist(self):
        """Test that all expected bin colors are defined."""
        expected_colors = {"WHITE", "BLUE", "GREEN", "BLACK", "RED", "GRAY"}
        actual_colors = {color.value for color in BinColor}

        assert actual_colors == expected_colors

    def test_bin_colors_are_strings(self):
        """Test that BinColor inherits from str."""
        for color in BinColor:
            assert isinstance(color.value, str)
            # Can use as string
            assert color.value == color.value.upper()


class TestMapperInstance:
    """Test Mapper instance creation and attributes."""

    def test_mapper_has_material_to_color_dict(self):
        """Test that Mapper has MATERIAL_TO_COLOR class attribute."""
        assert hasattr(Mapper, "MATERIAL_TO_COLOR")
        assert isinstance(Mapper.MATERIAL_TO_COLOR, dict)

    def test_mapper_dict_values_are_bin_colors(self):
        """Test that all values in MATERIAL_TO_COLOR are BinColor enums."""
        for material, color in Mapper.MATERIAL_TO_COLOR.items():
            assert isinstance(material, Material)
            assert isinstance(color, BinColor)

    def test_mapper_instance_creation(self):
        """Test that Mapper can be instantiated without arguments."""
        mapper = Mapper()
        assert mapper is not None
        assert hasattr(mapper, "map_to_color")


class TestColorDistribution:
    """Test the distribution of colors across materials (university 3-color system)."""

    def test_white_bin_materials(self):
        """Test which materials go in WHITE bin (all recyclables including paper)."""
        mapper = Mapper()

        # University system: all recyclables go to WHITE
        # Waste pickers handle cleaning if economically viable
        white_materials = [
            Material.PLASTIC,
            Material.GLASS,
            Material.METAL,
            Material.TETRAPAK,
            Material.PAPER,
            Material.CARDBOARD,
        ]

        for material in white_materials:
            color = mapper.map_to_color(material, "test")
            assert color == BinColor.WHITE, f"{material.value} should map to WHITE"

    def test_green_bin_materials(self):
        """Test which materials go in GREEN bin (organics)."""
        mapper = Mapper()

        green_materials = [Material.ORGANIC]

        for material in green_materials:
            color = mapper.map_to_color(material, "test")
            assert color == BinColor.GREEN, f"{material.value} should map to GREEN"

    def test_black_bin_materials(self):
        """Test which materials go in BLACK bin (non-recyclable)."""
        mapper = Mapper()

        black_materials = [Material.OTHER]

        for material in black_materials:
            color = mapper.map_to_color(material, "test")
            assert color == BinColor.BLACK, f"{material.value} should map to BLACK"


class TestRealWorldScenarios:
    """Test real-world waste classification scenarios (simplified - no cleanliness check)."""

    def test_pet_bottle(self):
        """PET bottle goes to WHITE - waste pickers clean if needed."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.PLASTIC, "test-pet-bottle")
        assert color == BinColor.WHITE

    def test_aluminum_can(self):
        """Aluminum can goes to WHITE - waste pickers clean if needed."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.METAL, "test-aluminum-can")
        assert color == BinColor.WHITE

    def test_pizza_box(self):
        """Pizza box (cardboard) goes to WHITE - waste pickers decide if salvageable."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.CARDBOARD, "test-pizza-box")
        assert color == BinColor.WHITE

    def test_food_scraps(self):
        """Food scraps go to GREEN for composting."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.ORGANIC, "test-food-scraps")
        assert color == BinColor.GREEN

    def test_styrofoam(self):
        """Styrofoam (if classified as OTHER) goes to BLACK."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.OTHER, "test-styrofoam")
        assert color == BinColor.BLACK

    def test_tetrapak_carton(self):
        """Tetrapak goes to WHITE - special processing handled by recyclers."""
        mapper = Mapper()
        color = mapper.map_to_color(Material.TETRAPAK, "test-tetrapak")
        assert color == BinColor.WHITE
