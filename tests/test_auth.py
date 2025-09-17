"""
Test cases for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

def test_health_endpoint(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]

def test_login_missing_fields(client: TestClient):
    """Test login with missing required fields."""
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser"}
    )
    assert response.status_code == 422

def test_register_missing_fields(client: TestClient):
    """Test registration with missing required fields."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com"}
    )
    assert response.status_code == 422

def test_refresh_token_invalid(client: TestClient):
    """Test refresh token with invalid token."""
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401

def test_protected_endpoint_without_token(client: TestClient):
    """Test accessing protected endpoint without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_logout_without_token(client: TestClient):
    """Test logout without token."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 401
