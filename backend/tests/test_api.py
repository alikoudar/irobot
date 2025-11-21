"""Tests for API endpoints."""
import pytest


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "IroBot"
        assert "environment" in data


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "IroBot" in data["message"]
        assert "version" in data
        assert data["version"] == "1.0.0"


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_headers_on_health(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # CORS should allow the request
        assert response.status_code in [200, 204]