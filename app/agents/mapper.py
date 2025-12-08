"""
Mapper Agent - Material to Bin Color mapping.

PHILOSOPHY:
Professional waste pickers (recicladores de oficio) handle cleaning.
We don't ask students for unrealistic tasks (washing containers).
This reflects the real value chain of recycling in Colombia.

Based on Colombian Technical Standard NTC 24 and university 3-color system.
"""

from __future__ import annotations

from typing import Dict

from app.core.logging import logger
from app.schemas.bin_color import BinColor
from app.schemas.classification import Material


class Mapper:
    """
    Maps waste material to bin color (NTC 24 standard).

    Simple, direct mapping without considering "cleanliness".
    Trust waste pickers to decide what's worth cleaning.

    University 3-color system:
    - WHITE: Aprovechable (reciclable) - plastics, glass, metal, paper
    - GREEN: Orgánicos biodegradables - food waste
    - BLACK: No aprovechable (residuos ordinarios) - non-recyclable

    This agent is synchronous because it only performs dictionary lookups
    with no I/O operations. Typical latency: <1ms.

    Example:
        >>> mapper = Mapper()
        >>> color = mapper.map_to_color(Material.PLASTIC, "trace-123")
        >>> print(color)  # BinColor.WHITE
    """

    # Static mapping: Material → Bin Color
    # Based on Colombian waste classification (NTC 24 + campus context)
    MATERIAL_TO_COLOR: Dict[Material, BinColor] = {
        # RECYCLABLES (WHITE) - Waste pickers clean if economically viable
        Material.PLASTIC: BinColor.WHITE,
        Material.METAL: BinColor.WHITE,
        Material.GLASS: BinColor.WHITE,
        Material.PAPER: BinColor.WHITE,
        Material.CARDBOARD: BinColor.WHITE,
        Material.TETRAPAK: BinColor.WHITE,
        # ORGANICS (GREEN) - Compostable
        Material.ORGANIC: BinColor.GREEN,
        # REJECT (BLACK) - Non-recyclable
        Material.NO_WASTE: BinColor.BLACK,
        Material.OTHER: BinColor.BLACK,
    }

    def map_to_color(
        self,
        material: Material,
        trace_id: str,
    ) -> BinColor:
        """
        Map material to bin color.

        Direct mapping without considering physical condition.
        Waste pickers handle cleaning decisions based on market value.

        Args:
            material: Classified waste material
            trace_id: Request trace ID for logging

        Returns:
            BinColor for disposal

        Examples:
            >>> mapper = Mapper()
            >>> mapper.map_to_color(Material.PLASTIC, "trace-123")
            BinColor.WHITE
        """
        logger.info(
            "mapper_started",
            trace_id=trace_id,
            agent="Mapper",
            material=material.value,
        )

        # Get color from static mapping (fallback to BLACK)
        color = self.MATERIAL_TO_COLOR.get(material, BinColor.BLACK)

        logger.info(
            "mapper_complete",
            trace_id=trace_id,
            material=material.value,
            color=color.value,
        )

        return color
