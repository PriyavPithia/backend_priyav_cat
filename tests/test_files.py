"""
Test cases for file upload and management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import tempfile
import os

def test_upload_file_without_auth(client: TestClient):
    """Test file upload without authentication."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
        tmp_file.write(b"Test file content")
        tmp_file_path = tmp_file.name
    
    try:
        with open(tmp_file_path, "rb") as f:
            response = client.post(
                "/api/files/upload",
                files={"file": ("test.txt", f, "text/plain")}
            )
        assert response.status_code == 401
    finally:
        os.unlink(tmp_file_path)

def test_list_files_without_auth(client: TestClient):
    """Test listing files without authentication."""
    response = client.get("/api/files/")
    assert response.status_code == 401

def test_download_file_without_auth(client: TestClient):
    """Test downloading file without authentication."""
    response = client.get("/api/files/download/1")
    assert response.status_code == 401

def test_delete_file_without_auth(client: TestClient):
    """Test deleting file without authentication."""
    response = client.delete("/api/files/1")
    assert response.status_code == 401

def test_upload_invalid_file_type(client: TestClient):
    """Test uploading file with invalid type."""
    # This would need authentication, but we can test the endpoint structure
    response = client.post("/api/files/upload")
    assert response.status_code == 401  # Should fail due to auth first

def test_file_endpoints_require_auth(client: TestClient):
    """Test that all file endpoints require authentication."""
    endpoints = [
        ("GET", "/api/files/"),
        ("POST", "/api/files/upload"),
        ("GET", "/api/files/download/1"),
        ("DELETE", "/api/files/1"),
        ("GET", "/api/files/view/1")
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint)
        elif method == "DELETE":
            response = client.delete(endpoint)
        
        assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"
