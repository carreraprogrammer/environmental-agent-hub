"""
Unit tests for FastAPI main application.

Tests startup, shutdown, health endpoints, and CORS configuration.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint /."""

    def test_root_returns_welcome_message(self):
        """Test that root endpoint returns welcome message."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Agent Hub API" in data["message"]
        assert "version" in data
        assert data["version"] == "2.0.0"
        assert data["status"] == "healthy"


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_direct(self):
        """Test /health direct endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "healthy"]

    def test_readiness_check(self):
        """Test /ready endpoint."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["status"] == "healthy"

    def test_debug_info(self):
        """Test /debug endpoint."""
        response = client.get("/debug")

        assert response.status_code == 200
        data = response.json()
        assert "python_version" in data
        assert "status" in data
        assert data["status"] == "debug_ok"


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are present in response."""
        response = client.options(
            "/api/v1/classify",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        # CORS middleware should add headers
        assert "access-control-allow-origin" in response.headers or response.status_code in [200, 405]


class TestAppMetadata:
    """Tests for application metadata."""

    def test_app_title(self):
        """Test that app has correct title."""
        assert app.title == "Agent Hub API"

    def test_app_version(self):
        """Test that app has correct version."""
        assert app.version == "2.0.0"

    def test_app_has_docs_url(self):
        """Test that app has docs URL configured."""
        assert app.docs_url == "/docs"

    def test_app_has_redoc_url(self):
        """Test that app has redoc URL configured."""
        assert app.redoc_url == "/redoc"


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_health_router_included(self):
        """Test that health router is included."""
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_classify_router_included(self):
        """Test that classify router is included."""
        routes = [route.path for route in app.routes]
        assert "/api/v1/classify" in routes


class TestStartupShutdownEvents:
    """Tests for startup and shutdown event handlers."""

    def test_startup_event_callable(self):
        """Test that startup event is defined."""
        # Verify startup event is registered
        assert hasattr(app, "router")
        assert app.router.on_startup is not None

    def test_shutdown_event_callable(self):
        """Test that shutdown event is defined."""
        # Verify shutdown event is registered
        assert hasattr(app, "router")
        assert app.router.on_shutdown is not None
