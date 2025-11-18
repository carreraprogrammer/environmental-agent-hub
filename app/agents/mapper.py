"""
Mapper Agent - Maps waste material to bin color with condition-aware logic.

Enhanced mapping based on Colombian/Latin American waste classification
standards (NTC 24) with support for conditional recommendations when
items are contaminated or require cleaning.
"""

from __future__ import annotations

from typing import Dict

from app.core.logging import logger
from app.schemas.bin_color import BinColor
from app.schemas.bin_recommendation import (
    BinRecommendation,
    RecommendationType,
)
from app.schemas.classification import (
    Material,
    PhysicalCondition,
    Recyclability,
)


class Mapper:
    """
    Mapper Agent - Maps waste material to bin color with condition-aware logic.

    Enhanced mapping based on Colombian/Latin American waste classification
    standards (NTC 24). Provides conditional recommendations when items are
    contaminated or require cleaning before recycling.

    University 3-color system:
    - WHITE: Aprovechable (reciclable) - plastics, glass, metal, paper
    - GREEN: Orgánicos biodegradables - food waste
    - BLACK: No aprovechable (residuos ordinarios) - non-recyclable

    This agent is synchronous because it only performs dictionary lookups
    with no I/O operations. Typical latency: <1ms.

    Example:
        >>> mapper = Mapper()
        >>> # Simple mapping (backward compatible)
        >>> color = mapper.map_to_color(Material.PLASTIC, "trace-123")
        >>> print(color)  # BinColor.WHITE

        >>> # Enhanced mapping with condition
        >>> rec = mapper.map_with_condition(
        ...     Material.PLASTIC,
        ...     PhysicalCondition.CONTAMINATED,
        ...     Recyclability.RECYCLABLE_AFTER_CLEANING,
        ...     "trace-123"
        ... )
        >>> print(rec.recommendation_type)  # CONDITIONAL
        >>> print(rec.alternative_bin)  # BLACK
    """

    # Static mapping dictionary for university 3-color system
    # Campus ecological points only have: WHITE, GREEN, BLACK
    MATERIAL_TO_COLOR: Dict[Material, BinColor] = {
        # WHITE: Aprovechable (reciclable)
        Material.PLASTIC: BinColor.WHITE,
        Material.GLASS: BinColor.WHITE,
        Material.METAL: BinColor.WHITE,
        Material.TETRAPAK: BinColor.WHITE,
        Material.PAPER: BinColor.WHITE,
        Material.CARDBOARD: BinColor.WHITE,
        # GREEN: Orgánicos biodegradables
        Material.ORGANIC: BinColor.GREEN,
        # BLACK: No aprovechable (residuos ordinarios)
        Material.OTHER: BinColor.BLACK,
    }

    # Educational messages in Spanish
    MESSAGES = {
        "clean_recyclable": "Deposita en caneca blanca",
        "contaminated_conditional": "Enjuaga antes de reciclar",
        "non_recyclable": "Deposita en caneca negra (no reciclable)",
        "organic": "Deposita en caneca verde (orgánicos)",
        "uncertain": "No pudimos identificar el material con certeza",
        "condition_clean": "Si está limpio → BLANCO",
        "condition_contaminated": "Si tiene residuos de comida → NEGRO",
        "requires_cleaning": "Este material requiere limpieza antes de reciclar",
    }

    def map_to_color(
        self,
        material: Material,
        trace_id: str,
    ) -> BinColor:
        """
        Simple material to bin color mapping (backward compatible).

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

        # Get color from static mapping, fallback to BLACK for unknown materials
        color = self.MATERIAL_TO_COLOR.get(material, BinColor.BLACK)

        logger.info(
            "mapper_complete",
            trace_id=trace_id,
            material=material.value,
            color=color.value,
        )

        return color

    def map_with_condition(
        self,
        material: Material,
        condition: PhysicalCondition | None,
        recyclability: Recyclability | None,
        trace_id: str,
        confidence: float = 1.0,
    ) -> BinRecommendation:
        """
        Enhanced mapping with condition-aware logic.

        Provides rich recommendations including conditional options for
        contaminated recyclables and educational messages.

        Args:
            material: Classified material
            condition: Physical condition (CLEAN, CONTAMINATED, etc.)
            recyclability: Recyclability assessment
            trace_id: Request trace ID for logging
            confidence: Material classification confidence (0.0-1.0)

        Returns:
            BinRecommendation with primary bin, type, and instructions
        """
        logger.info(
            "mapper_conditional_started",
            trace_id=trace_id,
            agent="Mapper",
            material=material.value,
            condition=condition.value if condition else None,
            recyclability=recyclability.value if recyclability else None,
            confidence=confidence,
        )

        # Get base color from material
        base_color = self.MATERIAL_TO_COLOR.get(material, BinColor.BLACK)

        # Determine recommendation based on condition and recyclability
        recommendation = self._determine_recommendation(
            material=material,
            base_color=base_color,
            condition=condition,
            recyclability=recyclability,
            confidence=confidence,
        )

        logger.info(
            "mapper_conditional_complete",
            trace_id=trace_id,
            material=material.value,
            primary_bin=recommendation.primary_bin.value,
            recommendation_type=recommendation.recommendation_type.value,
            has_alternative=recommendation.alternative_bin is not None,
        )

        return recommendation

    def _determine_recommendation(
        self,
        material: Material,
        base_color: BinColor,
        condition: PhysicalCondition | None,
        recyclability: Recyclability | None,
        confidence: float,
    ) -> BinRecommendation:
        """
        Determine the appropriate recommendation based on all factors.

        Decision logic:
        1. Low confidence → UNCERTAIN with note
        2. NON_RECYCLABLE → BLACK (definitive)
        3. ORGANIC → GREEN (definitive)
        4. CONTAMINATED + RECYCLABLE_AFTER_CLEANING → CONDITIONAL (white/black)
        5. CONTAMINATED + regular recyclable → CONDITIONAL (white/black)
        6. CLEAN recyclable → WHITE (definitive)
        """
        # Case 1: Low confidence - uncertain recommendation
        if confidence < 0.6:
            return BinRecommendation(
                primary_bin=base_color,
                recommendation_type=RecommendationType.UNCERTAIN,
                instruction=self.MESSAGES["uncertain"],
            )

        # Case 2: Explicitly non-recyclable
        if recyclability == Recyclability.NON_RECYCLABLE:
            return BinRecommendation(
                primary_bin=BinColor.BLACK,
                recommendation_type=RecommendationType.DEFINITIVE,
                instruction=self.MESSAGES["non_recyclable"],
            )

        # Case 3: Organic material
        if material == Material.ORGANIC:
            return BinRecommendation(
                primary_bin=BinColor.GREEN,
                recommendation_type=RecommendationType.DEFINITIVE,
                instruction=self.MESSAGES["organic"],
            )

        # Case 4: Requires special processing (like Tetrapak)
        if recyclability == Recyclability.REQUIRES_SPECIAL_PROCESSING:
            return BinRecommendation(
                primary_bin=BinColor.WHITE,
                recommendation_type=RecommendationType.DEFINITIVE,
                instruction="Deposita en caneca blanca (requiere proceso especial)",
            )

        # Case 5: Compostable (should go to organic)
        if recyclability == Recyclability.COMPOSTABLE:
            return BinRecommendation(
                primary_bin=BinColor.GREEN,
                recommendation_type=RecommendationType.DEFINITIVE,
                instruction=self.MESSAGES["organic"],
            )

        # Case 6: Contaminated recyclable - CONDITIONAL recommendation
        is_contaminated = condition in (
            PhysicalCondition.CONTAMINATED,
            PhysicalCondition.PARTIALLY_FULL,
        )
        is_recyclable = recyclability in (
            Recyclability.RECYCLABLE,
            Recyclability.RECYCLABLE_AFTER_CLEANING,
            None,  # Assume recyclable if not specified
        )

        if is_contaminated and is_recyclable and base_color == BinColor.WHITE:
            return BinRecommendation(
                primary_bin=BinColor.WHITE,
                recommendation_type=RecommendationType.CONDITIONAL,
                instruction=self.MESSAGES["contaminated_conditional"],
                alternative_bin=BinColor.BLACK,
                condition_message=self.MESSAGES["condition_clean"],
                alternative_message=self.MESSAGES["condition_contaminated"],
            )

        # Case 7: Clean recyclable - definitive
        if base_color == BinColor.WHITE:
            return BinRecommendation(
                primary_bin=BinColor.WHITE,
                recommendation_type=RecommendationType.DEFINITIVE,
                instruction=self.MESSAGES["clean_recyclable"],
            )

        # Case 8: Default - use base color
        return BinRecommendation(
            primary_bin=base_color,
            recommendation_type=RecommendationType.DEFINITIVE,
            instruction=f"Deposita en caneca {base_color.value.lower()}",
        )
