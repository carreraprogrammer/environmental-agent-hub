"""
Classifier factory placeholder.
"""

from __future__ import annotations

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.base import AdapterNotConfiguredError, ClassifierAdapter
from app.adapters.google_adapter import GoogleAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.roboflow_adapter import RoboflowAdapter
from app.core.config import settings


def get_classifier_adapter() -> ClassifierAdapter:
    """
    Resolve classifier adapter based on configuration.
    
    Returns:
        ClassifierAdapter: Configured adapter instance
    
    Raises:
        AdapterNotConfiguredError: If adapter is not supported
    """
    model = settings.CLASSIFIER_MODEL
    if model in {"openai-gpt4", "openai-gpt4o"}:
        return OpenAIAdapter()
    if model == "claude":
        return AnthropicAdapter()
    if model == "gemini":
        return GoogleAdapter()
    if model == "roboflow":
        return RoboflowAdapter()
    raise AdapterNotConfiguredError(model)
