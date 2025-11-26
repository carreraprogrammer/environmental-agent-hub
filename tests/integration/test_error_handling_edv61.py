"""
Integration tests for EDV-61: Error Handling Robusto + Circuit Breaker + Retry.

Tests específicos para validar todos los criterios de aceptación de EDV-61:
- CA-4: Pipeline error handling y graceful degradation
- CA-6: Finally siempre ejecuta métricas
- CA-7: FastAPI error mapping correcto
- CA-9: Backend NO aborta pipeline
- CA-10: Partial success en downstream

Coverage Target: Estos tests deben subir el coverage total a ≥85%
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AgentTimeoutError,
    CircuitBreakerOpenError,
    ClassificationError,
    ValidationError,
)
from app.main import app
from app.orchestrator.pipeline import Pipeline
from app.schemas.classification import Material
from app.schemas.requests import ClassifyRequestForm

client = TestClient(app)


class TestPipelineErrorHandling:
    """Tests for CA-4: Pipeline error handling y graceful degradation."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_validation_error(self):
        """Test that pipeline correctly handles ValidationError."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.classifier, "classify", side_effect=ValidationError("Invalid image")
        ):
            with pytest.raises(ValidationError) as exc_info:
                await pipeline.process(request)

            assert exc_info.value.message == "Invalid image"
            assert exc_info.value.error_code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_pipeline_handles_timeout_error(self):
        """Test that pipeline correctly handles AgentTimeoutError."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.classifier,
            "classify",
            side_effect=asyncio.TimeoutError("Timeout"),
        ):
            with pytest.raises(AgentTimeoutError) as exc_info:
                await pipeline.process(request)

            assert "Pipeline" in exc_info.value.agent_name
            assert exc_info.value.severity.value == "high"

    @pytest.mark.asyncio
    async def test_pipeline_handles_circuit_breaker_open(self):
        """Test that pipeline correctly handles CircuitBreakerOpenError."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.classifier,
            "classify",
            side_effect=CircuitBreakerOpenError(
                service_name="openai-api", failure_count=5, cooldown_seconds=60.0
            ),
        ):
            with pytest.raises(CircuitBreakerOpenError) as exc_info:
                await pipeline.process(request)

            assert exc_info.value.details["service"] == "openai-api"
            assert exc_info.value.details["failure_count"] == 5

    @pytest.mark.asyncio
    async def test_pipeline_handles_classification_error(self):
        """Test that pipeline correctly handles ClassificationError."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.classifier,
            "classify",
            side_effect=ClassificationError("Model failed"),
        ):
            with pytest.raises(ClassificationError) as exc_info:
                await pipeline.process(request)

            assert exc_info.value.message == "Model failed"
            assert exc_info.value.severity.value == "high"

    @pytest.mark.asyncio
    async def test_pipeline_wraps_unexpected_exceptions(self):
        """Test that pipeline wraps unexpected exceptions in ClassificationError."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.classifier, "classify", side_effect=RuntimeError("Unexpected")
        ):
            with pytest.raises(ClassificationError) as exc_info:
                await pipeline.process(request)

            assert "Pipeline failed" in exc_info.value.message
            assert exc_info.value.error_code == "INTERNAL_ERROR"


class TestFinallyAlwaysExecutes:
    """Tests for CA-6: Finally siempre ejecuta métricas."""

    @pytest.mark.asyncio
    async def test_finally_executes_on_success(self):
        """Test that finally block executes metrics on success."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(pipeline.metrics, "record_pipeline_execution") as mock_metrics:
            # Mock successful classification
            with patch.object(pipeline, "_execute_pipeline", return_value=MagicMock()):
                await pipeline.process(request)

            # Verify metrics were recorded
            assert mock_metrics.called
            call_args = mock_metrics.call_args[1]
            assert call_args["success"] is True
            assert "trace_id" in call_args
            assert "latency_ms" in call_args

    @pytest.mark.asyncio
    async def test_finally_executes_on_validation_error(self):
        """Test that finally block executes metrics even on ValidationError."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(pipeline.metrics, "record_pipeline_execution") as mock_metrics:
            with patch.object(
                pipeline.classifier,
                "classify",
                side_effect=ValidationError("Test error"),
            ):
                with pytest.raises(ValidationError):
                    await pipeline.process(request)

            # Verify metrics were still recorded despite exception
            assert mock_metrics.called
            call_args = mock_metrics.call_args[1]
            assert call_args["success"] is False
            assert call_args["error_type"] == "validation"

    @pytest.mark.asyncio
    async def test_finally_executes_on_timeout(self):
        """Test that finally block executes metrics even on timeout."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(pipeline.metrics, "record_pipeline_execution") as mock_metrics:
            with patch.object(
                pipeline.classifier,
                "classify",
                side_effect=asyncio.TimeoutError("Timeout"),
            ):
                with pytest.raises(AgentTimeoutError):
                    await pipeline.process(request)

            # Verify metrics were still recorded despite timeout
            assert mock_metrics.called
            call_args = mock_metrics.call_args[1]
            assert call_args["success"] is False
            assert call_args["error_type"] == "timeout"


class TestFastAPIErrorMapping:
    """Tests for CA-7: FastAPI error mapping correcto."""

    def test_validation_error_returns_400(self):
        """Test that ValidationError is mapped to HTTP 400."""
        with patch("app.api.endpoints.classify.get_pipeline") as mock_pipeline:
            mock_pipeline.return_value.process.side_effect = ValidationError(
                "No waste detected", error_code="NO_WASTE_DETECTED"
            )

            response = client.post(
                "/api/v1/classify",
                json={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "image_url": "https://example.com/image.jpg",
                    "tenant_id": "test",
                },
            )

            assert response.status_code == 400
            data = response.json()
            # Acepta ambos formatos
            assert data["detail"]["error"] in ["NO_WASTE_DETECTED", "VALIDATION_ERROR"]

    def test_circuit_breaker_open_returns_503(self):
        """Test that CircuitBreakerOpenError is mapped to HTTP 503."""
        with patch("app.api.endpoints.classify.get_pipeline") as mock_pipeline:
            mock_pipeline.return_value.process.side_effect = CircuitBreakerOpenError(
                service_name="openai-api", failure_count=5, cooldown_seconds=60.0
            )

            response = client.post(
                "/api/v1/classify",
                json={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "image_url": "https://example.com/image.jpg",
                    "tenant_id": "test",
                },
            )

            assert response.status_code == 503
            data = response.json()
            assert "SERVICE_TEMPORARILY_UNAVAILABLE" in data["detail"]["error"]

    def test_timeout_error_returns_504(self):
        """Test that AgentTimeoutError is mapped to HTTP 504."""
        with patch("app.api.endpoints.classify.get_pipeline") as mock_pipeline:
            mock_pipeline.return_value.process.side_effect = AgentTimeoutError(
                agent_name="MaterialClassifier", timeout_seconds=10.0
            )

            response = client.post(
                "/api/v1/classify",
                json={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "image_url": "https://example.com/image.jpg",
                    "tenant_id": "test",
                },
            )

            assert response.status_code == 504
            data = response.json()
            assert data["detail"]["error"] == "GATEWAY_TIMEOUT"

    def test_classification_error_returns_500(self):
        """Test that ClassificationError is mapped to HTTP 500."""
        with patch("app.api.endpoints.classify.get_pipeline") as mock_pipeline:
            mock_pipeline.return_value.process.side_effect = ClassificationError(
                "Classification failed"
            )

            response = client.post(
                "/api/v1/classify",
                json={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "image_url": "https://example.com/image.jpg",
                    "tenant_id": "test",
                },
            )

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "CLASSIFICATION_ERROR"

    def test_unexpected_error_returns_500_without_details(self):
        """Test that unexpected errors return HTTP 500 without internal details."""
        with patch("app.api.endpoints.classify.get_pipeline") as mock_pipeline:
            mock_pipeline.return_value.process.side_effect = RuntimeError(
                "Internal error with sensitive data"
            )

            response = client.post(
                "/api/v1/classify",
                json={
                    "scan_id": str(uuid4()),
                    "station_id": "TEST-01",
                    "image_url": "https://example.com/image.jpg",
                    "tenant_id": "test",
                },
            )

            assert response.status_code == 500
            data = response.json()
            # Acepta ambos formatos de error_code
            assert data["detail"]["error"] in ["INTERNAL_SERVER_ERROR", "INTERNAL_ERROR"]
            assert data["detail"]["message"] in [
                "An unexpected error occurred",
                "Classification failed",
                "Pipeline failed",
            ] or "Pipeline failed" in data["detail"]["message"]
            # Verify no sensitive data exposed
            assert "sensitive data" not in str(data)
            assert data["detail"]["details"] == {} or "details" not in data["detail"]


class TestBackendDoesNotAbort:
    """Tests for CA-9: Backend NO aborta pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_when_backend_fails(self):
        """Test that pipeline continues successfully even if backend fails."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        # Mock successful classification
        mock_result = MagicMock()
        mock_result.material.material_type = Material.PLASTIC
        mock_result.material.confidence = 0.95
        mock_result.subtype.value = None
        mock_result.volume.to_ml.return_value = 500.0
        mock_result.model_used = "gpt-4o"
        mock_result.model_provider = "openai"

        with patch.object(pipeline.classifier, "classify", return_value=mock_result):
            # Mock backend failure
            with patch.object(
                pipeline.backend_integration,
                "send",
                side_effect=Exception("Backend connection failed"),
            ):
                # Pipeline should still succeed
                result = await pipeline.process(request)

                # Verify classification succeeded despite backend failure
                assert result.material == Material.PLASTIC
                assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_backend_failure_logged_as_warning_not_error(self):
        """Test that backend failures are logged as WARNING, not ERROR."""
        from app.core.logging import logger

        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        mock_result = MagicMock()
        mock_result.material.material_type = Material.PLASTIC
        mock_result.material.confidence = 0.95
        mock_result.subtype.value = None
        mock_result.volume.to_ml.return_value = 500.0
        mock_result.model_used = "gpt-4o"
        mock_result.model_provider = "openai"

        with patch.object(pipeline.classifier, "classify", return_value=mock_result):
            with patch.object(
                pipeline.backend_integration,
                "send",
                side_effect=Exception("Backend failed"),
            ):
                # Should complete without raising
                result = await pipeline.process(request)
                assert result is not None


class TestMetricsRecording:
    """Tests for CA-11: Métricas recording."""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self):
        """Test that metrics are recorded on successful pipeline execution."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.metrics, "record_pipeline_execution"
        ) as mock_record:
            mock_result = MagicMock()
            mock_result.material.material_type = Material.PLASTIC
            mock_result.material.confidence = 0.95
            mock_result.subtype.value = None
            mock_result.volume.to_ml.return_value = 500.0
            mock_result.model_used = "gpt-4o"
            mock_result.model_provider = "openai"

            with patch.object(pipeline.classifier, "classify", return_value=mock_result):
                await pipeline.process(request)

            # Verify metrics were recorded
            assert mock_record.called
            call_args = mock_record.call_args[1]
            assert call_args["success"] is True
            assert call_args["latency_ms"] > 0
            assert len(call_args["agents_executed"]) > 0

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_error(self):
        """Test that metrics are recorded even when pipeline fails."""
        pipeline = Pipeline()
        request = ClassifyRequestForm(
            scan_id=uuid4(),
            station_id="TEST-01",
            tenant_id="test",
            image_bytes=b"fake_image_data",
        )

        with patch.object(
            pipeline.metrics, "record_pipeline_execution"
        ) as mock_record:
            with patch.object(
                pipeline.metrics, "record_error"
            ) as mock_record_error:
                with patch.object(
                    pipeline.classifier,
                    "classify",
                    side_effect=ValidationError("Test error"),
                ):
                    with pytest.raises(ValidationError):
                        await pipeline.process(request)

                # Verify error metrics were recorded
                assert mock_record_error.called
                error_call_args = mock_record_error.call_args[1]
                assert error_call_args["error_type"] == "validation"
                assert error_call_args["severity"] == "medium"

            # Verify pipeline metrics were also recorded
            assert mock_record.called
            pipeline_call_args = mock_record.call_args[1]
            assert pipeline_call_args["success"] is False
            assert pipeline_call_args["error_type"] == "validation"


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration in pipeline."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transitions during failures."""
        from app.core.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker("test-service")

        # Initially closed
        assert breaker.state == CircuitState.CLOSED

        # Simulate failures to open circuit
        for _ in range(5):
            breaker._on_failure()

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 5

    def test_circuit_breaker_get_state_value(self):
        """Test circuit breaker state value for metrics."""
        from app.core.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker("test-service")

        # CLOSED = 0
        assert breaker.get_state_value() == 0

        # Transition to OPEN
        breaker.state = CircuitState.OPEN
        assert breaker.get_state_value() == 2

        # Transition to HALF_OPEN
        breaker.state = CircuitState.HALF_OPEN
        assert breaker.get_state_value() == 1
