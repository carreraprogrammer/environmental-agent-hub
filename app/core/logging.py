"""
Structured logging setup using structlog.

Provides JSON-formatted logs for production and human-readable logs for development.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, MutableMapping

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging with structlog.
    
    Configures:
    - JSON output for production (LOG_FORMAT=json)
    - Console output for development (LOG_FORMAT=text)
    - Log level from settings
    - Timestamp formatting
    - Exception rendering
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Configure structlog processors
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Add formatter based on LOG_FORMAT
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Global logger instance
logger = structlog.get_logger()
