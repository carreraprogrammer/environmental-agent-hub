"""
Circuit Breaker Pattern for protecting external service calls.

Implements the circuit breaker pattern to prevent cascading failures and
provide graceful degradation when external services are unavailable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

from app.core.exceptions import CircuitBreakerOpenError

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Too many errors, reject requests
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5          # Consecutive failures to open
    success_threshold: int = 2          # Successes to close from half-open
    timeout_seconds: float = 60.0       # Time before attempting half-open
    exclude_exceptions: tuple[type[Exception], ...] = ()  # Exceptions that don't count as failure


class CircuitBreaker:
    """
    Circuit Breaker for protecting external service calls.

    State transitions:
    1. CLOSED → OPEN: After N consecutive failures
    2. OPEN → HALF_OPEN: After timeout
    3. HALF_OPEN → CLOSED: After M successes
    4. HALF_OPEN → OPEN: If failure in half-open

    Usage:
        breaker = CircuitBreaker("openai-api")

        @breaker.call
        async def classify_with_openai(image):
            return await openai_client.classify(image)
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            name: Name of service being protected
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None

        self.logger = logger.bind(circuit_breaker=name)

    def call(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to protect function with circuit breaker.

        Args:
            func: Async function to protect

        Returns:
            Wrapped function with circuit breaker protection
        """

        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # 1. Check circuit state
            self._check_state()

            # 2. If OPEN, reject immediately
            if self.state == CircuitState.OPEN:
                self.logger.warning(
                    "circuit_breaker_rejected",
                    state=self.state.value,
                    failure_count=self.failure_count,
                )
                raise CircuitBreakerOpenError(
                    service_name=self.name,
                    failure_count=self.failure_count,
                    cooldown_seconds=self.config.timeout_seconds,
                )

            # 3. Attempt call
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result

            except Exception as e:
                # Check if exception should be excluded
                if isinstance(e, self.config.exclude_exceptions):
                    self.logger.debug(
                        "circuit_breaker_exception_excluded",
                        exception=type(e).__name__,
                    )
                    raise  # Re-raise without affecting circuit

                self._on_failure()
                raise

        return wrapper  # type: ignore

    def _check_state(self) -> None:
        """Check and update circuit state."""
        if self.state == CircuitState.OPEN:
            # Check if timeout passed to attempt half-open
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.config.timeout_seconds:
                    self.logger.info(
                        "circuit_breaker_half_open",
                        elapsed_seconds=elapsed,
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.logger.debug(
                "circuit_breaker_success_in_half_open",
                success_count=self.success_count,
                threshold=self.config.success_threshold,
            )

            # If reached threshold, close circuit
            if self.success_count >= self.config.success_threshold:
                self.logger.info("circuit_breaker_closed")
                self.state = CircuitState.CLOSED
                self.failure_count = 0

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open → reopen
            self.logger.warning("circuit_breaker_reopened")
            self.state = CircuitState.OPEN

        elif self.state == CircuitState.CLOSED:
            # Check if reached threshold to open
            if self.failure_count >= self.config.failure_threshold:
                self.logger.error(
                    "circuit_breaker_opened",
                    failure_count=self.failure_count,
                    threshold=self.config.failure_threshold,
                )
                self.state = CircuitState.OPEN

    def get_state_value(self) -> int:
        """
        Get numeric state value for metrics.

        Returns:
            int: 0=closed, 1=half_open, 2=open
        """
        state_values = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2,
        }
        return state_values[self.state]
