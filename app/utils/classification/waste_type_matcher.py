"""
WasteTypeMatcher - Deterministic mapping to Backend waste type codes.

ARCHITECTURE NOTE: This is a UTILITY, not an AI agent.
Pure lookup table matching with Backend synchronization.

Maps the combination of material, characteristics, and volume to the exact
waste_type_code used by the Backend Rails system.

Philosophy:
- Hybrid pattern: sync from Backend, fallback to local catalog
- Deterministic matching: no AI, pure lookup tables
- Always validates codes before returning to prevent 422 errors
- Refresh catalog every 24 hours for freshness

Cost: $0 per request (no external API calls for mapping)
Latency: <10ms p95

Example:
    >>> from app.utils.classification.waste_type_matcher import WasteTypeMatcher
    >>> from app.schemas.classification import Material
    >>> matcher = WasteTypeMatcher()
    >>> await matcher.initialize()
    >>> code = matcher.map_to_waste_type_code(
    ...     Material.PLASTIC,
    ...     {"material_specific": "PET"},
    ...     520.0,
    ...     "trace-123"
    ... )
    >>> print(code)  # "PET_BOTTLE_500ML"
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from app.core.logging import logger
from app.schemas.classification import Material
from app.services.backend_client import BackendClient


class WasteTypeMatcher:
    """
    Deterministic utility for mapping waste characteristics to Backend codes.

    NOT AN AGENT: Pure lookup table matching, no AI/ML involved.

    Uses a hybrid pattern with Backend synchronization and local fallback
    to ensure reliable mapping even when Backend is unavailable.

    Attributes:
        local_catalog: Waste types from local YAML or hardcoded
        backend_catalog: Waste types synced from Backend (None if unavailable)
        last_sync: Timestamp of last successful Backend sync
        sync_interval: Time between Backend syncs (default 24 hours)
    """

    # Sync interval: 24 hours
    SYNC_INTERVAL_HOURS = 24

    # Fallback codes by material when no match found
    FALLBACK_CODES: dict[str, str] = {
        "PLASTIC": "PLASTIC_OTHER",
        "METAL": "ALUMINUM_CAN",
        "GLASS": "GLASS_BOTTLE_CLEAR",
        "PAPER": "PAPER_WHITE_A4",
        "CARDBOARD": "CARDBOARD_BOX",
        "ORGANIC": "FOOD_WASTE",
        "TETRAPAK": "PLASTIC_OTHER",
        "OTHER": "PLASTIC_OTHER",
    }

    def __init__(self, backend_client: BackendClient | None = None) -> None:
        """
        Initialize WasteTypeMapper with optional BackendClient.

        Args:
            backend_client: Optional BackendClient for catalog sync
        """
        self.backend_client = backend_client or BackendClient()
        self.local_catalog: list[dict[str, Any]] = self._load_local_catalog()
        self.backend_catalog: list[dict[str, Any]] | None = None
        self.last_sync: datetime | None = None
        self.sync_interval = timedelta(hours=self.SYNC_INTERVAL_HOURS)

        logger.info(
            "waste_type_mapper_initialized",
            local_catalog_size=len(self.local_catalog),
        )

    def _get_hardcoded_catalog(self) -> list[dict[str, Any]]:
        """
        Return hardcoded waste type catalog with minimum 12 codes.

        Returns:
            List of waste type definitions with code, category, and attributes
        """
        return [
            # PLASTIC types
            {
                "code": "PET_BOTTLE_500ML",
                "category": "PLASTIC",
                "volume_range": [400, 600],
                "material_type": "PET",
                "description": "Botella PET 500ml",
            },
            {
                "code": "PET_BOTTLE_1500ML",
                "category": "PLASTIC",
                "volume_range": [1300, 1700],
                "material_type": "PET",
                "description": "Botella PET 1.5L",
            },
            {
                "code": "HDPE_BOTTLE",
                "category": "PLASTIC",
                "material_type": "HDPE",
                "description": "Botella HDPE",
            },
            {
                "code": "PLASTIC_OTHER",
                "category": "PLASTIC",
                "description": "Otros plásticos",
            },
            # METAL types
            {
                "code": "ALUMINUM_CAN",
                "category": "METAL",
                "material_type": "aluminum",
                "description": "Lata de aluminio",
            },
            {
                "code": "STEEL_CAN",
                "category": "METAL",
                "material_type": "steel",
                "description": "Lata de acero",
            },
            # GLASS types
            {
                "code": "GLASS_BOTTLE_CLEAR",
                "category": "GLASS",
                "color": "clear",
                "description": "Botella de vidrio transparente",
            },
            {
                "code": "GLASS_BOTTLE_COLORED",
                "category": "GLASS",
                "color": "colored",
                "description": "Botella de vidrio de color",
            },
            # PAPER types
            {
                "code": "PAPER_WHITE_A4",
                "category": "PAPER",
                "paper_type": "white",
                "description": "Papel blanco A4",
            },
            {
                "code": "CARDBOARD_BOX",
                "category": "PAPER",
                "container_type": "box",
                "description": "Caja de cartón",
            },
            {
                "code": "NEWSPAPER",
                "category": "PAPER",
                "paper_type": "newspaper",
                "description": "Periódico",
            },
            # ORGANIC types
            {
                "code": "FOOD_WASTE",
                "category": "ORGANIC",
                "description": "Residuos de comida",
            },
        ]

    def _load_local_catalog(self) -> list[dict[str, Any]]:
        """
        Load waste type catalog from YAML file or use hardcoded.

        Returns:
            List of waste type definitions
        """
        yaml_path = Path("config/backend_waste_types.yaml")

        if yaml_path.exists():
            try:
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "waste_types" in data:
                        logger.info(
                            "local_catalog_loaded_from_yaml",
                            path=str(yaml_path),
                            count=len(data["waste_types"]),
                        )
                        return cast(list[dict[str, Any]], data["waste_types"])
            except (OSError, yaml.YAMLError, TypeError, ValueError) as exc:
                logger.warning(
                    "yaml_catalog_load_failed",
                    path=str(yaml_path),
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        # Use hardcoded catalog
        catalog = self._get_hardcoded_catalog()
        logger.info(
            "hardcoded_catalog_loaded",
            count=len(catalog),
        )
        return catalog

    async def initialize(self, trace_id: str = "system") -> None:
        """
        Initialize mapper by syncing catalog from Backend.

        Attempts to fetch waste types catalog from Backend Rails.
        If successful, updates backend_catalog. If fails, logs warning
        and continues with local catalog only.

        Args:
            trace_id: Request trace ID for logging
        """
        logger.info(
            "waste_type_mapper_started",
            trace_id=trace_id,
            agent="WasteTypeMapper",
        )

        try:
            catalog = await self.backend_client.get_waste_types_catalog()
            if catalog:
                self.backend_catalog = catalog
                self.last_sync = datetime.utcnow()
                logger.info(
                    "waste_type_catalog_synced",
                    trace_id=trace_id,
                    agent="WasteTypeMapper",
                    catalog_size=len(catalog),
                    source="backend",
                )
            else:
                logger.warning(
                    "backend_catalog_empty",
                    trace_id=trace_id,
                    agent="WasteTypeMapper",
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "backend_catalog_sync_failed",
                trace_id=trace_id,
                agent="WasteTypeMapper",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            self.backend_catalog = None

    async def refresh_if_needed(self, trace_id: str = "system") -> None:
        """
        Re-sync catalog from Backend if sync interval exceeded.

        Args:
            trace_id: Request trace ID for logging
        """
        if self.last_sync is None:
            await self.initialize(trace_id)
            return

        elapsed = datetime.utcnow() - self.last_sync
        if elapsed > self.sync_interval:
            logger.info(
                "catalog_refresh_triggered",
                trace_id=trace_id,
                agent="WasteTypeMapper",
                elapsed_hours=elapsed.total_seconds() / 3600,
            )
            await self.initialize(trace_id)
        else:
            logger.debug(
                "catalog_refresh_skipped",
                trace_id=trace_id,
                agent="WasteTypeMapper",
                next_refresh_in_hours=(self.sync_interval - elapsed).total_seconds() / 3600,
            )

    def get_active_catalog(self) -> list[dict[str, Any]]:
        """
        Get the active catalog, preferring backend over local.

        Returns:
            List of waste type definitions from backend or local catalog
        """
        if self.backend_catalog:
            return self.backend_catalog
        return self.local_catalog

    def get_valid_codes(self) -> list[str]:
        """
        Get list of all valid waste type codes from active catalog.

        Returns:
            List of waste type code strings
        """
        catalog = self.get_active_catalog()
        return [wt["code"] for wt in catalog]

    def map_to_waste_type_code(
        self,
        material: Material,
        characteristics: dict[str, Any],
        volume_ml: float | None,
        trace_id: str,
    ) -> str:
        """
        Map material and characteristics to waste type code.

        Args:
            material: Material type from classifier
            characteristics: Dict with material_specific, color, container_type, etc.
            volume_ml: Estimated volume in milliliters
            trace_id: Request trace ID for logging

        Returns:
            Waste type code string (never None or empty)
        """
        logger.info(
            "waste_type_mapping_started",
            trace_id=trace_id,
            agent="WasteTypeMapper",
            material=material.value,
            volume_ml=volume_ml,
        )

        catalog = self.get_active_catalog()

        # Find best match based on material
        code = self._find_best_match(material, characteristics, volume_ml, catalog)

        # Validate code exists in catalog
        valid_codes = self.get_valid_codes()
        if code not in valid_codes:
            logger.warning(
                "invalid_code_detected",
                trace_id=trace_id,
                agent="WasteTypeMapper",
                invalid_code=code,
            )
            code = self._get_fallback_code(material, catalog)
            strategy = "fallback"
        else:
            strategy = "direct_match"

        logger.info(
            "waste_type_mapped",
            trace_id=trace_id,
            agent="WasteTypeMapper",
            material=material.value,
            waste_type_code=code,
            strategy=strategy,
        )

        return code

    def _find_best_match(
        self,
        material: Material,
        characteristics: dict[str, Any],
        volume_ml: float | None,
        catalog: list[dict[str, Any]],
    ) -> str:
        """
        Find best matching waste type code based on material.

        Delegates to specific matching methods based on material type.

        Args:
            material: Material type
            characteristics: Material characteristics
            volume_ml: Volume in milliliters
            catalog: Waste type catalog

        Returns:
            Best matching waste type code
        """
        if material == Material.PLASTIC:
            return self._match_plastic(characteristics, volume_ml, catalog)
        if material == Material.METAL:
            return self._match_metal(characteristics, catalog)
        if material == Material.GLASS:
            return self._match_glass(characteristics, catalog)
        if material in (Material.PAPER, Material.CARDBOARD):
            return self._match_paper(characteristics, catalog)
        if material == Material.ORGANIC:
            return "FOOD_WASTE"
        if material == Material.TETRAPAK:
            # TETRAPAK typically goes to PLASTIC_OTHER
            return "PLASTIC_OTHER"

        # OTHER material
        return "PLASTIC_OTHER"

    def _match_plastic(
        self,
        characteristics: dict[str, Any],
        volume_ml: float | None,
        catalog: list[dict[str, Any]],
    ) -> str:
        """
        Match plastic waste by volume range and material type.

        Args:
            characteristics: Should contain material_specific
            volume_ml: Volume in milliliters
            catalog: Waste type catalog

        Returns:
            Matching plastic waste type code
        """
        material_specific = characteristics.get("material_specific", "").upper()

        # Filter to plastic types
        plastic_types = [wt for wt in catalog if wt.get("category") == "PLASTIC"]

        # Try to match by volume range first
        if volume_ml is not None:
            for wt in plastic_types:
                volume_range = wt.get("volume_range")
                if not volume_range:
                    continue

                min_vol, max_vol = volume_range
                if not min_vol <= volume_ml <= max_vol:
                    continue

                # Also check material type if specified
                wt_material = wt.get("material_type", "").upper()
                is_material_match = not wt_material or material_specific in (
                    wt_material,
                    "PET",
                )
                if is_material_match:
                    return cast(str, wt["code"])

        # Try to match by material type
        if material_specific:
            for wt in plastic_types:
                wt_material = wt.get("material_type", "").upper()
                if wt_material == material_specific:
                    return cast(str, wt["code"])

        # Default fallback for plastic
        return "PLASTIC_OTHER"

    def _match_metal(
        self,
        characteristics: dict[str, Any],
        catalog: list[dict[str, Any]],
    ) -> str:
        """
        Match metal waste by material_specific (aluminum/steel).

        Args:
            characteristics: Should contain material_specific
            catalog: Waste type catalog

        Returns:
            Matching metal waste type code
        """
        material_specific = characteristics.get("material_specific", "").lower()

        # Filter to metal types
        metal_types = [wt for wt in catalog if wt.get("category") == "METAL"]

        # Match by material type
        for wt in metal_types:
            wt_material = wt.get("material_type", "").lower()
            if wt_material == material_specific:
                return cast(str, wt["code"])

        # Default to aluminum can
        return "ALUMINUM_CAN"

    def _match_glass(
        self,
        characteristics: dict[str, Any],
        catalog: list[dict[str, Any]],
    ) -> str:
        """
        Match glass waste by color (clear/colored).

        Args:
            characteristics: Should contain color
            catalog: Waste type catalog

        Returns:
            Matching glass waste type code
        """
        color = characteristics.get("color", "").lower()

        # Filter to glass types
        glass_types = [wt for wt in catalog if wt.get("category") == "GLASS"]

        # Match by color
        for wt in glass_types:
            wt_color = wt.get("color", "").lower()
            if wt_color == color:
                return cast(str, wt["code"])

        # Default to clear glass
        return "GLASS_BOTTLE_CLEAR"

    def _match_paper(
        self,
        characteristics: dict[str, Any],
        catalog: list[dict[str, Any]],
    ) -> str:
        """
        Match paper/cardboard waste by container_type and paper_type.

        Args:
            characteristics: Should contain container_type or paper_type
            catalog: Waste type catalog

        Returns:
            Matching paper waste type code
        """
        container_type = characteristics.get("container_type", "").lower()
        paper_type = characteristics.get("paper_type", "").lower()

        # Filter to paper types
        paper_types = [wt for wt in catalog if wt.get("category") == "PAPER"]

        # Match by container_type first (for cardboard boxes)
        if container_type:
            for wt in paper_types:
                wt_container = wt.get("container_type", "").lower()
                if wt_container == container_type:
                    return cast(str, wt["code"])

        # Match by paper_type
        if paper_type:
            for wt in paper_types:
                wt_paper = wt.get("paper_type", "").lower()
                if wt_paper == paper_type:
                    return cast(str, wt["code"])

        # Default to white paper
        return "PAPER_WHITE_A4"

    def _get_fallback_code(
        self,
        material: Material,
        catalog: list[dict[str, Any]],
    ) -> str:
        """
        Get fallback code when no specific match found.

        First tries to find first code with matching category in catalog,
        then falls back to hardcoded fallback codes.

        Args:
            material: Material type
            catalog: Waste type catalog

        Returns:
            Fallback waste type code
        """
        category = material.value

        # Try to find first code with matching category
        for wt in catalog:
            if wt.get("category") == category:
                logger.warning(
                    "using_fallback_code",
                    material=category,
                    fallback_code=wt["code"],
                    source="catalog_first_match",
                )
                return cast(str, wt["code"])

        # Use hardcoded fallback
        fallback = self.FALLBACK_CODES.get(category, "PLASTIC_OTHER")
        logger.warning(
            "using_fallback_code",
            material=category,
            fallback_code=fallback,
            source="hardcoded",
        )
        return fallback
