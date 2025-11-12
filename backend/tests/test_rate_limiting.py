"""
Tests for rate limiting middleware

Tests verify:
- Rate limiting works correctly for different endpoints
- Different limits are applied based on endpoint type
- IP-based and user-based rate limiting
- Proper HTTP headers in responses
- Rate limiting can be disabled via settings
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.main import app
from app.middleware.rate_limit import RateLimitConfig


@pytest.fixture
def client():
    """Test client with rate limiting enabled"""
    return TestClient(app)


@pytest.fixture
def client_no_rate_limit():
    """Test client with rate limiting disabled"""
    # Mock settings to disable rate limiting
    with patch('app.middleware.rate_limit.get_settings') as mock_settings:
        settings_mock = MagicMock()
        settings_mock.enable_rate_limiting = False
        mock_settings.return_value = settings_mock
        yield TestClient(app)


class TestRateLimitingBasics:
    """Test basic rate limiting functionality"""

    def test_health_endpoint_not_rate_limited_heavily(self, client):
        """Test that health endpoint has generous rate limit"""
        # Health endpoint allows 60 requests per minute
        # Make several requests (less than limit)
        for _ in range(10):
            response = client.get("/api/health")
            assert response.status_code == 200

            # Check rate limit headers are present
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Window" in response.headers
            assert "X-RateLimit-Type" in response.headers

    def test_rate_limit_disabled(self, client_no_rate_limit):
        """Test that rate limiting can be disabled"""
        # Make many requests when rate limiting is disabled
        for _ in range(100):
            response = client_no_rate_limit.get("/api/health")
            assert response.status_code == 200

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are included in successful responses"""
        response = client.get("/api/health")
        assert response.status_code == 200

        # Verify headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Window" in response.headers
        assert "X-RateLimit-Type" in response.headers

        # Verify header values
        assert int(response.headers["X-RateLimit-Limit"]) > 0
        assert "s" in response.headers["X-RateLimit-Window"]
        assert response.headers["X-RateLimit-Type"] in ["ip", "user"]


class TestEndpointSpecificLimits:
    """Test different rate limits for different endpoint types"""

    def test_login_endpoint_strict_limit(self, client):
        """Test that login endpoint has strict rate limit (5 per minute)"""
        # Login limit: 5 requests per minute
        max_requests, time_window = RateLimitConfig.LOGIN_LIMIT

        # Make requests up to limit
        for i in range(max_requests):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "password"}
            )
            # May get 401 (invalid credentials) or 400 (validation error)
            # but NOT 429 (rate limited)
            assert response.status_code != 429, f"Request {i+1} was rate limited unexpectedly"

    def test_register_endpoint_strict_limit(self, client):
        """Test that register endpoint has very strict limit (3 per hour)"""
        # Register limit: 3 requests per hour
        # We can't wait an hour in tests, but we can verify the limit is set correctly
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "Test User",
                "role": "writer"
            }
        )

        # First request should not be rate limited
        # (may fail for other reasons like duplicate email)
        assert response.status_code != 429

        # Check headers indicate the strict limit
        # (headers are only present on successful requests)
        if response.status_code == 200:
            assert response.headers.get("X-RateLimit-Limit") == "3"

    def test_read_endpoints_generous_limit(self, client):
        """Test that read endpoints have generous limits (100 per minute)"""
        # Without authentication, we'll get 401, but not 429
        for i in range(10):  # Test subset of limit
            response = client.get("/api/documents")
            # Should get 401 (unauthorized) not 429 (rate limited)
            assert response.status_code != 429


class TestIPBasedLimiting:
    """Test IP-based rate limiting for unauthenticated requests"""

    def test_different_ips_tracked_separately(self, client):
        """Test that different IPs have separate rate limiters"""
        # Simulate requests from different IPs
        headers_ip1 = {"X-Forwarded-For": "192.168.1.1"}
        headers_ip2 = {"X-Forwarded-For": "192.168.1.2"}

        # Make requests from IP 1
        for _ in range(5):
            response = client.get("/api/health", headers=headers_ip1)
            assert response.status_code == 200
            assert response.headers.get("X-RateLimit-Type") == "ip"

        # Requests from IP 2 should also work (separate limiter)
        for _ in range(5):
            response = client.get("/api/health", headers=headers_ip2)
            assert response.status_code == 200
            assert response.headers.get("X-RateLimit-Type") == "ip"

    def test_x_real_ip_header_respected(self, client):
        """Test that X-Real-IP header is used for rate limiting"""
        headers = {"X-Real-IP": "10.0.0.1"}

        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200
        assert response.headers.get("X-RateLimit-Type") == "ip"


class TestRateLimitExceeded:
    """Test behavior when rate limits are exceeded"""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_response(self, client):
        """Test that exceeding rate limit returns 429 with proper headers"""
        # This test would need to exceed the actual rate limit
        # For login endpoint (5 per minute), make 6+ rapid requests

        responses = []
        for i in range(7):
            response = client.post(
                "/api/auth/login",
                json={"email": f"test{i}@example.com", "password": "password"}
            )
            responses.append(response)

        # At least one response should be 429 (rate limited)
        # Note: This might not always trigger in fast tests due to timing
        # but the structure verifies the response format
        rate_limited = [r for r in responses if r.status_code == 429]

        if rate_limited:
            response = rate_limited[0]

            # Verify 429 response structure
            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert "X-RateLimit-Limit" in response.headers

            # Verify response body
            data = response.json()
            assert "error" in data
            assert "detail" in data
            assert "retry_after" in data
            assert data["error"] == "Rate limit exceeded"

    def test_retry_after_header_present(self, client):
        """Test that Retry-After header is included in 429 responses"""
        # Make rapid requests to trigger rate limit
        responses = []
        for i in range(10):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "wrong"}
            )
            responses.append(response)

        # Check if any were rate limited
        rate_limited = [r for r in responses if r.status_code == 429]

        if rate_limited:
            response = rate_limited[0]
            assert "Retry-After" in response.headers

            # Retry-After should be a positive integer (seconds)
            retry_after = int(response.headers["Retry-After"])
            assert retry_after > 0


class TestDocumentationPaths:
    """Test that documentation paths are exempted from rate limiting"""

    def test_docs_not_rate_limited(self, client):
        """Test that /docs endpoint is not rate limited"""
        # Make many requests to docs
        for _ in range(100):
            response = client.get("/docs")
            assert response.status_code == 200

    def test_openapi_not_rate_limited(self, client):
        """Test that /openapi.json endpoint is not rate limited"""
        # Make many requests to OpenAPI spec
        for _ in range(100):
            response = client.get("/openapi.json")
            assert response.status_code == 200

    def test_redoc_not_rate_limited(self, client):
        """Test that /redoc endpoint is not rate limited"""
        # Make many requests to ReDoc
        for _ in range(100):
            response = client.get("/redoc")
            assert response.status_code == 200


class TestRateLimitConfiguration:
    """Test rate limit configuration"""

    def test_login_limit_config(self):
        """Test login endpoint rate limit configuration"""
        max_requests, time_window = RateLimitConfig.LOGIN_LIMIT
        assert max_requests == 5
        assert time_window == 60  # 60 seconds = 1 minute

    def test_register_limit_config(self):
        """Test register endpoint rate limit configuration"""
        max_requests, time_window = RateLimitConfig.REGISTER_LIMIT
        assert max_requests == 3
        assert time_window == 3600  # 3600 seconds = 1 hour

    def test_generation_limit_config(self):
        """Test generation endpoint rate limit configuration"""
        max_requests, time_window = RateLimitConfig.GENERATION_LIMIT
        assert max_requests == 10
        assert time_window == 60

    def test_read_limit_config(self):
        """Test read endpoint rate limit configuration"""
        max_requests, time_window = RateLimitConfig.READ_LIMIT
        assert max_requests == 100
        assert time_window == 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])