"""
Agents module - AI Agents + Utilities for waste classification.

ARCHITECTURE CLARITY (V4):

AI AGENTS (2):
- MaterialClassifier: Main classification agent (GPT-4o/Gemini/Claude)
- ConsensusClassificationAgent: Multi-model ensemble for uncertain cases

UTILITIES (Deterministic):
- pre_validator: Roboflow-based waste detection (anti-troll)
- waste_type_mapper: Material -> waste_type_code matching
- assembler: Response JSON construction
- mapper: Material -> bin color mapping
- router: Request routing logic
- feedback_coach: Educational message generation

For new imports, prefer explicit imports:
    from app.agents.material_classifier import MaterialClassifier
    from app.agents.consensus_classifier import ConsensusClassificationAgent
"""

# AI Agents
from app.agents.consensus_classifier import ConsensusClassificationAgent
from app.agents.material_classifier import MaterialClassifier

# Utilities (for backward compatibility)
from app.agents.assembler import Assembler
from app.agents.mapper import Mapper
from app.agents.pre_validator import PreValidator
from app.agents.waste_type_mapper import WasteTypeMapper

__all__ = [
    # AI Agents
    "MaterialClassifier",
    "ConsensusClassificationAgent",
    # Utilities
    "PreValidator",
    "WasteTypeMapper",
    "Mapper",
    "Assembler",
]
