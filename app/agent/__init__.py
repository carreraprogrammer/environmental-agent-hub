"""
AI Agent Module - Contains the single AI-powered agent.

This module contains MaterialClassifier, the only true AI agent in the system.
All other components are deterministic utilities in app/utils/classification/.
"""

from app.agent.material_classifier import MaterialClassifier

__all__ = ["MaterialClassifier"]
