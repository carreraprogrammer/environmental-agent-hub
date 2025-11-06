"""Tests for adapter bytes processing (new feature)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from PIL import Image

from app.adapters.google_adapter import GoogleClassifierAdapter
from app.adapters.openai_adapter import OpenAIClassifierAdapter
from app.adapters.roboflow_adapter import RoboflowClassifierAdapter
from app.schemas.domain import WasteMaterial


def create_test_image_bytes() -> bytes:
    """Create a simple test image as bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()


@pytest.mark.asyncio
async def test_openai_classify_from_bytes():
    """Test OpenAI adapter can classify from bytes."""
    image_bytes = create_test_image_bytes()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "PLASTIC"

    with patch("app.adapters.openai_adapter.AsyncOpenAI") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance

        adapter = OpenAIClassifierAdapter(model="gpt-4o")
        result = await adapter.classify(image_bytes, trace_id="test-123")

        assert result.material == WasteMaterial.PLASTIC
        assert result.confidence > 0
        assert result.model_provider == "openai"

        # Verify base64 conversion happened
        call_args = mock_instance.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        image_url = messages[0]["content"][1]["image_url"]["url"]
        assert image_url.startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_openai_classify_from_url_still_works():
    """Test OpenAI adapter backward compatibility with URLs."""
    image_url = "https://example.com/image.jpg"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "PAPER"

    with patch("app.adapters.openai_adapter.AsyncOpenAI") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance

        adapter = OpenAIClassifierAdapter(model="gpt-4o")
        result = await adapter.classify(image_url, trace_id="test-456")

        assert result.material == WasteMaterial.PAPER
        assert result.confidence > 0

        # Verify URL was passed directly
        call_args = mock_instance.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        passed_url = messages[0]["content"][1]["image_url"]["url"]
        assert passed_url == image_url


@pytest.mark.asyncio
async def test_google_classify_from_bytes():
    """Test Google adapter can classify from bytes."""
    image_bytes = create_test_image_bytes()

    mock_response = MagicMock()
    mock_response.text = "GLASS"

    with patch("app.adapters.google_adapter.genai") as mock_genai:
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        adapter = GoogleClassifierAdapter(model="gemini-2.0-flash-exp")
        result = await adapter.classify(image_bytes, trace_id="test-789")

        assert result.material == WasteMaterial.GLASS
        assert result.confidence == 0.80
        assert result.model_provider == "google"

        # Verify PIL.Image was created from bytes
        call_args = mock_model.generate_content_async.call_args
        content = call_args.args[0]
        # Second item should be PIL Image
        assert len(content) == 2
        # We can't easily check if it's a PIL.Image in the mock, but it should not be a dict


@pytest.mark.asyncio
async def test_google_classify_from_url_still_works():
    """Test Google adapter backward compatibility with URLs."""
    image_url = "https://example.com/bottle.jpg"
    fake_image_data = create_test_image_bytes()

    mock_response = MagicMock()
    mock_response.text = "METAL"

    with (
        patch("app.adapters.google_adapter.genai") as mock_genai,
        patch("app.adapters.google_adapter.httpx.AsyncClient") as mock_client,
    ):
        # Mock HTTP download
        mock_http_response = MagicMock()
        mock_http_response.content = fake_image_data
        mock_http_response.headers = {"content-type": "image/jpeg"}
        mock_http_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_http_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        mock_client.return_value = mock_client_instance

        # Mock Gemini
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        adapter = GoogleClassifierAdapter(model="gemini-2.0-flash-exp")
        result = await adapter.classify(image_url, trace_id="test-101")

        assert result.material == WasteMaterial.METAL
        assert result.confidence == 0.80

        # Verify URL was downloaded
        mock_client_instance.get.assert_called_once_with(image_url)


@pytest.mark.asyncio
async def test_roboflow_classify_from_bytes():
    """Test Roboflow adapter can classify from bytes."""
    image_bytes = create_test_image_bytes()

    mock_prediction = MagicMock()
    mock_prediction.predictions = [
        MagicMock(class_name="plastic", confidence=0.92)
    ]

    with patch("app.adapters.roboflow_adapter.Roboflow") as mock_roboflow:
        # Mock the chain: Roboflow().workspace().project().version().model
        mock_model = MagicMock()
        mock_model.predict = Mock(return_value=mock_prediction)

        mock_version = MagicMock()
        mock_version.model = mock_model

        mock_project = MagicMock()
        mock_project.version.return_value = mock_version

        mock_workspace = MagicMock()
        mock_workspace.project.return_value = mock_project

        mock_rf_instance = MagicMock()
        mock_rf_instance.workspace.return_value = mock_workspace
        mock_roboflow.return_value = mock_rf_instance

        adapter = RoboflowClassifierAdapter(
            model_id="test-workspace/test-project/1"
        )
        result = await adapter.classify(image_bytes, trace_id="test-rf-bytes")

        assert result.material == WasteMaterial.PLASTIC
        assert result.confidence == 0.92
        assert result.model_provider == "roboflow"

        # Verify predict was called with a file path (temp file)
        mock_model.predict.assert_called_once()
        call_args = mock_model.predict.call_args
        predicted_path = call_args.args[0]
        assert isinstance(predicted_path, str)
        # Should be a temp file path, not a URL
        assert not predicted_path.startswith("http")


@pytest.mark.asyncio
async def test_roboflow_classify_from_url_still_works():
    """Test Roboflow adapter backward compatibility with URLs."""
    image_url = "https://example.com/can.jpg"

    mock_prediction = MagicMock()
    mock_prediction.predictions = [
        MagicMock(class_name="metal", confidence=0.88)
    ]

    with patch("app.adapters.roboflow_adapter.Roboflow") as mock_roboflow:
        mock_model = MagicMock()
        mock_model.predict = Mock(return_value=mock_prediction)

        mock_version = MagicMock()
        mock_version.model = mock_model

        mock_project = MagicMock()
        mock_project.version.return_value = mock_version

        mock_workspace = MagicMock()
        mock_workspace.project.return_value = mock_project

        mock_rf_instance = MagicMock()
        mock_rf_instance.workspace.return_value = mock_workspace
        mock_roboflow.return_value = mock_rf_instance

        adapter = RoboflowClassifierAdapter(
            model_id="test-workspace/test-project/1"
        )
        result = await adapter.classify(image_url, trace_id="test-rf-url")

        assert result.material == WasteMaterial.METAL
        assert result.confidence == 0.88

        # Verify predict was called with URL and hosted=True
        mock_model.predict.assert_called_once()
        call_args = mock_model.predict.call_args
        assert call_args.args[0] == image_url
        assert call_args.kwargs.get("hosted") is True
