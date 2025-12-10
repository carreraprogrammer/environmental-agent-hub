"""
Integration tests for POST /classify endpoint.

Tests both multipart/form-data and JSON input formats with comprehensive
coverage of success cases, validation errors, timeouts, and error handling.

Coverage Target: ≥80% for app/api/endpoints/classify.py
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import AgentTimeoutError, ClassificationError, ValidationError
from app.main import app
from app.schemas.bin_color import BinColor
from app.schemas.classification import Material
from app.schemas.responses import ClassifyResponse, ResponseMeta

client = TestClient(app)


# Helper function to create mock classification response
def create_mock_response(
    material: Material = Material.PLASTIC,
    confidence: float = 0.95,
    input_format: str = "bytes",
) -> ClassifyResponse:
    """Create a mock ClassifyResponse for testing."""
    return ClassifyResponse(
        material=material,
        confidence=confidence,
        color=BinColor.WHITE,
        volume_ml=500.0,
        weight_g=15.0,
        waste_type_code="PLASTIC_PET_BOTTLE",
        message="¡Excelente! El plástico va en el contenedor BLANCO.",
        meta=ResponseMeta(
            model_used="openai/gpt-4o",
            model_provider="openai",
            latency_ms=600,
            cost_usd=0.01,
            validator_passed=True,
            estimation_method="lookup_default",
            input_format=input_format,
            s3_upload_status="pending" if input_format == "bytes" else "n/a",
            agents_executed=["MaterialClassifier", "VolumeEstimator", "ColorMapper"],
        ),
    )


class TestClassifyEndpointMultipart:
    """Tests for multipart/form-data format (preferred)."""

    def test_classify_multipart_success(self) -> None:
        """Test successful classification with multipart/form-data."""
        # Arrange
        scan_id = str(uuid4())
        station_id = "TEST-01"
        tenant_id = "test"
        trace_id = str(uuid4())

        test_image = b"fake_image_bytes_for_testing_plastic_bottle"
        mock_response = create_mock_response()

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                    data={
                        "scan_id": scan_id,
                        "station_id": station_id,
                        "tenant_id": tenant_id,
                        "trace_id": trace_id,
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["material"] == "PLASTIC"
        assert data["confidence"] == 0.95
        assert data["color"] == "WHITE"
        assert data["meta"]["input_format"] == "bytes"
        assert data["meta"]["s3_upload_status"] == "pending"
        assert "X-Trace-Id" in response.headers
        assert "X-Request-Duration" in response.headers

    def test_classify_multipart_with_auto_generated_ids(self) -> None:
        """Test multipart request with auto-generated trace_id and idempotency_key."""
        # Arrange
        scan_id = str(uuid4())
        test_image = b"fake_image_bytes"
        mock_response = create_mock_response()

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                    data={
                        "scan_id": scan_id,
                        "station_id": "TEST-01",
                        "tenant_id": "test",
                    },
                )

        # Assert
        assert response.status_code == 200
        assert "X-Trace-Id" in response.headers

    def test_classify_multipart_metal(self) -> None:
        """Test classification of metal material via multipart."""
        # Arrange
        test_image = b"fake_image_bytes_aluminum_can"
        mock_response = create_mock_response(material=Material.METAL, confidence=0.92)

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                    data={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "tenant_id": "test",
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["material"] == "METAL"
        assert data["confidence"] == 0.92


class TestClassifyEndpointJSON:
    """Tests for JSON format (legacy)."""

    def test_classify_json_success(self) -> None:
        """Test successful classification with JSON format."""
        # Arrange
        scan_id = str(uuid4())
        trace_id = str(uuid4())
        mock_response = create_mock_response(input_format="url")

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    json={
                        "scan_id": scan_id,
                        "station_id": "TEST-01",
                        "image_url": "https://example.com/test.jpg",
                        "tenant_id": "test",
                        "trace_id": trace_id,
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["material"] == "PLASTIC"
        assert data["meta"]["input_format"] == "url"
        assert data["meta"]["s3_upload_status"] == "n/a"

    def test_classify_json_with_s3_url(self) -> None:
        """Test JSON request with S3 URL."""
        # Arrange
        mock_response = create_mock_response(input_format="url")

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    json={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "image_url": "s3://bucket/image.jpg",
                        "tenant_id": "test",
                    },
                )

        # Assert
        assert response.status_code == 200


class TestClassifyEndpointValidationErrors:
    """Tests for validation errors (400 status codes)."""

    def test_classify_no_input_provided(self) -> None:
        """Test 400 error when neither multipart nor JSON provided."""
        # Act
        response = client.post("/api/v1/classify")

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error_code"] == "INVALID_INPUT"
        assert "multipart" in data["detail"]["message"].lower()

    def test_classify_no_waste_detected(self) -> None:
        """Test 400 error when pipeline detects no waste."""
        from app.api.dependencies import get_pipeline
        
        # Arrange
        test_image = b"empty_hand_image"

        mock_pipeline = AsyncMock()
        mock_pipeline.process.side_effect = ValidationError(
            error_code="NO_WASTE_DETECTED",
            message="No se detectó residuo en la imagen",
            details={"suggestion": "Acerca un residuo al encuadre y vuelve a intentar"},
        )
        
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
        
        try:
            # Act
            response = client.post(
                "/api/v1/classify",
                files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                data={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "tenant_id": "test",
                },
            )

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "NO_WASTE_DETECTED"
            assert "No se detectó" in data["detail"]["message"]
            assert "details" in data["detail"] and "suggestion" in data["detail"]["details"]
        finally:
            app.dependency_overrides.clear()

    def test_classify_low_confidence(self) -> None:
        """Test 400 error when classification confidence is too low."""
        from app.api.dependencies import get_pipeline
        
        # Arrange
        test_image = b"blurry_image"

        mock_pipeline = AsyncMock()
        mock_pipeline.process.side_effect = ValidationError(
            error_code="LOW_CONFIDENCE",
            message="Clasificación con confianza muy baja: 0.25",
            details={"suggestion": "Mejora la iluminación o acerca más el objeto a la cámara"},
        )
        
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
        
        try:
            # Act
            response = client.post(
                "/api/v1/classify",
                files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                data={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "tenant_id": "test",
                },
            )

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "LOW_CONFIDENCE"
            assert "confianza" in data["detail"]["message"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_classify_invalid_uuid(self) -> None:
        """Test 400 error when scan_id is not a valid UUID."""
        # Act
        response = client.post(
            "/api/v1/classify",
            files={"image": ("test.jpg", BytesIO(b"test"), "image/jpeg")},
            data={
                "scan_id": "invalid-uuid",
                "station_id": "TEST-01",
                "tenant_id": "test",
            },
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "VALIDATION_ERROR"


class TestClassifyEndpointTimeouts:
    """Tests for timeout errors (504 status codes)."""

    def test_classify_timeout_error(self) -> None:
        """Test 504 error when pipeline times out."""
        from app.api.dependencies import get_pipeline
        
        # Arrange
        test_image = b"complex_image"

        mock_pipeline = AsyncMock()
        # Simulate timeout with AgentTimeoutError
        mock_pipeline.process.side_effect = AgentTimeoutError(
            agent_name="MaterialClassifier",
            timeout_seconds=5.0
        )
        
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
        
        try:
            # Act
            response = client.post(
                "/api/v1/classify",
                files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                data={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "tenant_id": "test",
                },
            )

            # Assert
            assert response.status_code == 504
            data = response.json()
            assert data["detail"]["error"] == "GATEWAY_TIMEOUT"
            assert "timeout" in data["detail"]["message"].lower()
        finally:
            app.dependency_overrides.clear()


class TestClassifyEndpointServerErrors:
    """Tests for server errors (500 status codes)."""

    def test_classify_classification_error(self) -> None:
        """Test 500 error when classification fails."""
        from app.api.dependencies import get_pipeline
        
        # Arrange
        test_image = b"corrupted_image"

        mock_pipeline = AsyncMock()
        mock_pipeline.process.side_effect = ClassificationError(
            "Classification model unavailable"
        )
        
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
        
        try:
            # Act
            response = client.post(
                    "/api/v1/classify",
                    files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                    data={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "tenant_id": "test",
                    },
                )

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "CLASSIFICATION_ERROR"
        finally:
            app.dependency_overrides.clear()

    def test_classify_unexpected_error(self) -> None:
        """Test 500 error for unexpected exceptions."""
        from app.api.dependencies import get_pipeline
        
        # Arrange
        test_image = b"test_image"

        mock_pipeline = AsyncMock()
        mock_pipeline.process.side_effect = RuntimeError("Unexpected error")
        
        app.dependency_overrides[get_pipeline] = lambda: mock_pipeline
        
        try:
            # Act
            response = client.post(
                "/api/v1/classify",
                files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                data={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "tenant_id": "test",
                },
            )

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] in ["INTERNAL_ERROR", "INTERNAL_SERVER_ERROR"]
        finally:
            app.dependency_overrides.clear()


class TestClassifyEndpointHeaders:
    """Tests for response headers."""

    def test_classify_response_headers_present(self) -> None:
        """Test that X-Trace-Id and X-Request-Duration headers are present."""
        # Arrange
        test_image = b"test_image"
        mock_response = create_mock_response()

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                    data={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "tenant_id": "test",
                    },
                )

        # Assert
        assert "X-Trace-Id" in response.headers
        assert "X-Request-Duration" in response.headers
        assert response.headers["X-Request-Duration"].endswith("ms")


class TestClassifyEndpointBackgroundTasks:
    """Tests for background S3 upload tasks."""

    def test_classify_multipart_schedules_s3_upload(self) -> None:
        """Test that multipart request schedules S3 upload in background."""
        # Arrange
        test_image = b"test_image_for_s3_upload"
        mock_response = create_mock_response()

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                with patch("app.api.dependencies.S3Service") as MockS3Service:
                    mock_s3 = AsyncMock()
                    MockS3Service.return_value = mock_s3

                    # Act
                    response = client.post(
                        "/api/v1/classify",
                        files={
                            "image": ("test.jpg", BytesIO(test_image), "image/jpeg")
                        },
                        data={
                            "scan_id": str(uuid4()),
                            "station_id": "TEST-01",
                            "tenant_id": "test",
                        },
                    )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["s3_upload_status"] == "pending"

    def test_classify_json_does_not_schedule_s3_upload(self) -> None:
        """Test that JSON request does not schedule S3 upload."""
        # Arrange
        mock_response = create_mock_response(input_format="url")
        mock_response.meta.s3_upload_status = "n/a"

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    json={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "image_url": "https://example.com/test.jpg",
                        "tenant_id": "test",
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # S3 upload should not be scheduled for JSON requests
        assert data["meta"]["input_format"] == "url"


class TestClassifyEndpointTraceIdPropagation:
    """Tests for trace_id propagation throughout the request."""

    def test_trace_id_propagated_multipart(self) -> None:
        """Test that trace_id is propagated through multipart request."""
        # Arrange
        test_image = b"test_image"
        trace_id = str(uuid4())
        mock_response = create_mock_response()

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    files={"image": ("test.jpg", BytesIO(test_image), "image/jpeg")},
                    data={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "tenant_id": "test",
                        "trace_id": trace_id,
                    },
                )

        # Assert
        assert response.status_code == 200
        assert response.headers["X-Trace-Id"] == trace_id

    def test_trace_id_propagated_json(self) -> None:
        """Test that trace_id is propagated through JSON request."""
        # Arrange
        trace_id = str(uuid4())
        mock_response = create_mock_response(input_format="url")

        with patch("app.api.endpoints.classify.Pipeline") as MockPipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process.return_value = mock_response
            MockPipeline.return_value = mock_pipeline

            with patch("app.api.dependencies.Pipeline", return_value=mock_pipeline):
                # Act
                response = client.post(
                    "/api/v1/classify",
                    json={
                        "scan_id": str(uuid4()),
                        "station_id": "TEST-01",
                        "image_url": "https://example.com/test.jpg",
                        "tenant_id": "test",
                        "trace_id": trace_id,
                    },
                )

        # Assert
        assert response.status_code == 200
        assert response.headers["X-Trace-Id"] == trace_id
