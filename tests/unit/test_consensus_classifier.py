"""
Unit tests for ConsensusClassificationAgent V4.

Covers 5 main scenarios per acceptance criteria CA-4.1:
1. High confidence (fast path - primary model only)
2. Agreement boost (both models agree)
3. Disagreement confidence-based (difference > 0.15)
4. Disagreement tie-breaker (difference < 0.15)
5. No consensus (all 3 disagree, fallback to OTHER)

Coverage target: >85% for consensus_classifier.py
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.base import ClassifierAdapter
from app.agent.consensus_classifier import ConsensusClassificationAgent
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


class DummyAdapter(ClassifierAdapter):
    """Simple adapter stub for testing ConsensusClassificationAgent."""

    def __init__(self, model_name: str = "dummy-model") -> None:
        self._model_name = model_name

    async def classify(self, image_url: str, *, trace_id: str | None = None):  # type: ignore[override]
        raise NotImplementedError("V3 classify() not used in tests")

    async def classify_material(
        self, image_data: bytes, *, trace_id: str | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError("Use mock instead")

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return self._model_name

    @property
    def model_provider(self) -> str:  # type: ignore[override]
        return "dummy"

    @property
    def cost_per_request(self) -> float:  # type: ignore[override]
        return 0.010


def _create_classification_result(
    material: Material,
    confidence: float,
    cost: float = 0.010,
    model: str = "test-model",
) -> MaterialClassificationResult:
    """Helper to create MaterialClassificationResult for testing."""
    return MaterialClassificationResult(
        material=MaterialField(material_type=material, confidence=confidence),
        subtype=SubtypeField(value="PET", recycling_code="#1", confidence=0.85),
        condition=ConditionField(value=PhysicalCondition.CLEAN, confidence=0.8),
        volume=VolumeField(liters=0.5, source=VolumeSource.ESTIMATED, confidence=0.7),
        recyclability=RecyclabilityField(value=Recyclability.RECYCLABLE, confidence=0.9),
        reasoning="Test classification",
        timestamp=None,  # type: ignore
        cost=cost,
        model_used=model,
        model_provider="test",
        partial_success=False,
        metadata={},
    )


@pytest.mark.asyncio
async def test_high_confidence_fast_path() -> None:
    """
    Scenario 1: High confidence (≥0.70) → Fast path (primary model only).

    Expected:
    - Only primary model is called
    - Secondary/tiebreaker NOT called
    - Result returned immediately
    - Metadata: consensus_strategy="fast_path", consensus_triggered=False
    """
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock primary classifier to return high confidence result
    high_conf_result = _create_classification_result(Material.PLASTIC, 0.85)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary:
        mock_primary.return_value = high_conf_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-fast-path")

        # Assert
        assert mock_primary.call_count == 1  # Primary called
        assert result.material.material_type == Material.PLASTIC
        assert result.material.confidence == pytest.approx(0.85)
        assert result.metadata["consensus_strategy"] == "fast_path"
        assert result.metadata["consensus_triggered"] is False
        assert result.metadata["models_consulted"] == 1


@pytest.mark.asyncio
async def test_agreement_boost_strategy() -> None:
    """
    Scenario 2: Both models agree on material → Agreement boost.

    Expected:
    - Primary: PLASTIC, 0.65 (below threshold)
    - Secondary: PLASTIC, 0.68 (agrees)
    - Weighted avg: 0.65*0.6 + 0.68*0.4 = 0.662
    - Final: 0.662 + 0.10 (bonus) = 0.762
    - Metadata: consensus_strategy="agreement_boost", models_consulted=2
    """
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock results
    primary_result = _create_classification_result(Material.PLASTIC, 0.65)
    secondary_result = _create_classification_result(Material.PLASTIC, 0.68)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-agreement")

        # Assert
        assert mock_primary.call_count == 1
        assert mock_secondary.call_count == 1
        assert result.material.material_type == Material.PLASTIC
        # Expected: (0.65*0.6 + 0.68*0.4) + 0.10 = 0.762
        assert result.material.confidence == pytest.approx(0.762, abs=0.01)
        assert result.metadata["consensus_strategy"] == "agreement_boost"
        assert result.metadata["consensus_triggered"] is True
        assert result.metadata["models_consulted"] == 2


@pytest.mark.asyncio
async def test_confidence_based_strategy() -> None:
    """
    Scenario 3: Models disagree, confidence diff > 0.15 → Confidence-based.

    Expected:
    - Primary: PLASTIC, 0.65
    - Secondary: METAL, 0.45 (diff = 0.20 > 0.15)
    - Winner: Primary (higher confidence)
    - Final: 0.65 * 0.90 (penalty) = 0.585
    - Metadata: consensus_strategy="confidence_based"
    """
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock results (disagree, diff > 0.15)
    primary_result = _create_classification_result(Material.PLASTIC, 0.65)
    secondary_result = _create_classification_result(Material.METAL, 0.45)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-confidence-based")

        # Assert
        assert mock_primary.call_count == 1
        assert mock_secondary.call_count == 1
        assert result.material.material_type == Material.PLASTIC  # Winner
        assert result.material.confidence == pytest.approx(0.585, abs=0.01)  # 0.65 * 0.9
        assert result.metadata["consensus_strategy"] == "confidence_based"
        assert result.metadata["consensus_triggered"] is True
        assert result.metadata["models_consulted"] == 2


@pytest.mark.asyncio
async def test_tiebreaker_vote_strategy() -> None:
    """
    Scenario 4: Models disagree, confidence diff < 0.15 → Tie-breaker vote.

    Expected:
    - Primary: PLASTIC, 0.60
    - Secondary: METAL, 0.58 (diff = 0.02 < 0.15)
    - Tiebreaker: PLASTIC, 0.62
    - Votes: PLASTIC=2, METAL=1 → PLASTIC wins
    - Final: avg(0.60, 0.62) * 0.85 (penalty) = 0.517
    - Metadata: consensus_strategy="tie_breaker", models_consulted=3
    """
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock results (disagree, diff < 0.15)
    primary_result = _create_classification_result(Material.PLASTIC, 0.60)
    secondary_result = _create_classification_result(Material.METAL, 0.58)
    tiebreaker_result = _create_classification_result(Material.PLASTIC, 0.62)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary, patch.object(
        consensus.tiebreaker_classifier, "classify", new_callable=AsyncMock
    ) as mock_tiebreaker:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result
        mock_tiebreaker.return_value = tiebreaker_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-tiebreaker")

        # Assert
        assert mock_primary.call_count == 1
        assert mock_secondary.call_count == 1
        assert mock_tiebreaker.call_count == 1
        assert result.material.material_type == Material.PLASTIC  # Winner (2 votes)
        # Expected: avg(0.60, 0.62) * 0.85 = 0.517
        assert result.material.confidence == pytest.approx(0.517, abs=0.01)
        assert result.metadata["consensus_strategy"] == "tie_breaker"
        assert result.metadata["consensus_triggered"] is True
        assert result.metadata["models_consulted"] == 3


@pytest.mark.asyncio
async def test_no_consensus_fallback() -> None:
    """
    Scenario 5: All 3 models disagree → Fallback to OTHER.

    Expected:
    - Primary: PLASTIC, 0.60
    - Secondary: METAL, 0.58
    - Tiebreaker: GLASS, 0.61
    - No majority (all different) → Fallback
    - Result: Material.OTHER, confidence=0.50
    - Metadata: consensus_strategy="fallback_no_consensus"
    """
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock results (all disagree)
    primary_result = _create_classification_result(Material.PLASTIC, 0.60)
    secondary_result = _create_classification_result(Material.METAL, 0.58)
    tiebreaker_result = _create_classification_result(Material.GLASS, 0.61)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary, patch.object(
        consensus.tiebreaker_classifier, "classify", new_callable=AsyncMock
    ) as mock_tiebreaker:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result
        mock_tiebreaker.return_value = tiebreaker_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-fallback")

        # Assert
        assert mock_primary.call_count == 1
        assert mock_secondary.call_count == 1
        assert mock_tiebreaker.call_count == 1
        assert result.material.material_type == Material.OTHER  # Fallback
        assert result.material.confidence == pytest.approx(0.50)
        assert result.metadata["consensus_strategy"] == "fallback_no_consensus"
        assert result.metadata["consensus_triggered"] is True
        assert result.metadata["models_consulted"] == 3


@pytest.mark.asyncio
async def test_custom_uncertainty_threshold() -> None:
    """Test that custom uncertainty threshold works correctly."""
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    # Use custom threshold of 0.80 (higher than default 0.70)
    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.80,
    )

    # Mock primary result with confidence 0.75 (would be fast path with default 0.70)
    primary_result = _create_classification_result(Material.PLASTIC, 0.75)
    secondary_result = _create_classification_result(Material.PLASTIC, 0.78)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-custom-threshold")

        # Assert - should trigger consensus because 0.75 < 0.80
        assert mock_primary.call_count == 1
        assert mock_secondary.call_count == 1  # Consensus triggered
        assert result.metadata["consensus_triggered"] is True


@pytest.mark.asyncio
async def test_consensus_metadata_logging() -> None:
    """Test that consensus metadata is properly logged and included."""
    # Arrange
    primary_adapter = DummyAdapter("gpt-4o")
    secondary_adapter = DummyAdapter("gemini")
    tiebreaker_adapter = DummyAdapter("roboflow")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock agreement scenario
    primary_result = _create_classification_result(Material.PLASTIC, 0.65)
    secondary_result = _create_classification_result(Material.PLASTIC, 0.67)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-metadata")

        # Assert - check all expected metadata fields
        assert "consensus_strategy" in result.metadata
        assert "consensus_triggered" in result.metadata
        assert "models_consulted" in result.metadata
        assert "primary_confidence" in result.metadata
        assert "primary_material" in result.metadata
        assert "primary_model" in result.metadata
        assert "secondary_confidence" in result.metadata
        assert "secondary_material" in result.metadata
        assert "secondary_model" in result.metadata

        assert result.metadata["primary_confidence"] == 0.65
        assert result.metadata["secondary_confidence"] == 0.67
        assert result.metadata["primary_model"] == "gpt-4o"
        assert result.metadata["secondary_model"] == "gemini"


@pytest.mark.asyncio
async def test_consensus_cost_calculation() -> None:
    """Test that total cost is correctly calculated for consensus scenarios."""
    # Arrange
    primary_adapter = DummyAdapter("primary-model")
    secondary_adapter = DummyAdapter("secondary-model")
    tiebreaker_adapter = DummyAdapter("tiebreaker-model")

    consensus = ConsensusClassificationAgent(
        primary_adapter=primary_adapter,
        secondary_adapter=secondary_adapter,
        tiebreaker_adapter=tiebreaker_adapter,
        uncertainty_threshold=0.70,
    )

    # Mock tiebreaker scenario (3 models = 3 costs)
    primary_result = _create_classification_result(Material.PLASTIC, 0.60, cost=0.010)
    secondary_result = _create_classification_result(Material.METAL, 0.58, cost=0.001)
    tiebreaker_result = _create_classification_result(Material.PLASTIC, 0.62, cost=0.001)

    with patch.object(
        consensus.primary_classifier, "classify", new_callable=AsyncMock
    ) as mock_primary, patch.object(
        consensus.secondary_classifier, "classify", new_callable=AsyncMock
    ) as mock_secondary, patch.object(
        consensus.tiebreaker_classifier, "classify", new_callable=AsyncMock
    ) as mock_tiebreaker:
        mock_primary.return_value = primary_result
        mock_secondary.return_value = secondary_result
        mock_tiebreaker.return_value = tiebreaker_result

        # Act
        result = await consensus.classify(b"fake-image", "trace-cost")

        # Assert - total cost should be sum of all 3 models
        expected_cost = 0.010 + 0.001 + 0.001  # 0.012
        assert result.cost == pytest.approx(expected_cost, abs=0.001)
