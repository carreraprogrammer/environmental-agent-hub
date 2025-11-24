"""
Pytest configuration for environmental-agent-hub.

This file configures pytest options and fixtures used across all tests.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command-line options to pytest."""
    parser.addoption(
        "--backend",
        action="store_true",
        default=False,
        help="Run backend integration tests (requires Rails server running on localhost:3000)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "backend: mark test as backend integration test (requires Rails server)",
    )
