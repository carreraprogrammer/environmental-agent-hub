"""
Retry utilities with exponential backoff and jitter.

Provides retry logic for transient failures with configurable backoff
strategies to prevent thundering herd and improve success rates.
"""

from __future__ import annotations

import asyncio
import random
from functools import wraps
from typing import Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    *args,
    **kwargs,
) -> T:
    """
    Retry function with exponential backoff and jitter.

    Args:
        func: Async function to execute
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation (2 = doubles each time)
        jitter: Whether to add randomness to avoid thundering herd
        retryable_exceptions: Tuple of exceptions that trigger retry
        *args, **kwargs: Arguments for func

    Returns:
        Result of func if eventually succeeds

    Raises:
        Last exception if all attempts fail

    Example:
        result = await retry_with_backoff(
            openai_adapter.classify,
            max_attempts=3,
            retryable_exceptions=(TimeoutError, ExternalAPIError),
            image_data=image
        )
    """
    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = await func(*args, **kwargs)

            if attempt > 1:
                logger.info(
                    "retry_succeeded",
                    attempt=attempt,
                    max_attempts=max_attempts,
                )

            return result

        except retryable_exceptions as e:
            last_exception = e

            # If last attempt, don't retry
            if attempt == max_attempts:
                logger.error(
                    "retry_exhausted",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    exception=type(e).__name__,
                    message=str(e),
                )
                break

            # Calculate delay with exponential backoff
            delay = min(
                initial_delay * (exponential_base ** (attempt - 1)),
                max_delay,
            )

            # Add jitter (randomness) if enabled
            if jitter:
                delay = delay * (0.5 + random.random())  # 50-150% of delay

            logger.warning(
                "retry_attempt",
                attempt=attempt,
                max_attempts=max_attempts,
                next_delay_seconds=delay,
                exception=type(e).__name__,
            )

            await asyncio.sleep(delay)

    # Re-raise last exception
    if last_exception:
        raise last_exception

    # Should not reach here, but just in case
    raise RuntimeError("Retry logic failed unexpectedly")


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Decorator to add retry logic to async function.

    Usage:
        @with_retry(max_attempts=3, retryable_exceptions=(TimeoutError,))
        async def classify_image(image_data):
            return await api_call(image_data)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:  # type: ignore
            # Create a lambda that captures the function call with its arguments
            async def execute_func():
                return await func(*args, **kwargs)
            
            return await retry_with_backoff(
                execute_func,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
            )

        return wrapper  # type: ignore

    return decorator
