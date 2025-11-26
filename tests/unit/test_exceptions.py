"""
Unit tests for custom exceptions.

Tests all custom exceptions with hierarchy, severity, and error handling.
Target coverage: ≥90%
"""

import pytest

from app.core.exceptions import (
    AgentHubException,
    AgentTimeoutError,
    BackendIntegrationError,
    CircuitBreakerOpenError,
    ClassificationError,
    ConfigurationError,
    ErrorSeverity,
    ExternalAPIError,
    ValidationError,
)


class TestAgentHubException:
    """Tests for base AgentHubException class."""

    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = AgentHubException(
            message="Test error",
            error_code="TEST_ERROR",
        )

        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {}
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.recoverable is True

    def test_exception_with_details(self):
        """Test exception with custom details."""
        exc = AgentHubException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"field": "value", "count": 42},
            severity=ErrorSeverity.HIGH,
            recoverable=False,
        )

        assert exc.details == {"field": "value", "count": 42}
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.recoverable is False

    def test_to_dict(self):
        """Test serialization to dict."""
        exc = AgentHubException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"},
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
        )

        result = exc.to_dict()

        assert result == {
            "error": "TEST_ERROR",
            "message": "Test error",
            "details": {"key": "value"},
            "severity": "critical",
            "recoverable": False,
        }

    def test_string_representation(self):
        """Test string representation."""
        exc = AgentHubException(
            message="Test error message",
            error_code="TEST_ERROR",
        )

        assert str(exc) == "Test error message"


class TestValidationError:
    """Tests for ValidationError."""

    def test_default_creation(self):
        """Test ValidationError with defaults."""
        exc = ValidationError(
            message="Invalid request",
        )

        assert exc.message == "Invalid request"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.recoverable is False  # No point retrying with same input

    def test_custom_error_code(self):
        """Test ValidationError with custom error code."""
        exc = ValidationError(
            message="No waste detected",
            error_code="NO_WASTE_DETECTED",
            details={"confidence": 0.1},
        )

        assert exc.error_code == "NO_WASTE_DETECTED"
        assert exc.details == {"confidence": 0.1}

    def test_to_dict(self):
        """Test ValidationError serialization."""
        exc = ValidationError(
            message="Station ID not found",
            error_code="INVALID_STATION",
            details={"station_id": "XXX-99"},
        )

        result = exc.to_dict()

        assert result["error"] == "INVALID_STATION"
        assert result["message"] == "Station ID not found"
        assert result["details"]["station_id"] == "XXX-99"
        assert result["severity"] == "medium"
        assert result["recoverable"] is False


class TestClassificationError:
    """Tests for ClassificationError."""

    def test_default_creation(self):
        """Test ClassificationError with defaults."""
        exc = ClassificationError(
            message="Classification failed",
        )

        assert exc.message == "Classification failed"
        assert exc.error_code == "CLASSIFICATION_ERROR"
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.recoverable is True

    def test_non_recoverable(self):
        """Test ClassificationError as non-recoverable."""
        exc = ClassificationError(
            message="Invalid model response",
            error_code="INVALID_RESPONSE",
            recoverable=False,
        )

        assert exc.recoverable is False

    def test_with_details(self):
        """Test ClassificationError with details."""
        exc = ClassificationError(
            message="Low confidence",
            error_code="LOW_CONFIDENCE",
            details={"confidence": 0.45, "threshold": 0.70},
        )

        assert exc.details["confidence"] == 0.45
        assert exc.details["threshold"] == 0.70


class TestAgentTimeoutError:
    """Tests for AgentTimeoutError."""

    def test_default_message(self):
        """Test AgentTimeoutError with default message."""
        exc = AgentTimeoutError(
            agent_name="MaterialClassifier",
            timeout_seconds=10.0,
        )

        assert exc.agent_name == "MaterialClassifier"
        assert exc.timeout_seconds == 10.0
        assert "MaterialClassifier" in exc.message
        assert "10.0" in exc.message
        assert exc.error_code == "AGENT_TIMEOUT"
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.recoverable is True

    def test_custom_message(self):
        """Test AgentTimeoutError with custom message."""
        exc = AgentTimeoutError(
            agent_name="FastClassifier",
            timeout_seconds=3.0,
            message="Fast path timeout",
        )

        assert exc.message == "Fast path timeout"

    def test_details(self):
        """Test AgentTimeoutError details."""
        exc = AgentTimeoutError(
            agent_name="MaterialClassifier",
            timeout_seconds=15.0,
        )

        assert exc.details["agent"] == "MaterialClassifier"
        assert exc.details["timeout_seconds"] == 15.0


class TestExternalAPIError:
    """Tests for ExternalAPIError."""

    def test_basic_creation(self):
        """Test ExternalAPIError basic creation."""
        exc = ExternalAPIError(
            api_name="OpenAI",
        )

        assert exc.api_name == "OpenAI"
        assert exc.status_code is None
        assert "OpenAI" in exc.message
        assert exc.error_code == "EXTERNAL_API_ERROR"
        assert exc.recoverable is True

    def test_with_status_code(self):
        """Test ExternalAPIError with status code."""
        exc = ExternalAPIError(
            api_name="OpenAI",
            status_code=500,
        )

        assert exc.status_code == 500
        assert "500" in exc.message
        assert exc.details["status_code"] == 500

    def test_recoverable_5xx(self):
        """Test 5xx errors are recoverable."""
        exc = ExternalAPIError(
            api_name="OpenAI",
            status_code=500,
        )

        assert exc.recoverable is True
        assert exc.severity == ErrorSeverity.MEDIUM

    def test_recoverable_429(self):
        """Test 429 rate limit is recoverable."""
        exc = ExternalAPIError(
            api_name="Roboflow",
            status_code=429,
        )

        assert exc.recoverable is True

    def test_non_recoverable_4xx(self):
        """Test 4xx client errors are not recoverable."""
        exc = ExternalAPIError(
            api_name="Anthropic",
            status_code=401,
        )

        assert exc.recoverable is False
        assert exc.severity == ErrorSeverity.HIGH

    def test_custom_message(self):
        """Test ExternalAPIError with custom message."""
        exc = ExternalAPIError(
            api_name="Google",
            status_code=503,
            message="Service unavailable",
        )

        # Custom message gets status code appended
        assert "Service unavailable" in exc.message
        assert "503" in exc.message

    def test_override_recoverable(self):
        """Test overriding recoverable detection."""
        exc = ExternalAPIError(
            api_name="OpenAI",
            status_code=500,
            recoverable=False,
        )

        assert exc.recoverable is False


class TestBackendIntegrationError:
    """Tests for BackendIntegrationError."""

    def test_basic_creation(self):
        """Test BackendIntegrationError creation."""
        exc = BackendIntegrationError(
            message="Backend timeout",
        )

        assert exc.message == "Backend timeout"
        assert exc.error_code == "BACKEND_ERROR"
        assert exc.severity == ErrorSeverity.LOW  # NOT critical
        assert exc.recoverable is False  # No retry, continue without backend

    def test_with_status_code(self):
        """Test BackendIntegrationError with status code."""
        exc = BackendIntegrationError(
            message="Backend error",
            status_code=503,
        )

        assert exc.details["backend_status_code"] == 503

    def test_severity_always_low(self):
        """Test BackendIntegrationError always has low severity."""
        exc = BackendIntegrationError(
            message="Backend completely down",
            status_code=500,
        )

        # Even with 500 error, severity should be LOW
        # because backend is not critical for classification
        assert exc.severity == ErrorSeverity.LOW


class TestCircuitBreakerOpenError:
    """Tests for CircuitBreakerOpenError."""

    def test_creation(self):
        """Test CircuitBreakerOpenError creation."""
        exc = CircuitBreakerOpenError(
            service_name="openai-api",
            failure_count=5,
            cooldown_seconds=60.0,
        )

        assert "openai-api" in exc.message
        assert "5" in exc.message
        assert exc.error_code == "CIRCUIT_BREAKER_OPEN"
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.recoverable is True  # Recovers after cooldown

    def test_details(self):
        """Test CircuitBreakerOpenError details."""
        exc = CircuitBreakerOpenError(
            service_name="roboflow-api",
            failure_count=10,
            cooldown_seconds=120.0,
        )

        assert exc.details["service"] == "roboflow-api"
        assert exc.details["failure_count"] == 10
        assert exc.details["cooldown_seconds"] == 120.0


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_basic_creation(self):
        """Test ConfigurationError creation."""
        exc = ConfigurationError(
            message="Missing API key",
        )

        assert exc.message == "Missing API key"
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.recoverable is False

    def test_custom_error_code(self):
        """Test ConfigurationError with custom code."""
        exc = ConfigurationError(
            message="Invalid model",
            error_code="INVALID_MODEL",
            details={"model": "gpt-5"},
        )

        assert exc.error_code == "INVALID_MODEL"
        assert exc.details["model"] == "gpt-5"


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_severity_values(self):
        """Test all severity levels."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_severity_comparison(self):
        """Test severity enum values are different."""
        # String comparison doesn't work as expected, just check they're different
        assert ErrorSeverity.LOW != ErrorSeverity.CRITICAL
        assert ErrorSeverity.MEDIUM != ErrorSeverity.HIGH
        assert ErrorSeverity.LOW == ErrorSeverity.LOW
