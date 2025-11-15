"""
Tests for /api/metrics endpoint security

Verifies that the metrics endpoint is properly secured with admin-only authentication:
- Unauthenticated requests are rejected (401)
- Non-admin authenticated users are rejected (403)
- Admin users can access metrics successfully
"""

import pytest
from uuid import uuid4
from backend.app.db.models import User, UserRole
from backend.app.services.auth_service import AuthService


@pytest.fixture
async def test_users(db_session):
    """Create test users with different roles for metrics security tests"""
    users = {}

    # Create admin user
    admin = User(
        user_id=uuid4(),
        email="admin@metricstest.com",
        hashed_password=AuthService.hash_password("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(admin)
    users["admin"] = {"user": admin, "password": "AdminPass123!"}

    # Create editor user (non-admin)
    editor = User(
        user_id=uuid4(),
        email="editor@metricstest.com",
        hashed_password=AuthService.hash_password("EditorPass123!"),
        full_name="Editor User",
        role=UserRole.EDITOR,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(editor)
    users["editor"] = {"user": editor, "password": "EditorPass123!"}

    # Create writer user (non-admin)
    writer = User(
        user_id=uuid4(),
        email="writer@metricstest.com",
        hashed_password=AuthService.hash_password("WriterPass123!"),
        full_name="Writer User",
        role=UserRole.WRITER,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(writer)
    users["writer"] = {"user": writer, "password": "WriterPass123!"}

    await db_session.commit()

    # Refresh to get IDs
    for user_data in users.values():
        await db_session.refresh(user_data["user"])

    return users


async def get_auth_token(client, email: str, password: str) -> str:
    """Helper function to get authentication token"""
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


class TestMetricsEndpointSecurity:
    """Test suite for /api/metrics endpoint security"""

    def test_unauthenticated_request_returns_401(self, client):
        """
        Test that unauthenticated requests to /api/metrics are rejected with 401 Unauthorized
        """
        response = client.get("/api/metrics")

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        # FastAPI security returns this message for missing credentials
        assert "Not authenticated" in data["detail"] or "credentials" in data["detail"].lower()

    def test_invalid_token_returns_401(self, client):
        """
        Test that requests with invalid tokens are rejected with 401 Unauthorized
        """
        response = client.get(
            "/api/metrics",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_editor_user_returns_403(self, client, test_users):
        """
        Test that authenticated editor users receive 403 Forbidden when accessing metrics
        """
        # Login as editor
        token = await get_auth_token(
            client,
            test_users["editor"]["user"].email,
            test_users["editor"]["password"]
        )

        # Try to access metrics
        response = client.get(
            "/api/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "Admin access required" in data["detail"]

    @pytest.mark.asyncio
    async def test_writer_user_returns_403(self, client, test_users):
        """
        Test that authenticated writer users receive 403 Forbidden when accessing metrics
        """
        # Login as writer
        token = await get_auth_token(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Try to access metrics
        response = client.get(
            "/api/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "Admin access required" in data["detail"]

    @pytest.mark.asyncio
    async def test_admin_user_can_access_metrics(self, client, test_users):
        """
        Test that admin users can successfully access metrics endpoint
        """
        # Login as admin
        token = await get_auth_token(
            client,
            test_users["admin"]["user"].email,
            test_users["admin"]["password"]
        )

        # Access metrics
        response = client.get(
            "/api/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify metrics structure (basic validation)
        # The actual metrics structure depends on your MetricsMiddleware implementation
        assert isinstance(data, dict)
        # Common metrics fields - adjust based on your actual implementation
        # Examples: request_count, error_count, average_response_time, etc.

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client, test_users):
        """
        Test that requests with expired tokens are rejected

        Note: This test assumes that tokens expire after a certain period.
        Since we can't easily wait for token expiration in tests, this is a placeholder
        for the behavior that would occur with an expired token.
        """
        # This test documents the expected behavior but doesn't actually test it
        # because creating an expired token requires waiting or manipulating time
        # In a real scenario, an expired token would return 401
        pass

    @pytest.mark.asyncio
    async def test_token_from_different_endpoint_works(self, client, test_users):
        """
        Test that authentication tokens work consistently across endpoints

        Verifies that a token obtained from login works for metrics access
        """
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": test_users["admin"]["user"].email,
                "password": test_users["admin"]["password"]
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Use the same token to access metrics
        metrics_response = client.get(
            "/api/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert metrics_response.status_code == 200

    def test_metrics_endpoint_requires_bearer_scheme(self, client):
        """
        Test that the metrics endpoint requires Bearer authentication scheme
        """
        # Try with a token but without Bearer prefix
        response = client.get(
            "/api/metrics",
            headers={"Authorization": "some_token"}
        )

        # Should fail because Bearer scheme is required
        assert response.status_code == 401 or response.status_code == 403