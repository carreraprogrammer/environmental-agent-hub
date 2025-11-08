"""Factory for creating classifier adapter instances."""

from __future__ import annotations

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.base import ClassifierAdapter
from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.core.config import settings
from app.core.logging import logger


class ClassifierFactory:
    """Factory for creating classifier adapter instances based on configuration."""

    # Mapping of model identifiers to their adapter classes and initialization params
    _SUPPORTED_MODELS: dict[str, tuple[type[ClassifierAdapter], dict]] = {
        "openai-gpt4": (OpenAIClassifierAdapter, {"model": "gpt-4-vision-preview"}),
        "openai-gpt4o": (OpenAIClassifierAdapter, {"model": "gpt-4o"}),
        "claude": (AnthropicAdapter, {}),
        "gemini": (GoogleClassifierAdapter, {}),
        "roboflow": (RoboflowClassifierAdapter, {}),
    }

    @staticmethod
    def create(model_override: str | None = None) -> ClassifierAdapter:
        """
        Create a classifier adapter instance.

        Args:
            model_override: Optional model identifier to override settings.CLASSIFIER_MODEL.
                          If None, uses the model from settings.

        Returns:
            An initialized classifier adapter instance.

        Raises:
            ValueError: If the model identifier is not supported.

        Example:
            >>> factory = ClassifierFactory()
            >>> adapter = factory.create("openai-gpt4")
            >>> # Or use default from settings
            >>> adapter = factory.create()
        """
        model_id = model_override or settings.CLASSIFIER_MODEL
        model_id = model_id.strip().lower()

        if model_id not in ClassifierFactory._SUPPORTED_MODELS:
            available = list(ClassifierFactory._SUPPORTED_MODELS.keys())
            raise ValueError(
                f"Unsupported model '{model_id}'. Available models: {available}"
            )

        adapter_class, init_params = ClassifierFactory._SUPPORTED_MODELS[model_id]

        logger.info(
            "classifier_factory_create",
            model_id=model_id,
            adapter_class=adapter_class.__name__,
        )

        # Handle special case for claude model (not yet fully implemented)
        if model_id == "claude":
            logger.warning(
                "classifier_factory_unsupported",
                model_id=model_id,
                message="Anthropic adapter not yet fully implemented, returns placeholder responses",
            )

        return adapter_class(**init_params)

    @staticmethod
    def list_available() -> list[str]:
        """
        List all available classifier models.

        Returns:
            A list of supported model identifiers.

        Example:
            >>> ClassifierFactory.list_available()
            ['openai-gpt4', 'openai-gpt4o', 'claude', 'gemini', 'roboflow']
        """
        return list(ClassifierFactory._SUPPORTED_MODELS.keys())
