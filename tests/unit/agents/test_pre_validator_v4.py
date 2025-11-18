"""
Unit tests for PreValidator Agent V4.

Covers:
- ValidationResult V4 schema (is_valid, reason, metadata, cost, fallback_used)
- Layer 1 technical validations (format, size, dimensions)
- Layer 2 Roboflow Object Detection integration (detections vs no detections)
- Fallback behaviour on Roboflow timeout/error
- Logging of Roboflow metadata (classes, confidences, detections)
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from PIL import Image
import pytest

from app.agents.pre_validator import PreValidator
from app.schemas.classification import ValidationReason, ValidationResult


def make_image_bytes(
    width: int = 256,
    height: int = 256,
    fmt: str = "JPEG",
) -> bytes:
    """Create a simple in-memory image and return its bytes."""
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Roboflow settings for tests."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROBOFLOW_MODEL_ID", "workspace/project/1", raising=False)
    monkeypatch.setattr(settings, "ROBOFLOW_API_KEY", "test-key", raising=False)


@pytest.fixture
def validator_with_mock_model(monkeypatch: pytest.MonkeyPatch) -> tuple[PreValidator, Any]:
    """Create PreValidator with a mocked Roboflow model to avoid network."""

    class DummyModel:
        def __init__(self) -> None:
            self.predictions: list[Any] = []

        def predict(self, *_args: Any, **_kwargs: Any) -> Any:
            return SimpleNamespace(predictions=self.predictions)

    dummy_model = DummyModel()

    class DummyVersion:
        def __init__(self) -> None:
            self.model = dummy_model

    class DummyProject:
        def version(self, _version: str) -> DummyVersion:
            return DummyVersion()

    class DummyWorkspace:
        def project(self, _project: str) -> DummyProject:
            return DummyProject()

    class DummyRoboflow:
        def __init__(self, api_key: str) -> None:  # noqa: ARG002 - for interface
            self._workspace = DummyWorkspace()

        def workspace(self, _workspace: str) -> DummyWorkspace:
            return self._workspace

    monkeypatch.setattr("app.agents.pre_validator.Roboflow", DummyRoboflow)

    validator = PreValidator(model_id="workspace/project/1")

    # Replace model with our dummy model (for clarity)
    validator.model = dummy_model
    return validator, dummy_model


class TestValidationResultSchema:
    """Tests for ValidationResult V4 schema."""

    def test_validation_result_defaults(self) -> None:
        result = ValidationResult(
            is_valid=True,
            reason=ValidationReason.WASTE_DETECTED,
        )

        assert result.is_valid is True
        assert result.reason == ValidationReason.WASTE_DETECTED
        assert result.metadata == {}
        assert result.cost == 0.001
        assert result.fallback_used is False

    def test_validation_result_custom_metadata_and_cost(self) -> None:
        result = ValidationResult(
            is_valid=False,
            reason=ValidationReason.NO_WASTE_DETECTED,
            metadata={"detections": [], "num_detections": 0},
            cost=0.002,
            fallback_used=True,
        )

        assert result.is_valid is False
        assert result.reason == ValidationReason.NO_WASTE_DETECTED
        assert result.metadata["num_detections"] == 0
        assert result.cost == 0.002
        assert result.fallback_used is True


class TestTechnicalValidation:
    """Layer 1: technical validations (format, size, dimensions)."""

    def test_empty_image_rejected(self, validator_with_mock_model: tuple[PreValidator, Any]) -> None:
        validator, _ = validator_with_mock_model

        result = validator._validate_technical(b"", "trace-empty")

        assert result.is_valid is False
        assert result.reason == ValidationReason.EMPTY_IMAGE
        assert result.metadata["size_bytes"] == 0

    def test_large_image_rejected_by_size(self, validator_with_mock_model: tuple[PreValidator, Any]) -> None:
        validator, _ = validator_with_mock_model

        large_bytes = b"x" * (11 * 1024 * 1024)  # >10MB
        result = validator._validate_technical(large_bytes, "trace-large")

        assert result.is_valid is False
        assert result.reason == ValidationReason.INVALID_SIZE
        assert result.metadata["max_size_mb"] == validator.MAX_IMAGE_SIZE_MB

    def test_invalid_format_rejected(self, validator_with_mock_model: tuple[PreValidator, Any]) -> None:
        validator, _ = validator_with_mock_model

        result = validator._validate_technical(b"not-an-image", "trace-format")

        assert result.is_valid is False
        assert result.reason == ValidationReason.INVALID_FORMAT

    def test_small_dimensions_rejected(self, validator_with_mock_model: tuple[PreValidator, Any]) -> None:
        validator, _ = validator_with_mock_model

        small_image = make_image_bytes(width=100, height=100)
        result = validator._validate_technical(small_image, "trace-small")

        assert result.is_valid is False
        assert result.reason == ValidationReason.INVALID_DIMENSIONS
        assert result.metadata["width"] == 100
        assert result.metadata["height"] == 100

    def test_valid_image_passes_layer1(self, validator_with_mock_model: tuple[PreValidator, Any]) -> None:
        validator, _ = validator_with_mock_model

        image_bytes = make_image_bytes(256, 256)
        result = validator._validate_technical(image_bytes, "trace-valid")

        assert result.is_valid is True
        assert result.reason == ValidationReason.WASTE_DETECTED
        assert result.metadata["width"] == 256
        assert result.metadata["height"] == 256


class TestRoboflowConfig:
    """Roboflow configuration (model_id and thresholds)."""

    def test_roboflow_config_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "ROBOFLOW_MODEL_ID", "workspace/default/6", raising=False)

        class DummyWorkspace:
            def project(self, _project: str) -> Any:
                return SimpleNamespace(version=lambda _v: SimpleNamespace(model=object()))

        class DummyRoboflow:
            def __init__(self, api_key: str) -> None:  # noqa: ARG002
                self._workspace = DummyWorkspace()

            def workspace(self, _workspace: str) -> DummyWorkspace:
                return self._workspace

        monkeypatch.setattr("app.agents.pre_validator.Roboflow", DummyRoboflow)

        validator = PreValidator()

        assert validator.model_id == "workspace/default/6"
        assert validator.confidence_threshold == PreValidator.ROBOFLOW_CONFIDENCE_THRESHOLD
        assert validator.overlap_threshold == PreValidator.ROBOFLOW_OVERLAP_THRESHOLD

    def test_roboflow_config_custom_thresholds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "ROBOFLOW_MODEL_ID", "workspace/custom/2", raising=False)

        class DummyWorkspace:
            def project(self, _project: str) -> Any:
                return SimpleNamespace(version=lambda _v: SimpleNamespace(model=object()))

        class DummyRoboflow:
            def __init__(self, api_key: str) -> None:  # noqa: ARG002
                self._workspace = DummyWorkspace()

            def workspace(self, _workspace: str) -> DummyWorkspace:
                return self._workspace

        monkeypatch.setattr("app.agents.pre_validator.Roboflow", DummyRoboflow)

        validator = PreValidator(
            confidence_threshold=0.5,
            overlap_threshold=0.6,
        )

        assert validator.model_id == "workspace/custom/2"
        assert validator.confidence_threshold == 0.5
        assert validator.overlap_threshold == 0.6


class TestRoboflowWasteDetection:
    """Layer 2: Roboflow Object Detection integration."""

    @pytest.mark.asyncio
    async def test_accepts_waste_when_detections_present(
        self,
        validator_with_mock_model: tuple[PreValidator, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        validator, dummy_model = validator_with_mock_model

        # One detection with high confidence
        dummy_model.predictions = [
            SimpleNamespace(
                class_name="plastic_bottle",
                confidence=0.9,
                x=10,
                y=20,
                width=30,
                height=40,
            )
        ]

        async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
            return func(*args, **kwargs)

        monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

        image_bytes = make_image_bytes()
        result = await validator._detect_waste_roboflow(image_bytes, "trace-waste")

        assert result.is_valid is True
        assert result.reason == ValidationReason.WASTE_DETECTED
        assert result.metadata["num_detections"] == 1
        assert "detections" in result.metadata
        assert "classes" in result.metadata
        assert result.metadata["classes"] == ["plastic_bottle"]

    @pytest.mark.asyncio
    async def test_rejects_no_waste_when_no_detections(
        self,
        validator_with_mock_model: tuple[PreValidator, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        validator, dummy_model = validator_with_mock_model

        dummy_model.predictions = []

        async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
            return func(*args, **kwargs)

        monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

        image_bytes = make_image_bytes()
        result = await validator._detect_waste_roboflow(image_bytes, "trace-no-waste")

        assert result.is_valid is False
        assert result.reason == ValidationReason.NO_WASTE_DETECTED
        assert result.metadata["num_detections"] == 0
        assert result.metadata["detections"] == []


class TestTwoLayerValidation:
    """End-to-end two-layer validation behaviour."""

    @pytest.mark.asyncio
    async def test_two_layer_validation_success(
        self,
        validator_with_mock_model: tuple[PreValidator, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        validator, dummy_model = validator_with_mock_model

        dummy_model.predictions = [
            SimpleNamespace(
                class_name="plastic_bottle",
                confidence=0.9,
                x=10,
                y=20,
                width=30,
                height=40,
            )
        ]

        async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
            return func(*args, **kwargs)

        monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

        image_bytes = make_image_bytes()
        result = await validator.validate(image_bytes, "trace-two-layer")

        assert result.is_valid is True
        assert result.reason == ValidationReason.WASTE_DETECTED
        assert result.metadata.get("num_detections") == 1


class TestRoboflowFallback:
    """Fallback behaviour when Roboflow API fails or times out."""

    @pytest.mark.asyncio
    async def test_roboflow_timeout_fallback(
        self,
        validator_with_mock_model: tuple[PreValidator, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        validator, _ = validator_with_mock_model

        async def fake_wait_for(*_args, **_kwargs):  # type: ignore[override]
            raise asyncio.TimeoutError()

        monkeypatch.setattr("app.agents.pre_validator.asyncio.wait_for", fake_wait_for)

        image_bytes = make_image_bytes()
        result = await validator.validate(image_bytes, "trace-timeout")

        assert result.is_valid is True
        assert result.reason == ValidationReason.WASTE_DETECTED
        assert result.fallback_used is True
        assert result.cost == 0.0
        assert result.metadata.get("fallback_reason") == "roboflow_timeout"

    @pytest.mark.asyncio
    async def test_roboflow_error_fallback(
        self,
        validator_with_mock_model: tuple[PreValidator, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        validator, _ = validator_with_mock_model

        async def fake_wait_for(*_args, **_kwargs):  # type: ignore[override]
            raise RuntimeError("roboflow failure")

        monkeypatch.setattr("app.agents.pre_validator.asyncio.wait_for", fake_wait_for)

        image_bytes = make_image_bytes()
        result = await validator.validate(image_bytes, "trace-error")

        assert result.is_valid is True
        assert result.reason == ValidationReason.WASTE_DETECTED
        assert result.fallback_used is True
        assert result.cost == 0.0
        assert result.metadata.get("fallback_reason") == "roboflow_error"
        assert "roboflow failure" in result.metadata.get("error", "")


class TestRoboflowMetadataLogging:
    """Verify that Roboflow metadata is logged for analysis."""

    @pytest.mark.asyncio
    async def test_roboflow_metadata_logging(
        self,
        validator_with_mock_model: tuple[PreValidator, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        validator, dummy_model = validator_with_mock_model

        dummy_model.predictions = [
            SimpleNamespace(
                class_name="plastic_bottle",
                confidence=0.9,
                x=10,
                y=20,
                width=30,
                height=40,
            )
        ]

        async def fake_to_thread(func, *args, **kwargs):  # type: ignore[override]
            return func(*args, **kwargs)

        monkeypatch.setattr("app.agents.pre_validator.asyncio.to_thread", fake_to_thread)

        image_bytes = make_image_bytes()

        with patch("app.agents.pre_validator.logger") as mock_logger:
            await validator._detect_waste_roboflow(image_bytes, "trace-logging")

            # Look for pre_validator_roboflow_detections log
            info_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call[0][0] == "pre_validator_roboflow_detections"
            ]
            assert info_calls, "Expected pre_validator_roboflow_detections log entry"

            _, fields = info_calls[0]
            assert fields.get("num_detections") == 1
            assert fields.get("classes") == ["plastic_bottle"]
            assert fields.get("confidences") == [0.9]
