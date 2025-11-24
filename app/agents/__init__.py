"""
[DEPRECATED] Legacy agents module - Use new locations instead.

This module is DEPRECATED. The architecture has been refactored for honesty:

NEW LOCATIONS:
- MaterialClassifier (AI AGENT) ’ app.agent.material_classifier
- ColorMapper (UTIL) ’ app.utils.classification.color_mapper
- WasteTypeMatcher (UTIL) ’ app.utils.classification.waste_type_matcher
- ResponseAssembler (UTIL) ’ app.utils.classification.response_assembler

Imports below are provided for backward compatibility only.
Update your imports to use the new locations.
"""

# Backward compatibility imports
from app.agent.material_classifier import MaterialClassifier
from app.utils.classification.color_mapper import ColorMapper as Mapper
from app.utils.classification.response_assembler import ResponseAssembler as Assembler
from app.utils.classification.waste_type_matcher import WasteTypeMatcher as WasteTypeMapper

__all__ = [
    "MaterialClassifier",
    "Mapper",
    "Assembler",
    "WasteTypeMapper",
]
