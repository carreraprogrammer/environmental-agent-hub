"""
Unit tests for WasteTypeMapper agent.

Tests cover:
- Hardcoded catalog validation
- Backend synchronization
- Refresh logic
- Material-specific mapping
- Fallback behavior
- Helper methods
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.waste_type_mapper import WasteTypeMapper
from app.schemas.classification import Material


class TestCatalog:
    """Test catalog loading and validation."""

    def test_hardcoded_catalog_has_minimum_12_codes(self) -> None:
        """Test that hardcoded catalog has at least 12 waste types."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        assert len(catalog) >= 12, f"Expected ≥12 codes, got {len(catalog)}"

    def test_hardcoded_catalog_has_required_codes(self) -> None:
        """Test that catalog contains all required waste type codes."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()
        codes = [wt["code"] for wt in catalog]

        required_codes = [
            "PET_BOTTLE_500ML",
            "PET_BOTTLE_1500ML",
            "HDPE_BOTTLE",
            "PLASTIC_OTHER",
            "ALUMINUM_CAN",
            "STEEL_CAN",
            "GLASS_BOTTLE_CLEAR",
            "GLASS_BOTTLE_COLORED",
            "PAPER_WHITE_A4",
            "CARDBOARD_BOX",
            "NEWSPAPER",
            "FOOD_WASTE",
        ]

        for code in required_codes:
            assert code in codes, f"Missing required code: {code}"

    def test_each_catalog_entry_has_code_and_category(self) -> None:
        """Test that each waste type has required fields."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        for wt in catalog:
            assert "code" in wt, f"Missing 'code' in {wt}"
            assert "category" in wt, f"Missing 'category' in {wt}"

    def test_load_local_catalog_uses_hardcoded_when_yaml_missing(self) -> None:
        """Test that local catalog falls back to hardcoded when YAML missing."""
        with patch("app.agents.waste_type_mapper.Path.exists", return_value=False):
            mapper = WasteTypeMapper()
            assert len(mapper.local_catalog) >= 12

    def test_load_local_catalog_reads_yaml_when_present(self) -> None:
        """Test that local catalog reads from YAML when file exists."""
        yaml_content = {"waste_types": [{"code": "TEST_CODE", "category": "TEST"}]}

        with patch("app.agents.waste_type_mapper.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("yaml.safe_load", return_value=yaml_content):
                    mapper = WasteTypeMapper()
                    assert mapper.local_catalog == yaml_content["waste_types"]


class TestInitialization:
    """Test mapper initialization and backend sync."""

    @pytest.mark.asyncio
    async def test_initialize_success_syncs_backend_catalog(self) -> None:
        """Test that initialize() syncs catalog from backend on success."""
        backend_catalog = [
            {"code": "BACKEND_CODE_1", "category": "PLASTIC"},
            {"code": "BACKEND_CODE_2", "category": "METAL"},
        ]

        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(return_value=backend_catalog)

        mapper = WasteTypeMapper(backend_client=mock_client)
        await mapper.initialize("test-trace")

        assert mapper.backend_catalog == backend_catalog
        assert mapper.last_sync is not None

    @pytest.mark.asyncio
    async def test_initialize_failure_keeps_backend_catalog_none(self) -> None:
        """Test that initialize() keeps backend_catalog None on failure."""
        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(
            side_effect=Exception("Connection error")
        )

        mapper = WasteTypeMapper(backend_client=mock_client)
        await mapper.initialize("test-trace")

        assert mapper.backend_catalog is None

    @pytest.mark.asyncio
    async def test_initialize_logs_sync_success(self) -> None:
        """Test that successful sync is logged."""
        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(
            return_value=[{"code": "TEST", "category": "PLASTIC"}]
        )

        mapper = WasteTypeMapper(backend_client=mock_client)

        with patch("app.agents.waste_type_mapper.logger") as mock_logger:
            await mapper.initialize("test-trace")

            # Check that catalog synced log was called
            mock_logger.info.assert_any_call(
                "waste_type_catalog_synced",
                trace_id="test-trace",
                agent="WasteTypeMapper",
                catalog_size=1,
                source="backend",
            )

    @pytest.mark.asyncio
    async def test_initialize_logs_sync_failure(self) -> None:
        """Test that sync failure is logged as warning."""
        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(
            side_effect=Exception("Timeout")
        )

        mapper = WasteTypeMapper(backend_client=mock_client)

        with patch("app.agents.waste_type_mapper.logger") as mock_logger:
            await mapper.initialize("test-trace")

            # Check warning was logged
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "backend_catalog_sync_failed"


class TestRefresh:
    """Test catalog refresh logic."""

    @pytest.mark.asyncio
    async def test_refresh_if_needed_skips_when_recent(self) -> None:
        """Test that refresh is skipped when last sync is recent."""
        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(return_value=[])

        mapper = WasteTypeMapper(backend_client=mock_client)
        mapper.last_sync = datetime.utcnow() - timedelta(hours=1)
        mapper.backend_catalog = [{"code": "EXISTING", "category": "PLASTIC"}]

        await mapper.refresh_if_needed("test-trace")

        # Should not call get_waste_types_catalog
        mock_client.get_waste_types_catalog.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_if_needed_refreshes_when_stale(self) -> None:
        """Test that refresh happens when sync interval exceeded."""
        new_catalog = [{"code": "NEW_CODE", "category": "METAL"}]

        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(return_value=new_catalog)

        mapper = WasteTypeMapper(backend_client=mock_client)
        mapper.last_sync = datetime.utcnow() - timedelta(hours=25)
        mapper.backend_catalog = [{"code": "OLD_CODE", "category": "PLASTIC"}]

        await mapper.refresh_if_needed("test-trace")

        # Should call get_waste_types_catalog
        mock_client.get_waste_types_catalog.assert_called_once()
        assert mapper.backend_catalog == new_catalog

    @pytest.mark.asyncio
    async def test_refresh_if_needed_initializes_when_never_synced(self) -> None:
        """Test that refresh initializes when last_sync is None."""
        catalog = [{"code": "FIRST_SYNC", "category": "GLASS"}]

        mock_client = MagicMock()
        mock_client.get_waste_types_catalog = AsyncMock(return_value=catalog)

        mapper = WasteTypeMapper(backend_client=mock_client)
        assert mapper.last_sync is None

        await mapper.refresh_if_needed("test-trace")

        mock_client.get_waste_types_catalog.assert_called_once()
        assert mapper.backend_catalog == catalog


class TestHelpers:
    """Test helper methods."""

    def test_get_valid_codes_returns_list_of_strings(self) -> None:
        """Test that get_valid_codes returns list of string codes."""
        mapper = WasteTypeMapper()
        codes = mapper.get_valid_codes()

        assert isinstance(codes, list)
        assert all(isinstance(code, str) for code in codes)
        assert len(codes) >= 12

    def test_get_valid_codes_contains_required_codes(self) -> None:
        """Test that valid codes includes required codes."""
        mapper = WasteTypeMapper()
        codes = mapper.get_valid_codes()

        required = ["PET_BOTTLE_500ML", "ALUMINUM_CAN", "GLASS_BOTTLE_CLEAR"]
        for code in required:
            assert code in codes, f"Missing {code} in valid codes"

    def test_get_active_catalog_prefers_backend(self) -> None:
        """Test that get_active_catalog returns backend when available."""
        mapper = WasteTypeMapper()
        mapper.backend_catalog = [{"code": "BACKEND", "category": "PLASTIC"}]

        active = mapper.get_active_catalog()
        assert active == mapper.backend_catalog

    def test_get_active_catalog_falls_back_to_local(self) -> None:
        """Test that get_active_catalog returns local when no backend."""
        mapper = WasteTypeMapper()
        mapper.backend_catalog = None

        active = mapper.get_active_catalog()
        assert active == mapper.local_catalog


class TestMappingPlastic:
    """Test plastic material mapping."""

    def test_plastic_500ml_maps_to_pet_bottle_500ml(self) -> None:
        """Test that 500ml plastic bottle maps to PET_BOTTLE_500ML."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {"material_specific": "PET"},
            520.0,
            "test-trace",
        )

        assert code == "PET_BOTTLE_500ML"

    def test_plastic_1500ml_maps_to_pet_bottle_1500ml(self) -> None:
        """Test that 1500ml plastic bottle maps to PET_BOTTLE_1500ML."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {"material_specific": "PET"},
            1500.0,
            "test-trace",
        )

        assert code == "PET_BOTTLE_1500ML"

    def test_plastic_hdpe_maps_to_hdpe_bottle(self) -> None:
        """Test that HDPE plastic maps to HDPE_BOTTLE."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {"material_specific": "HDPE"},
            None,
            "test-trace",
        )

        assert code == "HDPE_BOTTLE"

    def test_plastic_unknown_maps_to_plastic_other(self) -> None:
        """Test that unknown plastic maps to PLASTIC_OTHER."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {},
            None,
            "test-trace",
        )

        assert code == "PLASTIC_OTHER"

    def test_plastic_boundary_volume_400ml(self) -> None:
        """Test that 400ml (boundary) maps to PET_BOTTLE_500ML."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {"material_specific": "PET"},
            400.0,
            "test-trace",
        )

        assert code == "PET_BOTTLE_500ML"

    def test_plastic_boundary_volume_600ml(self) -> None:
        """Test that 600ml (boundary) maps to PET_BOTTLE_500ML."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {"material_specific": "PET"},
            600.0,
            "test-trace",
        )

        assert code == "PET_BOTTLE_500ML"


class TestMappingMetal:
    """Test metal material mapping."""

    def test_metal_aluminum_maps_to_aluminum_can(self) -> None:
        """Test that aluminum metal maps to ALUMINUM_CAN."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.METAL,
            {"material_specific": "aluminum"},
            355.0,
            "test-trace",
        )

        assert code == "ALUMINUM_CAN"

    def test_metal_steel_maps_to_steel_can(self) -> None:
        """Test that steel metal maps to STEEL_CAN."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.METAL,
            {"material_specific": "steel"},
            400.0,
            "test-trace",
        )

        assert code == "STEEL_CAN"

    def test_metal_unknown_defaults_to_aluminum_can(self) -> None:
        """Test that unknown metal defaults to ALUMINUM_CAN."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.METAL,
            {},
            None,
            "test-trace",
        )

        assert code == "ALUMINUM_CAN"


class TestMappingGlass:
    """Test glass material mapping."""

    def test_glass_clear_maps_to_glass_bottle_clear(self) -> None:
        """Test that clear glass maps to GLASS_BOTTLE_CLEAR."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.GLASS,
            {"color": "clear"},
            330.0,
            "test-trace",
        )

        assert code == "GLASS_BOTTLE_CLEAR"

    def test_glass_colored_maps_to_glass_bottle_colored(self) -> None:
        """Test that colored glass maps to GLASS_BOTTLE_COLORED."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.GLASS,
            {"color": "colored"},
            750.0,
            "test-trace",
        )

        assert code == "GLASS_BOTTLE_COLORED"

    def test_glass_unknown_defaults_to_glass_bottle_clear(self) -> None:
        """Test that unknown glass defaults to GLASS_BOTTLE_CLEAR."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.GLASS,
            {},
            None,
            "test-trace",
        )

        assert code == "GLASS_BOTTLE_CLEAR"


class TestMappingPaper:
    """Test paper material mapping."""

    def test_paper_box_maps_to_cardboard_box(self) -> None:
        """Test that paper box maps to CARDBOARD_BOX."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PAPER,
            {"container_type": "box"},
            None,
            "test-trace",
        )

        assert code == "CARDBOARD_BOX"

    def test_cardboard_box_maps_to_cardboard_box(self) -> None:
        """Test that cardboard box maps to CARDBOARD_BOX."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.CARDBOARD,
            {"container_type": "box"},
            None,
            "test-trace",
        )

        assert code == "CARDBOARD_BOX"

    def test_paper_newspaper_maps_to_newspaper(self) -> None:
        """Test that newspaper maps to NEWSPAPER."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PAPER,
            {"paper_type": "newspaper"},
            None,
            "test-trace",
        )

        assert code == "NEWSPAPER"

    def test_paper_white_maps_to_paper_white_a4(self) -> None:
        """Test that white paper maps to PAPER_WHITE_A4."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PAPER,
            {"paper_type": "white"},
            None,
            "test-trace",
        )

        assert code == "PAPER_WHITE_A4"

    def test_paper_unknown_defaults_to_paper_white_a4(self) -> None:
        """Test that unknown paper defaults to PAPER_WHITE_A4."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.PAPER,
            {},
            None,
            "test-trace",
        )

        assert code == "PAPER_WHITE_A4"


class TestMappingOrganic:
    """Test organic material mapping."""

    def test_organic_maps_to_food_waste(self) -> None:
        """Test that organic maps directly to FOOD_WASTE."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.ORGANIC,
            {},
            None,
            "test-trace",
        )

        assert code == "FOOD_WASTE"


class TestMappingOther:
    """Test other material mapping."""

    def test_other_maps_to_plastic_other(self) -> None:
        """Test that OTHER material maps to PLASTIC_OTHER."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.OTHER,
            {},
            None,
            "test-trace",
        )

        assert code == "PLASTIC_OTHER"

    def test_tetrapak_maps_to_plastic_other(self) -> None:
        """Test that TETRAPAK maps to PLASTIC_OTHER."""
        mapper = WasteTypeMapper()

        code = mapper.map_to_waste_type_code(
            Material.TETRAPAK,
            {},
            None,
            "test-trace",
        )

        assert code == "PLASTIC_OTHER"


class TestFallbacks:
    """Test fallback behavior."""

    def test_fallback_code_plastic(self) -> None:
        """Test fallback code for PLASTIC material."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        code = mapper._get_fallback_code(Material.PLASTIC, catalog)
        assert code == "PET_BOTTLE_500ML"  # First PLASTIC in catalog

    def test_fallback_code_metal(self) -> None:
        """Test fallback code for METAL material."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        code = mapper._get_fallback_code(Material.METAL, catalog)
        assert code == "ALUMINUM_CAN"  # First METAL in catalog

    def test_fallback_code_glass(self) -> None:
        """Test fallback code for GLASS material."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        code = mapper._get_fallback_code(Material.GLASS, catalog)
        assert code == "GLASS_BOTTLE_CLEAR"  # First GLASS in catalog

    def test_fallback_code_paper(self) -> None:
        """Test fallback code for PAPER material."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        code = mapper._get_fallback_code(Material.PAPER, catalog)
        assert code == "PAPER_WHITE_A4"  # First PAPER in catalog

    def test_fallback_code_organic(self) -> None:
        """Test fallback code for ORGANIC material."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        code = mapper._get_fallback_code(Material.ORGANIC, catalog)
        assert code == "FOOD_WASTE"  # First ORGANIC in catalog

    def test_fallback_uses_hardcoded_when_category_not_in_catalog(self) -> None:
        """Test that hardcoded fallback is used when category missing."""
        mapper = WasteTypeMapper()
        empty_catalog: list[dict] = []

        code = mapper._get_fallback_code(Material.PLASTIC, empty_catalog)
        assert code == "PLASTIC_OTHER"

    def test_empty_characteristics_uses_fallback(self) -> None:
        """Test that empty characteristics result in fallback code."""
        mapper = WasteTypeMapper()

        # All materials with empty characteristics should return valid codes
        for material in Material:
            code = mapper.map_to_waste_type_code(
                material,
                {},
                None,
                "test-trace",
            )
            assert code is not None
            assert code != ""
            assert code in mapper.get_valid_codes()


class TestLogging:
    """Test logging behavior."""

    def test_mapping_logs_started_event(self) -> None:
        """Test that mapping logs started event."""
        mapper = WasteTypeMapper()

        with patch("app.agents.waste_type_mapper.logger") as mock_logger:
            mapper.map_to_waste_type_code(
                Material.PLASTIC,
                {},
                None,
                "test-trace-123",
            )

            mock_logger.info.assert_any_call(
                "waste_type_mapping_started",
                trace_id="test-trace-123",
                agent="WasteTypeMapper",
                material="PLASTIC",
                volume_ml=None,
            )

    def test_mapping_logs_result_event(self) -> None:
        """Test that mapping logs result event."""
        mapper = WasteTypeMapper()

        with patch("app.agents.waste_type_mapper.logger") as mock_logger:
            mapper.map_to_waste_type_code(
                Material.METAL,
                {"material_specific": "aluminum"},
                355.0,
                "test-trace-456",
            )

            mock_logger.info.assert_any_call(
                "waste_type_mapped",
                trace_id="test-trace-456",
                agent="WasteTypeMapper",
                material="METAL",
                waste_type_code="ALUMINUM_CAN",
                strategy="direct_match",
            )

    def test_fallback_logs_warning(self) -> None:
        """Test that fallback usage logs warning."""
        mapper = WasteTypeMapper()
        catalog = mapper._get_hardcoded_catalog()

        with patch("app.agents.waste_type_mapper.logger") as mock_logger:
            mapper._get_fallback_code(Material.PLASTIC, catalog)

            mock_logger.warning.assert_called()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_mapping_never_returns_none(self) -> None:
        """Test that mapping never returns None."""
        mapper = WasteTypeMapper()

        for material in Material:
            code = mapper.map_to_waste_type_code(
                material,
                {},
                None,
                "test-trace",
            )
            assert code is not None

    def test_mapping_never_returns_empty_string(self) -> None:
        """Test that mapping never returns empty string."""
        mapper = WasteTypeMapper()

        for material in Material:
            code = mapper.map_to_waste_type_code(
                material,
                {},
                None,
                "test-trace",
            )
            assert code != ""

    def test_volume_outside_range_uses_material_match(self) -> None:
        """Test that volume outside range falls back to material match."""
        mapper = WasteTypeMapper()

        # Volume 800ml is outside both 400-600 and 1300-1700 ranges
        code = mapper.map_to_waste_type_code(
            Material.PLASTIC,
            {"material_specific": "PET"},
            800.0,
            "test-trace",
        )

        # Should still get a valid plastic code
        assert code in ["PET_BOTTLE_500ML", "PET_BOTTLE_1500ML", "PLASTIC_OTHER"]

    def test_case_insensitive_material_specific(self) -> None:
        """Test that material_specific matching is case insensitive."""
        mapper = WasteTypeMapper()

        # Uppercase
        code1 = mapper.map_to_waste_type_code(
            Material.METAL,
            {"material_specific": "ALUMINUM"},
            None,
            "test-trace",
        )

        # Lowercase
        code2 = mapper.map_to_waste_type_code(
            Material.METAL,
            {"material_specific": "aluminum"},
            None,
            "test-trace",
        )

        assert code1 == code2 == "ALUMINUM_CAN"

    def test_case_insensitive_color(self) -> None:
        """Test that color matching is case insensitive."""
        mapper = WasteTypeMapper()

        # Uppercase
        code1 = mapper.map_to_waste_type_code(
            Material.GLASS,
            {"color": "CLEAR"},
            None,
            "test-trace",
        )

        # Lowercase
        code2 = mapper.map_to_waste_type_code(
            Material.GLASS,
            {"color": "clear"},
            None,
            "test-trace",
        )

        assert code1 == code2 == "GLASS_BOTTLE_CLEAR"
