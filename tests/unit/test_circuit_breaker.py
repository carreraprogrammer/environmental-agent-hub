"""
Unit tests for Circuit Breaker pattern.

Tests circuit breaker state transitions, failure thresholds, and recovery.
Target coverage: ≥85%
"""

import asyncio

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from app.core.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 60.0
        assert config.exclude_exceptions == ()

    def test_custom_config(self):
        """Test custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout_seconds=30.0,
            exclude_exceptions=(ValueError, KeyError),
        )

        assert config.failure_threshold == 3
        assert config.success_threshold == 1
        assert config.timeout_seconds == 30.0
        assert config.exclude_exceptions == (ValueError, KeyError)


class TestCircuitBreakerBasic:
    """Basic circuit breaker tests."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker("test-service")

        assert breaker.name == "test-service"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.last_failure_time is None

    def test_custom_config(self):
        """Test circuit breaker with custom config."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test-service", config)

        assert breaker.config.failure_threshold == 3


class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_closed_to_open_transition(self):
        """Test CLOSED → OPEN after N failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test-service", config)

        @breaker.call
        async def failing_func():
            raise Exception("Service down")

        # First 2 failures → circuit stays CLOSED
        for _ in range(2):
            with pytest.raises(Exception):
                await failing_func()
            assert breaker.state == CircuitState.CLOSED

        # Third failure → circuit opens
        with pytest.raises(Exception):
            await failing_func()
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_rejects_immediately(self):
        """Test OPEN circuit rejects requests immediately."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test-service", config)

        @breaker.call
        async def failing_func():
            raise Exception("Service down")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await failing_func()

        assert breaker.state == CircuitState.OPEN

        # Next attempt → CircuitBreakerOpenError immediately
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await failing_func()

        assert exc_info.value.details["service"] == "test-service"
        assert exc_info.value.details["failure_count"] == 2

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        """Test OPEN → HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,  # Short timeout for test
        )
        breaker = CircuitBreaker("test-service", config)

        @breaker.call
        async def failing_func():
            raise Exception("Service down")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await failing_func()

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Check state transitions to HALF_OPEN
        breaker._check_state()
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_after_successes(self):
        """Test HALF_OPEN → CLOSED after M successes."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        breaker = CircuitBreaker("test-service", config)

        attempt_count = 0

        @breaker.call
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise Exception("Service down")
            return "success"

        # Open the circuit (2 failures)
        for _ in range(2):
            with pytest.raises(Exception):
                await flaky_func()

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout → HALF_OPEN
        await asyncio.sleep(0.15)

        # First success in HALF_OPEN
        result = await flaky_func()
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.success_count == 1

        # Second success → CLOSED
        result = await flaky_func()
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        """Test HALF_OPEN → OPEN if failure occurs."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,
        )
        breaker = CircuitBreaker("test-service", config)

        attempt_count = 0

        @breaker.call
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 3:  # Fail on first 3 attempts
                raise Exception("Service down")
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await flaky_func()

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout → HALF_OPEN
        await asyncio.sleep(0.15)

        # Failure in HALF_OPEN → back to OPEN
        with pytest.raises(Exception):
            await flaky_func()

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerSuccessfulCalls:
    """Tests for successful calls through circuit breaker."""

    @pytest.mark.asyncio
    async def test_successful_call_closed(self):
        """Test successful call when circuit is CLOSED."""
        breaker = CircuitBreaker("test-service")

        @breaker.call
        async def success_func():
            return "success"

        result = await success_func()

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """Test success resets failure count in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker("test-service", config)

        attempt_count = 0

        @breaker.call
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise Exception("Transient failure")
            return "success"

        # 2 failures
        for _ in range(2):
            with pytest.raises(Exception):
                await flaky_func()

        assert breaker.failure_count == 2

        # Success resets failure count
        result = await flaky_func()
        assert result == "success"
        assert breaker.failure_count == 0


class TestCircuitBreakerExcludedExceptions:
    """Tests for excluded exceptions."""

    @pytest.mark.asyncio
    async def test_excluded_exception_does_not_count(self):
        """Test excluded exceptions don't count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            exclude_exceptions=(ValueError,),
        )
        breaker = CircuitBreaker("test-service", config)

        @breaker.call
        async def func_with_validation():
            raise ValueError("Validation error")

        # ValueError is excluded, so circuit stays CLOSED
        for _ in range(5):
            with pytest.raises(ValueError):
                await func_with_validation()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_non_excluded_exception_counts(self):
        """Test non-excluded exceptions count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            exclude_exceptions=(ValueError,),
        )
        breaker = CircuitBreaker("test-service", config)

        @breaker.call
        async def func_with_error():
            raise RuntimeError("Service error")

        # RuntimeError is NOT excluded, so it counts
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await func_with_error()

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerStateValue:
    """Tests for circuit breaker state value."""

    def test_get_state_value_closed(self):
        """Test state value for CLOSED."""
        breaker = CircuitBreaker("test-service")
        assert breaker.get_state_value() == 0

    def test_get_state_value_half_open(self):
        """Test state value for HALF_OPEN."""
        breaker = CircuitBreaker("test-service")
        breaker.state = CircuitState.HALF_OPEN
        assert breaker.get_state_value() == 1

    def test_get_state_value_open(self):
        """Test state value for OPEN."""
        breaker = CircuitBreaker("test-service")
        breaker.state = CircuitState.OPEN
        assert breaker.get_state_value() == 2


class TestCircuitBreakerEdgeCases:
    """Edge case tests for circuit breaker."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self):
        """Test circuit breaker with concurrent calls."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker("test-service", config)

        call_count = 0

        @breaker.call
        async def concurrent_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result-{call_count}"

        # Execute multiple concurrent calls
        results = await asyncio.gather(
            concurrent_func(),
            concurrent_func(),
            concurrent_func(),
        )

        assert len(results) == 3
        assert all("result-" in r for r in results)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_very_short_timeout_recovers_quickly(self):
        """Test circuit breaker with very short timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.05,  # Very short timeout
        )
        breaker = CircuitBreaker("test-service", config)

        @breaker.call
        async def failing_func():
            raise Exception("Service down")

        # Open the circuit
        with pytest.raises(Exception):
            await failing_func()

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout to pass
        await asyncio.sleep(0.1)
        breaker._check_state()
        assert breaker.state == CircuitState.HALF_OPEN
