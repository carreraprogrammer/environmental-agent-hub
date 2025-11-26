"""
Custom exceptions for Agent Hub.

Defines domain-specific exceptions with error codes, severity, and structured metadata
for production-ready error handling with circuit breakers and retry logic.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorSeverity(str, Enum):
    """Severity level for error logging and alerting."""

    LOW = "low"           # Warning - does not affect classification
    MEDIUM = "medium"     # Recoverable error - fallback available
    HIGH = "high"         # Critical error - aborts request
    CRITICAL = "critical" # System compromised - immediate alert


class AgentHubException(Exception):
    """
    Base exception for all Agent Hub errors.

    Attributes:
        message: Descriptive error message
        error_code: Unique error code (e.g., "VALIDATION_ERROR")
        details: Additional error metadata
        severity: Error severity level (LOW, MEDIUM, HIGH, CRITICAL)
        recoverable: Whether error is recoverable with retry/fallback
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        details: dict[str, Any] | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize exception.

        Args:
            message: Descriptive error message
            error_code: Unique error identifier
            details: Additional metadata about the error
            severity: Error severity level
            recoverable: Whether error is recoverable with retry/fallback
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.severity = severity
        self.recoverable = recoverable
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to dict for HTTP response.

        Returns:
            dict: Error information for API response
        """
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
        }


class ValidationError(AgentHubException):
    """
    Error in request validation or business rules.

    Examples:
        - Invalid request schema
        - Station ID does not exist
        - Corrupted image data
    """

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error."""
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            recoverable=False,  # No point retrying with same input
        )


class ClassificationError(AgentHubException):
    """
    Error in image classification.

    Examples:
        - MaterialClassifier fails parsing JSON
        - Confidence too low (<0.7)
        - Model returns invalid response
    """

    def __init__(
        self,
        message: str,
        error_code: str = "CLASSIFICATION_ERROR",
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ) -> None:
        """Initialize classification error."""
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            severity=ErrorSeverity.HIGH,
            recoverable=recoverable,
        )


class AgentTimeoutError(AgentHubException):
    """
    Timeout in a pipeline agent.

    Examples:
        - MaterialClassifier takes >10s
        - Roboflow API does not respond
        - Backend Rails takes >5s
    """

    def __init__(
        self,
        agent_name: str,
        timeout_seconds: float,
        message: str | None = None,
    ) -> None:
        """
        Initialize timeout error.

        Args:
            agent_name: Name of agent that timed out
            timeout_seconds: Timeout threshold that was exceeded
            message: Optional custom message
        """
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds

        msg = message or f"Agent {agent_name} exceeded timeout of {timeout_seconds}s"
        super().__init__(
            message=msg,
            error_code="AGENT_TIMEOUT",
            details={
                "agent": agent_name,
                "timeout_seconds": timeout_seconds,
            },
            severity=ErrorSeverity.HIGH,
            recoverable=True,  # May work with retry
        )


class ExternalAPIError(AgentHubException):
    """
    Error communicating with external API.

    Examples:
        - OpenAI API returns 500
        - Roboflow API rate limit (429)
        - Anthropic API authentication error (401)
    """

    def __init__(
        self,
        api_name: str,
        status_code: int | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        recoverable: bool | None = None,
    ) -> None:
        """
        Initialize external API error.

        Args:
            api_name: Name of external API
            status_code: HTTP status code (if available)
            message: Optional custom message
            details: Additional error metadata
            recoverable: Override recoverable detection (auto-detected from status_code)
        """
        self.api_name = api_name
        self.status_code = status_code

        msg = message or f"External API {api_name} failed"
        if status_code:
            msg += f" (status: {status_code})"

        error_details = details or {}
        error_details["api_name"] = api_name
        if status_code:
            error_details["status_code"] = status_code

        # Determine if recoverable by status code
        if recoverable is None and status_code:
            # 5xx = recoverable (temporary server error)
            # 429 = recoverable (rate limit, retry later)
            # 4xx (except 429) = not recoverable (client error)
            recoverable = status_code >= 500 or status_code == 429
        elif recoverable is None:
            recoverable = True

        super().__init__(
            message=msg,
            error_code="EXTERNAL_API_ERROR",
            details=error_details,
            severity=ErrorSeverity.HIGH if not recoverable else ErrorSeverity.MEDIUM,
            recoverable=recoverable,
        )


class BackendIntegrationError(AgentHubException):
    """
    Error communicating with Backend Rails.

    IMPORTANT: This error should NOT abort classification.
    The system must continue without environmental data.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize backend integration error.

        Args:
            message: Error message
            status_code: HTTP status code from backend
            details: Additional error metadata
        """
        error_details = details or {}
        if status_code:
            error_details["backend_status_code"] = status_code

        super().__init__(
            message=message,
            error_code="BACKEND_ERROR",
            details=error_details,
            severity=ErrorSeverity.LOW,  # NOT critical
            recoverable=False,  # No retry, continue without backend
        )


class CircuitBreakerOpenError(AgentHubException):
    """
    Circuit breaker is open (too many consecutive failures).

    When an external service fails repeatedly, the circuit breaker
    opens to avoid overwhelming the service and fail fast.
    """

    def __init__(
        self,
        service_name: str,
        failure_count: int,
        cooldown_seconds: float,
    ) -> None:
        """
        Initialize circuit breaker open error.

        Args:
            service_name: Name of service with open circuit
            failure_count: Number of consecutive failures
            cooldown_seconds: Seconds until circuit attempts half-open
        """
        super().__init__(
            message=f"Circuit breaker open for {service_name} after {failure_count} failures",
            error_code="CIRCUIT_BREAKER_OPEN",
            details={
                "service": service_name,
                "failure_count": failure_count,
                "cooldown_seconds": cooldown_seconds,
            },
            severity=ErrorSeverity.HIGH,
            recoverable=True,  # Recovers after cooldown
        )


class ConfigurationError(AgentHubException):
    """
    Raised when configuration is invalid.

    Examples:
        - Missing API keys
        - Invalid model selection
        - Invalid settings
    """

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIGURATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize configuration error."""
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
        )
