"""
Adapter package exports (lazy).

This module intentionally avoids importing concrete adapters at import
time to prevent circular dependencies with MaterialClassifier, which
defines the unified classification prompt used by the adapters.

Import adapters directly from their modules, for example:

    from app.adapters.openai_adapter import OpenAIClassifierAdapter
"""

from __future__ import annotations

__all__ = [
    "AnthropicAdapter",
    "GoogleClassifierAdapter",
    "OpenAIClassifierAdapter",
    "RoboflowClassifierAdapter",
]
