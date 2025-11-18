"""
Mapper Agent - Maps waste material to bin color.

Simple static mapping based on Colombian/Latin American waste classification
standards (NTC 24). No I/O operations, synchronous execution.
"""

from __future__ import annotations

from typing import Dict

from app.core.logging import logger
from app.schemas.bin_color import BinColor
from app.schemas.classification import Material


class Mapper:
    """
    Mapper Agent - Maps waste material to bin color.

    Simple static mapping based on Colombian/Latin American
    waste classification standards (NTC 24).

    This agent is synchronous because it only performs dictionary lookups
    with no I/O operations. Typical latency: <1ms.

    Example:
        >>> mapper = Mapper()
        >>> color = mapper.map_to_color(Material.PLASTIC, "trace-123")
        >>> print(color)  # BinColor.WHITE
    """

    # Static mapping dictionary based on NTC 24
    MATERIAL_TO_COLOR: Dict[Material, BinColor] = {
        # WHITE: Aprovechable (reciclable)
        Material.PLASTIC: BinColor.WHITE,
        Material.GLASS: BinColor.WHITE,
        Material.METAL: BinColor.WHITE,
        Material.TETRAPAK: BinColor.WHITE,
        # BLUE: Papel y cartón
        Material.PAPER: BinColor.BLUE,
        Material.CARDBOARD: BinColor.BLUE,
        # GREEN: Orgánicos biodegradables
        Material.ORGANIC: BinColor.GREEN,
        # GRAY: Otros / no clasificados
        Material.OTHER: BinColor.GRAY,
    }

    def map_to_color(
        self,
        material: Material,
        trace_id: str,
    ) -> BinColor:
        """
        Map material to bin color.

        Args:
            material: Classified material from MaterialClassifier
            trace_id: Request trace ID for logging

        Returns:
            BinColor corresponding to the material
        """
        logger.info(
            "mapper_started",
            trace_id=trace_id,
            agent="Mapper",
            material=material.value,
        )

        # Get color from static mapping, fallback to GRAY for unknown materials
        color = self.MATERIAL_TO_COLOR.get(material, BinColor.GRAY)

        logger.info(
            "mapper_complete",
            trace_id=trace_id,
            material=material.value,
            color=color.value,
        )

        return color
