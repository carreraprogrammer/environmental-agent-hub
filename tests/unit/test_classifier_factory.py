"""Unit tests for the ClassifierFactory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.factories.classifier_factory import ClassifierFactory


@pytest.fixture(autouse=True)
def reset_classifier_settings():
    """Reset classifier settings before each test."""
    from app.core.config import settings

    settings.CLASSIFIER_MODEL = "openai-gpt4"
    yield


class TestClassifierFactoryCreate:
    """Test suite for ClassifierFactory.create() method."""

    @patch("app.adapters.openai_adapter.AsyncOpenAI")
    def test_create_openai_gpt4_from_settings(self, mock_openai_client):
        """Test creating OpenAI GPT-4 adapter from settings."""
        from app.core.config import settings

        settings.CLASSIFIER_MODEL = "openai-gpt4"
        adapter = ClassifierFactory.create()

        assert adapter is not None
        assert adapter.model == "gpt-4-vision-preview"

    @patch("app.adapters.openai_adapter.AsyncOpenAI")
    def test_create_openai_gpt4o_with_override(self, mock_openai_client):
        """Test creating OpenAI GPT-4o adapter with model override."""
        adapter = ClassifierFactory.create(model_override="openai-gpt4o")

        assert adapter is not None
        assert adapter.model == "gpt-4o"

    @patch("app.adapters.google_adapter.genai")
    def test_create_gemini_adapter(self, mock_genai):
        """Test creating Gemini adapter."""
        from app.core.config import settings

        settings.GOOGLE_API_KEY = "test-key"
        adapter = ClassifierFactory.create(model_override="gemini")

        assert adapter is not None
        assert adapter.model_provider == "google"

    @patch("app.adapters.roboflow_adapter.Roboflow")
    def test_create_roboflow_adapter(self, mock_roboflow):
        """Test creating Roboflow adapter."""
        from app.core.config import settings

        settings.ROBOFLOW_API_KEY = "test-key"
        settings.ROBOFLOW_MODEL_ID = "workspace/project/1"

        # Mock the Roboflow client chain
        mock_client = mock_roboflow.return_value
        mock_workspace = mock_client.workspace.return_value
        mock_project = mock_workspace.project.return_value
        mock_version = mock_project.version.return_value
        mock_version.model = "mock_model"

        adapter = ClassifierFactory.create(model_override="roboflow")

        assert adapter is not None
        assert adapter.model_provider == "roboflow"

    @patch("app.factories.classifier_factory.logger")
    def test_create_claude_adapter_with_warning(self, mock_logger):
        """Test creating Claude adapter triggers warning about placeholder implementation."""
        adapter = ClassifierFactory.create(model_override="claude")

        assert adapter is not None
        assert adapter.model_provider == "anthropic"
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "classifier_factory_unsupported" in warning_call[0]

    def test_create_invalid_model_raises_value_error(self):
        """Test that invalid model identifier raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ClassifierFactory.create(model_override="invalid-model")

        error_message = str(exc_info.value)
        assert "Unsupported model 'invalid-model'" in error_message
        assert "openai-gpt4" in error_message
        assert "gemini" in error_message
        assert "roboflow" in error_message

    @patch("app.adapters.openai_adapter.AsyncOpenAI")
    def test_create_with_case_insensitive_model(self, mock_openai_client):
        """Test that model identifiers are case-insensitive."""
        adapter = ClassifierFactory.create(model_override="OPENAI-GPT4")

        assert adapter is not None
        assert adapter.model == "gpt-4-vision-preview"

    @patch("app.adapters.openai_adapter.AsyncOpenAI")
    def test_create_with_whitespace_in_model(self, mock_openai_client):
        """Test that whitespace in model identifiers is stripped."""
        adapter = ClassifierFactory.create(model_override="  openai-gpt4  ")

        assert adapter is not None
        assert adapter.model == "gpt-4-vision-preview"

    @patch("app.factories.classifier_factory.logger")
    @patch("app.adapters.openai_adapter.AsyncOpenAI")
    def test_create_logs_adapter_creation(self, mock_openai_client, mock_logger):
        """Test that adapter creation is logged."""
        ClassifierFactory.create(model_override="openai-gpt4")

        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "classifier_factory_create" in log_call[0]


class TestClassifierFactoryListAvailable:
    """Test suite for ClassifierFactory.list_available() method."""

    def test_list_available_returns_all_models(self):
        """Test that list_available returns all supported models."""
        available_models = ClassifierFactory.list_available()

        assert isinstance(available_models, list)
        assert len(available_models) == 5
        assert "openai-gpt4" in available_models
        assert "openai-gpt4o" in available_models
        assert "claude" in available_models
        assert "gemini" in available_models
        assert "roboflow" in available_models

    def test_list_available_returns_copy(self):
        """Test that list_available returns a new list each time."""
        models_1 = ClassifierFactory.list_available()
        models_2 = ClassifierFactory.list_available()

        assert models_1 == models_2
        assert models_1 is not models_2


class TestClassifierFactoryIntegration:
    """Integration tests for ClassifierFactory with real adapter classes."""

    @patch("app.adapters.openai_adapter.AsyncOpenAI")
    def test_integration_create_openai_adapter(self, mock_client):
        """Test integration with real OpenAIClassifierAdapter class."""
        adapter = ClassifierFactory.create(model_override="openai-gpt4")

        assert isinstance(adapter, OpenAIClassifierAdapter)
        assert adapter.model == "gpt-4-vision-preview"

    @patch("app.adapters.google_adapter.genai")
    def test_integration_create_google_adapter(self, mock_genai):
        """Test integration with real GoogleClassifierAdapter class."""
        from app.core.config import settings

        settings.GOOGLE_API_KEY = "test-key"

        adapter = ClassifierFactory.create(model_override="gemini")

        assert isinstance(adapter, GoogleClassifierAdapter)

    def test_integration_create_anthropic_adapter(self):
        """Test integration with real AnthropicAdapter class."""
        adapter = ClassifierFactory.create(model_override="claude")

        assert isinstance(adapter, AnthropicAdapter)

    @patch("app.adapters.roboflow_adapter.Roboflow")
    def test_integration_create_roboflow_adapter(self, mock_roboflow):
        """Test integration with real RoboflowClassifierAdapter class."""
        from app.core.config import settings

        settings.ROBOFLOW_API_KEY = "test-key"
        settings.ROBOFLOW_MODEL_ID = "workspace/project/1"

        # Mock the Roboflow client chain
        mock_client = mock_roboflow.return_value
        mock_workspace = mock_client.workspace.return_value
        mock_project = mock_workspace.project.return_value
        mock_version = mock_project.version.return_value
        mock_version.model = "mock_model"

        adapter = ClassifierFactory.create(model_override="roboflow")

        assert isinstance(adapter, RoboflowClassifierAdapter)
