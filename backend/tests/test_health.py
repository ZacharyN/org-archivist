"""
Integration tests for health check and system endpoints.
"""
import pytest


def test_health_check(client):
    """Test the health check endpoint returns expected structure."""
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "org-archivist-backend"
    assert "version" in data
    assert "checks" in data
    assert data["checks"]["api"] == "ok"


def test_root_endpoint(client):
    """Test the root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Org Archivist API"
    assert "version" in data
    assert "description" in data
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/api/health"
    assert data["metrics_url"] == "/api/metrics"


def test_metrics_endpoint(client):
    """Test the metrics endpoint returns performance data."""
    # Make some requests first
    client.get("/api/health")
    client.get("/")

    response = client.get("/api/metrics")

    assert response.status_code == 200

    data = response.json()
    assert "total_requests" in data
    assert "total_errors" in data
    assert "error_rate" in data
    assert "avg_response_time_ms" in data
    assert int(data["total_requests"]) >= 3  # At least the 3 requests we made


def test_request_id_header(client):
    """Test that all responses include X-Request-ID header."""
    response = client.get("/api/health")

    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 36  # UUID length


def test_process_time_header(client):
    """Test that all responses include X-Process-Time header."""
    response = client.get("/api/health")

    assert "X-Process-Time" in response.headers
    assert "ms" in response.headers["X-Process-Time"]


def test_not_found_error(client):
    """Test that 404 errors are handled properly."""
    response = client.get("/api/nonexistent")

    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert "request_id" in data
    assert data["error"] == "Resource not found"


def test_method_not_allowed(client):
    """Test that 405 Method Not Allowed errors are handled."""
    # Try to POST to a GET-only endpoint
    response = client.post("/api/health")

    assert response.status_code == 405

    data = response.json()
    assert "error" in data
    assert data["error"] == "Method not allowed"
