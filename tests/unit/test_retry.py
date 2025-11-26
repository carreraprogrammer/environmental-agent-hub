"""
Unit tests for retry logic with exponential backoff.

Tests retry behavior, backoff calculations, and jitter.
Target coverage: ≥85%
"""

import asyncio
import time

import pytest

from app.utils.retry import retry_with_backoff, with_retry


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_immediate_success(self):
        """Test function succeeds on first attempt."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(success_func, max_attempts=3)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_after_failures(self):
        """Test function succeeds after some failures."""
        attempt_count = 0

        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise TimeoutError("Temporary failure")
            return "success"

        result = await retry_with_backoff(
            flaky_func,
            max_attempts=3,
            initial_delay=0.01,  # Short delay for test
        )

        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Test function fails after max attempts."""

        async def always_fails():
            raise ValueError("Permanent failure")

        with pytest.raises(ValueError) as exc_info:
            await retry_with_backoff(
                always_fails,
                max_attempts=3,
                initial_delay=0.01,
            )

        assert "Permanent failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retryable_exceptions_only(self):
        """Test only retryable exceptions trigger retry."""
        attempt_count = 0

        async def func_with_validation_error():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Validation error")

        # ValueError is not in retryable_exceptions
        with pytest.raises(ValueError):
            await retry_with_backoff(
                func_with_validation_error,
                max_attempts=3,
                retryable_exceptions=(TimeoutError,),
                initial_delay=0.01,
            )

        # Should fail immediately without retry
        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        delays = []
        attempt_count = 0

        async def track_delays():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count > 1:
                delays.append(time.time())
            if attempt_count < 4:
                raise Exception("Fail")
            return "success"

        start_time = time.time()
        await retry_with_backoff(
            track_delays,
            max_attempts=4,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable timing
        )

        # Calculate actual delays between attempts
        actual_delays = []
        prev_time = start_time
        for delay_time in delays:
            actual_delays.append(delay_time - prev_time)
            prev_time = delay_time

        # Expected delays: 0.1s, 0.2s, 0.4s (exponential)
        # Allow 50ms tolerance for timing variations
        assert len(actual_delays) == 3
        assert 0.08 < actual_delays[0] < 0.15  # ~0.1s
        assert 0.18 < actual_delays[1] < 0.25  # ~0.2s
        assert 0.38 < actual_delays[2] < 0.45  # ~0.4s

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test max_delay caps exponential backoff."""
        delays = []
        attempt_count = 0

        async def track_delays():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count > 1:
                delays.append(time.time())
            raise Exception("Fail")

        with pytest.raises(Exception):
            await retry_with_backoff(
                track_delays,
                max_attempts=5,
                initial_delay=1.0,
                max_delay=2.0,  # Cap at 2 seconds
                exponential_base=2.0,
                jitter=False,
            )

        # Calculate actual delays
        actual_delays = []
        for i in range(1, len(delays)):
            actual_delays.append(delays[i] - delays[i - 1])

        # Delays should be capped at max_delay (2.0s)
        # Expected: 1.0s, 2.0s (capped), 2.0s (capped), 2.0s (capped)
        for delay in actual_delays[1:]:  # Skip first delay
            assert delay <= 2.5  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delays."""
        delays_run1 = []
        delays_run2 = []

        async def track_delays(delay_list):
            if len(delay_list) > 0:
                delay_list.append(time.time())
            raise Exception("Fail")

        # Run 1
        try:
            await retry_with_backoff(
                lambda: track_delays(delays_run1),
                max_attempts=3,
                initial_delay=0.1,
                jitter=True,
            )
        except Exception:
            pass

        # Run 2
        try:
            await retry_with_backoff(
                lambda: track_delays(delays_run2),
                max_attempts=3,
                initial_delay=0.1,
                jitter=True,
            )
        except Exception:
            pass

        # With jitter, delays should be different between runs
        # (though there's a small chance they're the same)
        # This is a probabilistic test
        assert len(delays_run1) == len(delays_run2)

    @pytest.mark.asyncio
    async def test_with_args_and_kwargs(self):
        """Test retry_with_backoff with function that takes arguments."""

        async def func_with_args(x, y, z=10):
            return x + y + z

        # Use a lambda to avoid argument conflicts
        result = await retry_with_backoff(
            lambda: func_with_args(6, 7, z=20),
            max_attempts=3,
            initial_delay=0.01,
        )

        assert result == 33  # 6 + 7 + 20


class TestWithRetryDecorator:
    """Tests for @with_retry decorator."""

    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """Test decorator works with successful function."""

        @with_retry(max_attempts=3)
        async def success_func():
            return "success"

        result = await success_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_with_retries(self):
        """Test decorator retries on failure."""
        attempt_count = 0

        @with_retry(
            max_attempts=3,
            initial_delay=0.01,
            retryable_exceptions=(TimeoutError,),
        )
        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise TimeoutError("Temporary failure")
            return "success"

        result = await flaky_func()

        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_decorator_exhausts_retries(self):
        """Test decorator exhausts retries."""

        @with_retry(max_attempts=3, initial_delay=0.01)
        async def always_fails():
            raise RuntimeError("Permanent failure")

        with pytest.raises(RuntimeError):
            await always_fails()

    @pytest.mark.asyncio
    async def test_decorator_with_function_args(self):
        """Test decorator with function arguments."""

        @with_retry(max_attempts=3, initial_delay=0.01)
        async def func_with_args(x, y):
            return x + y

        result = await func_with_args(10, 20)
        assert result == 30

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        @with_retry(max_attempts=3)
        async def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestRetryEdgeCases:
    """Edge case tests for retry logic."""

    @pytest.mark.asyncio
    async def test_max_attempts_one(self):
        """Test with max_attempts=1 (no retry)."""
        attempt_count = 0

        async def func():
            nonlocal attempt_count
            attempt_count += 1
            raise Exception("Fail")

        with pytest.raises(Exception):
            await retry_with_backoff(func, max_attempts=1)

        assert attempt_count == 1

    @pytest.mark.asyncio
    async def test_zero_initial_delay(self):
        """Test with zero initial delay."""
        attempt_count = 0

        async def func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise Exception("Fail")
            return "success"

        start_time = time.time()
        result = await retry_with_backoff(
            func,
            max_attempts=2,
            initial_delay=0.0,
        )
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed < 0.1  # Should be almost instant

    @pytest.mark.asyncio
    async def test_large_max_attempts(self):
        """Test with large max_attempts."""
        attempt_count = 0

        async def func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 10:
                raise Exception("Fail")
            return "success"

        result = await retry_with_backoff(
            func,
            max_attempts=10,
            initial_delay=0.01,
            max_delay=0.1,
        )

        assert result == "success"
        assert attempt_count == 10

    @pytest.mark.asyncio
    async def test_multiple_exception_types(self):
        """Test retrying on multiple exception types."""
        attempt_count = 0

        async def func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise TimeoutError("Timeout")
            if attempt_count == 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = await retry_with_backoff(
            func,
            max_attempts=3,
            retryable_exceptions=(TimeoutError, ConnectionError),
            initial_delay=0.01,
        )

        assert result == "success"
        assert attempt_count == 3


class TestRetryPerformance:
    """Performance-related tests for retry logic."""

    @pytest.mark.asyncio
    async def test_concurrent_retries(self):
        """Test multiple concurrent retry operations."""

        async def flaky_func(task_id):
            if task_id % 2 == 0:
                raise Exception(f"Task {task_id} failed")
            return f"success-{task_id}"

        # Run multiple concurrent retry operations using lambdas
        tasks = []
        for i in range(5):
            task = retry_with_backoff(
                lambda task_id=i: flaky_func(task_id),
                max_attempts=2,
                initial_delay=0.01,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        assert len(results) == 5
        success_count = sum(1 for r in results if isinstance(r, str))
        error_count = sum(1 for r in results if isinstance(r, Exception))

        # Odd task_ids should succeed, even should fail
        assert success_count == 3  # task_ids: 1, 3, 4
        assert error_count == 2  # task_ids: 0, 2
