"""
Structured logging setup using structlog.

Provides JSON-formatted logs for production and human-readable logs for development.
Supports contextual fields like trace_id, agent, action, latency_ms, etc.

Standard Log Fields:
    Mandatory:
        - timestamp: ISO 8601 format
        - level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        - event: Description of the event

    Contextual (per agent):
        - trace_id: UUID of request (propagated through pipeline)
        - agent: Agent name (e.g., "PreValidator", "Classifier")
        - action: Specific action (e.g., "validate_image", "classify_material")
        - latency_ms: Execution time in milliseconds
        - cost_usd: Operation cost (if applicable)
        - model_used: Active model (for Classifier)
        - confidence: Confidence score (for classifications)
        - material: Classified material
        - error_code: Error code (if applicable)

Usage:
    Basic logging:
        logger.info("event_name", trace_id="abc-123", agent="Classifier")

    Context binding (persistent context per agent):
        agent_logger = logger.bind(agent="PreValidator", trace_id="abc-123")
        agent_logger.info("validation_started")
        agent_logger.info("validation_complete", has_waste=True)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def setup_logging(log_level: str | None = None) -> None:
    """
    Configure structured logging with structlog.

    Args:
        log_level: Optional override for log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   If not provided, uses settings.LOG_LEVEL.

    Configures:
        - JSON output for production (LOG_FORMAT=json)
        - Console output for development (LOG_FORMAT=text)
        - Log level from settings or override
        - ISO 8601 timestamp formatting
        - Exception rendering
        - Stack trace rendering
        - Unicode handling
        - Context propagation (trace_id, agent, etc.)

    Examples:
        >>> setup_logging()  # Uses settings.LOG_LEVEL
        >>> setup_logging(log_level="DEBUG")  # Override to DEBUG
    """
    # Determine log level
    if log_level is None:
        log_level = settings.LOG_LEVEL

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Build processor chain
    # Pre-processing: Add context and metadata
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,  # Merge context vars
        structlog.stdlib.filter_by_level,  # Filter by log level
        structlog.stdlib.add_logger_name,  # Add logger name
        structlog.stdlib.add_log_level,  # Add log level
        structlog.stdlib.PositionalArgumentsFormatter(),  # Handle positional args
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
        structlog.processors.StackInfoRenderer(),  # Render stack traces
        structlog.processors.format_exc_info,  # Format exceptions
        structlog.processors.UnicodeDecoder(),  # Decode unicode
    ]

    # Final rendering: JSON for production, pretty console for development
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Global logger instance
logger = structlog.get_logger()
