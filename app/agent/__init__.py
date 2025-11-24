"""
AI Agent Module - Contains AI-powered agents.

This module contains:
- MaterialClassifier: Single-model material classification agent
- ConsensusClassificationAgent: Multi-model ensemble learning agent (V4)

All other components are deterministic utilities in app/utils/classification/.
"""

from app.agent.consensus_classifier import ConsensusClassificationAgent
from app.agent.material_classifier import MaterialClassifier

__all__ = ["MaterialClassifier", "ConsensusClassificationAgent"]
