"""
Unit tests for health check endpoint.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """
    Create test client.
    
    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """
    Test: Health endpoint returns status 200.
    
    Given: Application is running
    When: GET /health is called
    Then: Response status is 200
    """
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_correct_structure(client: TestClient) -> None:
    """
    Test: Health endpoint returns expected JSON structure.
    
    Given: Application is running
    When: GET /health is called
    Then: Response contains status, service, and version fields
    """
    response = client.get("/health")
    data = response.json()
    
    assert "status" in data
    assert "service" in data
    assert "version" in data


def test_health_endpoint_returns_healthy_status(client: TestClient) -> None:
    """
    Test: Health endpoint returns healthy status.
    
    Given: Application is running normally
    When: GET /health is called
    Then: Status is "healthy"
    """
    response = client.get("/health")
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "agent-hub"
    assert data["version"] == "2.0.0"


def test_root_endpoint_returns_200(client: TestClient) -> None:
    """
    Test: Root endpoint returns status 200.
    
    Given: Application is running
    When: GET / is called
    Then: Response status is 200
    """
    response = client.get("/")
    assert response.status_code == 200


def test_root_endpoint_returns_welcome_message(client: TestClient) -> None:
    """
    Test: Root endpoint returns welcome message.
    
    Given: Application is running
    When: GET / is called
    Then: Response contains welcome message
    """
    response = client.get("/")
    data = response.json()
    
    assert "message" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "healthy"
