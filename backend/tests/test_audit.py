"""
Comprehensive Audit Log API Tests

Tests for Phase 5: Context & Sensitivity - Audit Log Viewing Endpoints
- Query audit logs with filtering and pagination (Admin only)
- Get entity-specific audit logs (Admin only)
- Role-based access control enforcement
- Filter and pagination functionality
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from uuid import uuid4

from backend.app.main import app
from backend.app.db.models import User, UserRole, AuditLog
from backend.app.db.session import get_db
from backend.app.services.auth_service import AuthService


@pytest.fixture(scope="function")
async def test_users(db_session):
    """Create test users with different roles"""
    users = {}

    # Create admin user
    admin = User(
        user_id=uuid4(),
        email="admin@test.com",
        hashed_password=AuthService.hash_password("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(admin)
    users["admin"] = {"user": admin, "password": "AdminPass123!"}

    # Create editor user
    editor = User(
        user_id=uuid4(),
        email="editor@test.com",
        hashed_password=AuthService.hash_password("EditorPass123!"),
        full_name="Editor User",
        role=UserRole.EDITOR,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(editor)
    users["editor"] = {"user": editor, "password": "EditorPass123!"}

    # Create writer user
    writer = User(
        user_id=uuid4(),
        email="writer@test.com",
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


@pytest.fixture(scope="function")
async def test_audit_logs(db_session, test_users):
    """Create test audit log entries"""
    audit_logs = []

    # Test entity IDs
    doc_id_1 = uuid4()
    doc_id_2 = uuid4()
    output_id_1 = uuid4()

    # Create document upload audit logs
    log1 = AuditLog(
        log_id=uuid4(),
        event_type="document.upload",
        entity_type="document",
        entity_id=doc_id_1,
        user_id=str(test_users["editor"]["user"].user_id),
        details={
            "filename": "test_proposal_2024.pdf",
            "file_size": 1024000,
            "sensitivity_confirmed": True,
            "ip_address": "192.168.1.100"
        },
        created_at=datetime.utcnow() - timedelta(days=5)
    )
    db_session.add(log1)
    audit_logs.append(log1)

    log2 = AuditLog(
        log_id=uuid4(),
        event_type="document.upload",
        entity_type="document",
        entity_id=doc_id_2,
        user_id=str(test_users["editor"]["user"].user_id),
        details={
            "filename": "annual_report_2023.pdf",
            "file_size": 2048000,
            "sensitivity_confirmed": False,
            "ip_address": "192.168.1.100"
        },
        created_at=datetime.utcnow() - timedelta(days=3)
    )
    db_session.add(log2)
    audit_logs.append(log2)

    # Create output creation audit log
    log3 = AuditLog(
        log_id=uuid4(),
        event_type="output.create",
        entity_type="output",
        entity_id=output_id_1,
        user_id=str(test_users["writer"]["user"].user_id),
        details={
            "output_type": "grant_proposal",
            "title": "Youth Development Grant Proposal",
            "word_count": 1500,
            "ip_address": "192.168.1.101"
        },
        created_at=datetime.utcnow() - timedelta(days=2)
    )
    db_session.add(log3)
    audit_logs.append(log3)

    # Create user login audit logs
    log4 = AuditLog(
        log_id=uuid4(),
        event_type="user.login",
        entity_type="user",
        entity_id=test_users["admin"]["user"].user_id,
        user_id=str(test_users["admin"]["user"].user_id),
        details={
            "ip_address": "192.168.1.102",
            "user_agent": "Mozilla/5.0...",
            "success": True
        },
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    db_session.add(log4)
    audit_logs.append(log4)

    # Create document delete audit log for doc_id_1 (multiple logs for same entity)
    log5 = AuditLog(
        log_id=uuid4(),
        event_type="document.delete",
        entity_type="document",
        entity_id=doc_id_1,
        user_id=str(test_users["admin"]["user"].user_id),
        details={
            "filename": "test_proposal_2024.pdf",
            "reason": "outdated",
            "ip_address": "192.168.1.102"
        },
        created_at=datetime.utcnow()
    )
    db_session.add(log5)
    audit_logs.append(log5)

    await db_session.commit()

    # Refresh to get IDs
    for log in audit_logs:
        await db_session.refresh(log)

    return {
        "logs": audit_logs,
        "doc_id_1": doc_id_1,
        "doc_id_2": doc_id_2,
        "output_id_1": output_id_1
    }


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class TestAuditLogQuery:
    """Test audit log query endpoint"""

    @pytest.mark.asyncio
    async def test_admin_can_query_all_logs(self, client, test_users, test_audit_logs):
        """Test that admin can query all audit logs"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Query all audit logs
        response = client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "logs" in data
        assert "total_count" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        # Should have all 5 audit logs
        assert data["total_count"] == 5
        assert len(data["logs"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 50

        # Verify logs are sorted by created_at DESC (most recent first)
        assert data["logs"][0]["event_type"] == "document.delete"  # Most recent
        assert data["logs"][4]["event_type"] == "document.upload"  # Oldest

    @pytest.mark.asyncio
    async def test_filter_by_event_type(self, client, test_users, test_audit_logs):
        """Test filtering audit logs by event type"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Filter by document.upload event type
        response = client.get(
            "/api/audit/logs?event_type=document.upload",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 2 document.upload logs
        assert data["total_count"] == 2
        assert len(data["logs"]) == 2

        # All should be document.upload
        for log in data["logs"]:
            assert log["event_type"] == "document.upload"

    @pytest.mark.asyncio
    async def test_filter_by_entity_type(self, client, test_users, test_audit_logs):
        """Test filtering audit logs by entity type"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Filter by document entity type
        response = client.get(
            "/api/audit/logs?entity_type=document",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 3 document logs (2 uploads + 1 delete)
        assert data["total_count"] == 3
        assert len(data["logs"]) == 3

        # All should have entity_type "document"
        for log in data["logs"]:
            assert log["entity_type"] == "document"

    @pytest.mark.asyncio
    async def test_filter_by_user_id(self, client, test_users, test_audit_logs):
        """Test filtering audit logs by user ID"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Filter by editor user ID
        editor_user_id = str(test_users["editor"]["user"].user_id)
        response = client.get(
            f"/api/audit/logs?user_id={editor_user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 2 logs from editor
        assert data["total_count"] == 2
        assert len(data["logs"]) == 2

        # All should have editor's user_id
        for log in data["logs"]:
            assert log["user_id"] == editor_user_id

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, client, test_users, test_audit_logs):
        """Test filtering audit logs by date range"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Filter logs from last 3 days
        start_date = (datetime.utcnow() - timedelta(days=3)).isoformat()
        response = client.get(
            f"/api/audit/logs?start_date={start_date}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 4 logs (last 3 days worth)
        assert data["total_count"] == 4
        assert len(data["logs"]) == 4

    @pytest.mark.asyncio
    async def test_pagination(self, client, test_users, test_audit_logs):
        """Test pagination of audit logs"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Get first page with 2 logs per page
        response_page1 = client.get(
            "/api/audit/logs?page=1&per_page=2",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response_page1.status_code == 200
        data_page1 = response_page1.json()

        assert data_page1["total_count"] == 5
        assert len(data_page1["logs"]) == 2
        assert data_page1["page"] == 1
        assert data_page1["per_page"] == 2
        assert data_page1["total_pages"] == 3  # 5 logs / 2 per page = 3 pages

        # Get second page
        response_page2 = client.get(
            "/api/audit/logs?page=2&per_page=2",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response_page2.status_code == 200
        data_page2 = response_page2.json()

        assert len(data_page2["logs"]) == 2
        assert data_page2["page"] == 2

        # Verify different logs on different pages
        page1_ids = [log["log_id"] for log in data_page1["logs"]]
        page2_ids = [log["log_id"] for log in data_page2["logs"]]
        assert set(page1_ids).isdisjoint(set(page2_ids))  # No overlap

    @pytest.mark.asyncio
    async def test_combined_filters(self, client, test_users, test_audit_logs):
        """Test combining multiple filters"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Filter by event_type AND entity_type
        response = client.get(
            "/api/audit/logs?event_type=document.upload&entity_type=document",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 2 document upload logs
        assert data["total_count"] == 2
        for log in data["logs"]:
            assert log["event_type"] == "document.upload"
            assert log["entity_type"] == "document"


class TestEntityAuditLogs:
    """Test entity-specific audit log endpoint"""

    @pytest.mark.asyncio
    async def test_get_entity_audit_logs(self, client, test_users, test_audit_logs):
        """Test getting audit logs for specific entity"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Get logs for doc_id_1 (should have upload + delete)
        doc_id_1 = test_audit_logs["doc_id_1"]
        response = client.get(
            f"/api/audit/logs/entity/document/{doc_id_1}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 2 logs for this document
        assert len(data) == 2
        assert isinstance(data, list)

        # Verify both logs are for the same entity
        for log in data:
            assert log["entity_id"] == str(doc_id_1)
            assert log["entity_type"] == "document"

        # Should be sorted by created_at DESC
        assert data[0]["event_type"] == "document.delete"  # Most recent
        assert data[1]["event_type"] == "document.upload"  # Older

    @pytest.mark.asyncio
    async def test_get_entity_audit_logs_single(self, client, test_users, test_audit_logs):
        """Test getting audit logs for entity with single log"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Get logs for output_id_1 (should have only 1 log)
        output_id_1 = test_audit_logs["output_id_1"]
        response = client.get(
            f"/api/audit/logs/entity/output/{output_id_1}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have 1 log
        assert len(data) == 1
        assert data[0]["entity_id"] == str(output_id_1)
        assert data[0]["entity_type"] == "output"
        assert data[0]["event_type"] == "output.create"

    @pytest.mark.asyncio
    async def test_get_entity_audit_logs_nonexistent(self, client, test_users, test_audit_logs):
        """Test getting audit logs for nonexistent entity returns empty list"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Get logs for nonexistent entity
        fake_id = uuid4()
        response = client.get(
            f"/api/audit/logs/entity/document/{fake_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty list
        assert data == []


class TestRoleBasedAccessControl:
    """Test role-based access control for audit endpoints"""

    @pytest.mark.asyncio
    async def test_editor_cannot_query_audit_logs(self, client, test_users, test_audit_logs):
        """Test that editor cannot access audit logs (admin only)"""
        # Login as editor
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "editor@test.com",
                "password": "EditorPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Try to query audit logs
        response = client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "Admin access required" in data["detail"]

    @pytest.mark.asyncio
    async def test_writer_cannot_query_audit_logs(self, client, test_users, test_audit_logs):
        """Test that writer cannot access audit logs (admin only)"""
        # Login as writer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "writer@test.com",
                "password": "WriterPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Try to query audit logs
        response = client.get(
            "/api/audit/logs",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_editor_cannot_get_entity_audit_logs(self, client, test_users, test_audit_logs):
        """Test that editor cannot access entity audit logs (admin only)"""
        # Login as editor
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "editor@test.com",
                "password": "EditorPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Try to get entity audit logs
        doc_id = test_audit_logs["doc_id_1"]
        response = client.get(
            f"/api/audit/logs/entity/document/{doc_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "Admin access required" in data["detail"]

    @pytest.mark.asyncio
    async def test_writer_cannot_get_entity_audit_logs(self, client, test_users, test_audit_logs):
        """Test that writer cannot access entity audit logs (admin only)"""
        # Login as writer
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "writer@test.com",
                "password": "WriterPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Try to get entity audit logs
        doc_id = test_audit_logs["doc_id_1"]
        response = client.get(
            f"/api/audit/logs/entity/document/{doc_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_access(self, client, test_audit_logs):
        """Test that unauthenticated users cannot access audit endpoints"""
        # Try without token
        response1 = client.get("/api/audit/logs")
        assert response1.status_code == 401

        doc_id = test_audit_logs["doc_id_1"]
        response2 = client.get(f"/api/audit/logs/entity/document/{doc_id}")
        assert response2.status_code == 401


class TestAuditLogValidation:
    """Test validation and edge cases"""

    @pytest.mark.asyncio
    async def test_invalid_page_number(self, client, test_users, test_audit_logs):
        """Test that invalid page number is rejected"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Try with page=0 (should be >= 1)
        response = client.get(
            "/api/audit/logs?page=0",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_invalid_per_page(self, client, test_users, test_audit_logs):
        """Test that invalid per_page value is rejected"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Try with per_page=150 (max is 100)
        response = client.get(
            "/api/audit/logs?per_page=150",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_empty_results(self, client, test_users, test_audit_logs):
        """Test that queries with no matches return empty results"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Query for nonexistent event type
        response = client.get(
            "/api/audit/logs?event_type=nonexistent.event",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert data["logs"] == []
        assert data["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_log_details_structure(self, client, test_users, test_audit_logs):
        """Test that log details are properly returned"""
        # Login as admin
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminPass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Get logs with details
        response = client.get(
            "/api/audit/logs?event_type=document.upload",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify log structure
        log = data["logs"][0]
        assert "log_id" in log
        assert "event_type" in log
        assert "entity_type" in log
        assert "entity_id" in log
        assert "user_id" in log
        assert "details" in log
        assert "created_at" in log

        # Verify details is a dictionary with expected fields
        assert isinstance(log["details"], dict)
        assert "filename" in log["details"]
        assert "file_size" in log["details"]
        assert "sensitivity_confirmed" in log["details"]
