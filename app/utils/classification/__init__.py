"""
Classification Utilities Module - Deterministic utilities for classification pipeline.

ARCHITECTURE NOTE: These are NOT AI agents, they are deterministic utilities.
- ColorMapper: Material -> bin color lookup (NTC 24 standard)
- WasteTypeMatcher: Material -> waste_type_code matching
- ResponseAssembler: JSON response construction
- FeedbackGenerator: Template-based educational messages

The only AI agent is MaterialClassifier in app/agent/.
"""

from app.utils.classification.color_mapper import ColorMapper
from app.utils.classification.response_assembler import ResponseAssembler
from app.utils.classification.waste_type_matcher import WasteTypeMatcher

__all__ = [
    "ColorMapper",
    "WasteTypeMatcher",
    "ResponseAssembler",
]
