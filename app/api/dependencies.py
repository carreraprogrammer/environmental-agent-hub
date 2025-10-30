"""
Dependency injection container for API routes.

Provides reusable dependencies for request handling.
"""

from __future__ import annotations

# from collections.abc import AsyncGenerator
from typing import Generator


def get_request_id() -> Generator[str, None, None]:
    """
    Placeholder dependency for generating request identifiers.
    
    Yields:
        str: Unique request identifier (placeholder value)
    """
    yield "placeholder-request-id"
