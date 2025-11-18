"""
Bin color schema for waste classification.

Based on Colombian Technical Standard NTC 24 for waste separation colors.
"""

from __future__ import annotations

from enum import Enum


class BinColor(str, Enum):
    """
    Bin colors for waste classification (Colombian/Latin American standard).

    Based on Colombian Technical Standard NTC 24 and university guidelines.

    Colors:
        WHITE: Aprovechable (reciclable) - plástico, vidrio, metal, Tetrapak
        BLUE: Papel y cartón
        GREEN: Orgánicos biodegradables
        BLACK: No aprovechable (residuos ordinarios)
        RED: Peligrosos (baterías, electrónicos, químicos)
        GRAY: Otros / no clasificados
    """

    WHITE = "WHITE"  # Aprovechable (reciclable): plástico, vidrio, metal
    BLUE = "BLUE"  # Papel y cartón
    GREEN = "GREEN"  # Orgánicos biodegradables
    BLACK = "BLACK"  # No aprovechable (residuos ordinarios)
    RED = "RED"  # Peligrosos (baterías, electrónicos, químicos)
    GRAY = "GRAY"  # Otros / no clasificados
