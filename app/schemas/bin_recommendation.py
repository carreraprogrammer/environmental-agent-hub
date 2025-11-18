"""
Bin recommendation schemas for condition-aware waste classification.

Provides rich recommendation output that handles uncertainty and conditional
scenarios (e.g., contaminated recyclables).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.schemas.bin_color import BinColor


class RecommendationType(str, Enum):
    """Type of bin recommendation."""

    DEFINITIVE = "DEFINITIVE"  # Single clear answer
    CONDITIONAL = "CONDITIONAL"  # Depends on user action (clean/not clean)
    UNCERTAIN = "UNCERTAIN"  # Low confidence, needs verification


@dataclass(slots=True)
class BinRecommendation:
    """
    Rich bin recommendation with conditional options and educational feedback.

    This structure allows the Mapper to return nuanced recommendations for
    edge cases like contaminated recyclables, where the correct bin depends
    on user action.

    Attributes:
        primary_bin: Main bin color recommendation
        recommendation_type: Whether this is definitive, conditional, or uncertain
        instruction: Educational message for the user (Spanish)
        alternative_bin: Alternative bin if condition changes (e.g., if cleaned)
        condition_message: Message explaining the condition (e.g., "si está limpio")
        alternative_message: Message for alternative bin (e.g., "si tiene comida")

    Examples:
        Clean plastic bottle:
            primary_bin=WHITE, recommendation_type=DEFINITIVE,
            instruction="Deposita en caneca blanca"

        Contaminated aluminum can:
            primary_bin=WHITE, recommendation_type=CONDITIONAL,
            instruction="Enjuaga antes de reciclar",
            alternative_bin=BLACK,
            condition_message="Si está limpio → BLANCO",
            alternative_message="Si tiene residuos → NEGRO"

        Unknown material:
            primary_bin=BLACK, recommendation_type=UNCERTAIN,
            instruction="No pudimos identificar el material con certeza"
    """

    primary_bin: BinColor
    recommendation_type: RecommendationType
    instruction: str
    alternative_bin: BinColor | None = None
    condition_message: str | None = None
    alternative_message: str | None = None

    def as_dict(self) -> dict:
        """Serialize to dictionary for JSON response."""
        result = {
            "primary_bin": self.primary_bin.value,
            "recommendation_type": self.recommendation_type.value,
            "instruction": self.instruction,
        }

        if self.alternative_bin:
            result["alternative_bin"] = self.alternative_bin.value
        if self.condition_message:
            result["condition_message"] = self.condition_message
        if self.alternative_message:
            result["alternative_message"] = self.alternative_message

        return result

    @property
    def is_conditional(self) -> bool:
        """Check if recommendation has conditional options."""
        return self.recommendation_type == RecommendationType.CONDITIONAL

    @property
    def requires_user_decision(self) -> bool:
        """Check if user needs to make a decision."""
        return self.alternative_bin is not None
