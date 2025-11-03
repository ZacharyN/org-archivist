"""
Outputs API Integration Tests

Tests for Phase 4: Past Outputs Dashboard
- POST /api/outputs - Create output
- GET /api/outputs - List outputs with filtering
- GET /api/outputs/stats - Statistics
- GET /api/outputs/{id} - Get single output
- PUT /api/outputs/{id} - Update output
- DELETE /api/outputs/{id} - Delete output
- Analytics endpoints (style, funder, year, summary, funders)

Tests cover:
- CRUD operations
- Permission checks (Writer/Editor/Admin roles)
- Authentication requirements (401 errors)
- Error handling (403, 404, 422, 500)
- Request/response validation
- Status transition validation
- Data filtering and search
"""

import pytest
import pytest_asyncio
from datetime import datetime, date
from fastapi.testclient import TestClient
from uuid import uuid4

from backend.app.main import app
from backend.app.db.models import User, UserRole, Output, WritingStyle
from backend.app.db.session import get_db
from backend.app.services.auth_service import AuthService
from backend.tests.conftest import mock_lifespan

# Database fixtures (db_engine, db_session) are now imported from conftest.py


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

    # Create second writer for permission tests
    writer2 = User(
        user_id=uuid4(),
        email="writer2@test.com",
        hashed_password=AuthService.hash_password("Writer2Pass123!"),
        full_name="Writer Two",
        role=UserRole.WRITER,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(writer2)
    users["writer2"] = {"user": writer2, "password": "Writer2Pass123!"}

    await db_session.commit()

    # Refresh to get IDs
    for user_data in users.values():
        await db_session.refresh(user_data["user"])

    return users


@pytest.fixture(scope="function")
async def test_writing_style(db_session, test_users):
    """Create a test writing style"""
    style = WritingStyle(
        style_id=uuid4(),
        name="Test Grant Style",
        type="grant",
        description="A test writing style for grants",
        prompt_content="Write clearly and concisely. This is a sample grant proposal...",
        created_by=test_users["writer"]["user"].user_id,
    )
    db_session.add(style)
    await db_session.commit()
    await db_session.refresh(style)
    return style


@pytest.fixture(scope="function")
async def test_outputs(db_session, test_users, test_writing_style):
    """Create test outputs for various scenarios"""
    outputs = []

    # Writer 1's outputs
    # Draft output
    output1 = Output(
        output_id=uuid4(),
        output_type="grant_proposal",
        title="Test Grant Proposal - Draft",
        content="This is a draft grant proposal content...",
        word_count=500,
        status="draft",
        writing_style_id=test_writing_style.style_id,
        created_by=test_users["writer"]["user"].email,
    )
    db_session.add(output1)
    outputs.append(output1)

    # Submitted output
    output2 = Output(
        output_id=uuid4(),
        output_type="grant_proposal",
        title="NSF Grant - Submitted",
        content="This is a submitted NSF grant proposal...",
        word_count=1500,
        status="submitted",
        funder_name="National Science Foundation",
        requested_amount=500000.00,
        submission_date=date(2024, 1, 15),
        writing_style_id=test_writing_style.style_id,
        created_by=test_users["writer"]["user"].email,
    )
    db_session.add(output2)
    outputs.append(output2)

    # Awarded output
    output3 = Output(
        output_id=uuid4(),
        output_type="grant_proposal",
        title="NIH Grant - Awarded",
        content="This is an awarded NIH grant...",
        word_count=2000,
        status="awarded",
        funder_name="National Institutes of Health",
        requested_amount=750000.00,
        awarded_amount=700000.00,
        submission_date=date(2024, 2, 1),
        decision_date=date(2024, 5, 15),
        success_notes="Successfully funded! Great collaboration mentioned.",
        writing_style_id=test_writing_style.style_id,
        created_by=test_users["writer"]["user"].email,
    )
    db_session.add(output3)
    outputs.append(output3)

    # Writer 2's output
    output4 = Output(
        output_id=uuid4(),
        output_type="other",
        title="LOI - Foundation XYZ",
        content="This is a letter of inquiry...",
        word_count=800,
        status="pending",
        funder_name="Foundation XYZ",
        requested_amount=100000.00,
        submission_date=date(2024, 3, 10),
        created_by=test_users["writer2"]["user"].email,
    )
    db_session.add(output4)
    outputs.append(output4)

    await db_session.commit()

    # Refresh all outputs
    for output in outputs:
        await db_session.refresh(output)

    return outputs


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Disable lifespan during tests to avoid database connection issues
    # The lifespan tries to connect to real PostgreSQL before override takes effect
    # Save original lifespan and replace with mock that does nothing
    original_router_lifespan = app.router.lifespan_context
    app.router.lifespan_context = mock_lifespan

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Restore original lifespan
        app.router.lifespan_context = original_router_lifespan
        app.dependency_overrides.clear()


def get_auth_token(client, email, password):
    """Helper function to get authentication token"""
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


# ======================
# POST /api/outputs - Create Output Tests
# ======================


class TestCreateOutput:
    """Test POST /api/outputs endpoint"""

    def test_create_output_authenticated_user(self, client, test_users):
        """Test successful output creation by authenticated user"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "New Grant Proposal",
                "content": "This is the content of the grant proposal...",
                "word_count": 1000,
                "status": "draft"
            },
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Grant Proposal"
        assert data["status"] == "draft"
        assert data["created_by"] == "writer@test.com"
        assert "output_id" in data

    def test_create_output_with_writing_style(self, client, test_users, test_writing_style):
        """Test creating output with writing style"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Styled Grant",
                "content": "Content following the style...",
                "word_count": 800,
                "status": "draft",
                "writing_style_id": str(test_writing_style.style_id)
            },
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["writing_style_id"] == str(test_writing_style.style_id)

    def test_create_output_minimal_data(self, client, test_users):
        """Test creating output with only required fields"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Minimal",
                "content": "Content",
                "status": "draft"
            },
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal"

    def test_create_output_unauthenticated(self, client):
        """Test creating output without authentication fails"""
        response = client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Test",
                "content": "Content",
                "status": "draft"
            }
        )

        assert response.status_code == 401

    def test_create_output_validation_error(self, client, test_users):
        """Test creating output with invalid data"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        # Missing required field 'content'
        response = client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Test",
                "status": "draft"
            },
            headers=headers
        )

        assert response.status_code == 422


# ======================
# GET /api/outputs - List Outputs Tests
# ======================


class TestListOutputs:
    """Test GET /api/outputs endpoint"""

    
    def test_list_outputs_as_writer(self, client, test_users, test_outputs):
        """Test that writers only see their own outputs"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/outputs", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) == 3  # Writer 1 has 3 outputs
        for output in data["outputs"]:
            assert output["created_by"] == "writer@test.com"

    
    def test_list_outputs_as_editor(self, client, test_users, test_outputs):
        """Test that editors see all outputs"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/outputs", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) == 4  # All outputs visible

    
    def test_list_outputs_as_admin(self, client, test_users, test_outputs):
        """Test that admins see all outputs"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/outputs", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) == 4  # All outputs visible

    
    def test_list_outputs_with_type_filter(self, client, test_users, test_outputs):
        """Test filtering outputs by type"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs?output_type=grant_proposal",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) == 3  # 3 grant proposals
        for output in data["outputs"]:
            assert output["output_type"] == "grant_proposal"

    
    def test_list_outputs_with_status_filter(self, client, test_users, test_outputs):
        """Test filtering outputs by status"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs?status=awarded",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) == 1
        assert data["outputs"][0]["status"] == "awarded"

    
    def test_list_outputs_with_search_query(self, client, test_users, test_outputs):
        """Test searching outputs by title/content"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs?search=NSF",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) >= 1
        # Should find the NSF grant

    
    def test_list_outputs_pagination(self, client, test_users, test_outputs):
        """Test pagination with skip and limit"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs?skip=0&limit=2",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["outputs"]) <= 2
        assert data["per_page"] == 2

    
    def test_list_outputs_unauthenticated(self, client):
        """Test listing outputs without authentication fails"""
        response = client.get("/api/outputs")
        assert response.status_code == 401


# ======================
# GET /api/outputs/stats - Statistics Tests
# ======================


class TestGetStats:
    """Test GET /api/outputs/stats endpoint"""

    
    def test_get_stats_as_writer(self, client, test_users, test_outputs):
        """Test that writers get stats for their own outputs only"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/outputs/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_outputs"] == 3  # Writer 1's outputs only
        assert "by_type" in data
        assert "by_status" in data

    
    def test_get_stats_as_editor(self, client, test_users, test_outputs):
        """Test that editors get stats for all outputs"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/outputs/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_outputs"] == 4  # All outputs

    
    def test_get_stats_with_type_filter(self, client, test_users, test_outputs):
        """Test getting stats filtered by output type"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs/stats?output_type=grant_proposal",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_outputs"] == 3  # Only grant proposals

    
    def test_get_stats_success_rate_calculation(self, client, test_users, test_outputs):
        """Test that success rate is calculated correctly"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/outputs/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        # Writer 1 has 1 awarded out of 2 submitted/awarded total
        # Success rate should be calculable
        assert "success_rate" in data


# ======================
# GET /api/outputs/{id} - Get Single Output Tests
# ======================


class TestGetOutput:
    """Test GET /api/outputs/{id} endpoint"""

    
    def test_get_output_as_owner(self, client, test_users, test_outputs):
        """Test that owner can view their own output"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id
        response = client.get(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["output_id"] == str(output_id)

    
    def test_get_output_as_editor(self, client, test_users, test_outputs):
        """Test that editor can view any output"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[3].output_id  # Writer 2's output
        response = client.get(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["output_id"] == str(output_id)

    
    def test_get_output_as_admin(self, client, test_users, test_outputs):
        """Test that admin can view any output"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[3].output_id  # Writer 2's output
        response = client.get(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["output_id"] == str(output_id)

    
    def test_get_output_as_other_writer(self, client, test_users, test_outputs):
        """Test that writer cannot view another writer's output"""
        token = get_auth_token(client, "writer2@test.com", "Writer2Pass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id  # Writer 1's output
        response = client.get(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 403

    
    def test_get_output_not_found(self, client, test_users):
        """Test getting non-existent output returns 404"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        fake_id = uuid4()
        response = client.get(f"/api/outputs/{fake_id}", headers=headers)

        assert response.status_code == 404


# ======================
# PUT /api/outputs/{id} - Update Output Tests
# ======================


class TestUpdateOutput:
    """Test PUT /api/outputs/{id} endpoint"""

    
    def test_update_output_as_owner(self, client, test_users, test_outputs):
        """Test that owner can update their own output"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"title": "Updated Title"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    
    def test_update_output_as_editor(self, client, test_users, test_outputs):
        """Test that editor can update any output"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[3].output_id  # Writer 2's output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"title": "Editor Updated Title"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Editor Updated Title"

    
    def test_update_output_as_admin(self, client, test_users, test_outputs):
        """Test that admin can update any output"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[3].output_id
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"content": "Admin updated content"},
            headers=headers
        )

        assert response.status_code == 200

    
    def test_update_output_as_other_writer(self, client, test_users, test_outputs):
        """Test that writer cannot update another writer's output"""
        token = get_auth_token(client, "writer2@test.com", "Writer2Pass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id  # Writer 1's output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"title": "Hacked Title"},
            headers=headers
        )

        assert response.status_code == 403

    
    def test_update_output_status_transition_valid(self, client, test_users, test_outputs):
        """Test valid status transition is allowed"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id  # Draft output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "submitted", "submission_date": "2024-06-01"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"

    
    def test_update_output_status_transition_invalid(self, client, test_users, test_outputs):
        """Test invalid status transition is rejected"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id  # Draft output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "awarded"},  # Cannot go from draft to awarded
            headers=headers
        )

        assert response.status_code == 422

    
    def test_update_output_admin_override(self, client, test_users, test_outputs):
        """Test that admin can override status transition rules"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id  # Draft output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "awarded"},  # Admin can override
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "awarded"


# ======================
# DELETE /api/outputs/{id} - Delete Output Tests
# ======================


class TestDeleteOutput:
    """Test DELETE /api/outputs/{id} endpoint"""

    
    def test_delete_output_as_owner(self, client, test_users, test_outputs):
        """Test that owner can delete their own output"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id
        response = client.delete(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    
    def test_delete_output_as_admin(self, client, test_users, test_outputs):
        """Test that admin can delete any output"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[3].output_id  # Writer 2's output
        response = client.delete(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 200

    
    def test_delete_output_as_editor(self, client, test_users, test_outputs):
        """Test that editor cannot delete others' outputs"""
        token = get_auth_token(client, "editor@test.com", "EditorPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[3].output_id  # Writer 2's output
        response = client.delete(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 403

    
    def test_delete_output_as_other_writer(self, client, test_users, test_outputs):
        """Test that writer cannot delete another writer's output"""
        token = get_auth_token(client, "writer2@test.com", "Writer2Pass123!")
        headers = {"Authorization": f"Bearer {token}"}

        output_id = test_outputs[0].output_id  # Writer 1's output
        response = client.delete(f"/api/outputs/{output_id}", headers=headers)

        assert response.status_code == 403

    
    def test_delete_output_not_found(self, client, test_users):
        """Test deleting non-existent output returns 404"""
        token = get_auth_token(client, "admin@test.com", "AdminPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        fake_id = uuid4()
        response = client.delete(f"/api/outputs/{fake_id}", headers=headers)

        assert response.status_code == 404


# ======================
# Analytics Endpoints Tests
# ======================


class TestAnalyticsEndpoints:
    """Test analytics endpoints"""

    
    def test_get_analytics_by_style(self, client, test_users, test_outputs, test_writing_style):
        """Test getting success rate by writing style"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        style_id = test_writing_style.style_id
        response = client.get(
            f"/api/outputs/analytics/style/{style_id}",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_outputs" in data

    
    def test_get_analytics_by_funder(self, client, test_users, test_outputs):
        """Test getting success rate by funder"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs/analytics/funder/National Science Foundation",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "funder_name" in data

    
    def test_get_analytics_by_year(self, client, test_users, test_outputs):
        """Test getting success rate by year"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs/analytics/year/2024",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "year" in data

    
    def test_get_analytics_summary(self, client, test_users, test_outputs):
        """Test getting comprehensive analytics summary"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs/analytics/summary",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "overall_stats" in data

    
    def test_get_analytics_funders(self, client, test_users, test_outputs):
        """Test getting funder performance metrics"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs/analytics/funders?limit=5",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ======================
# Error Handling Tests
# ======================


class TestErrorHandling:
    """Test error handling scenarios"""

    
    def test_invalid_uuid_format(self, client, test_users):
        """Test that invalid UUID format returns 422"""
        token = get_auth_token(client, "writer@test.com", "WriterPass123!")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(
            "/api/outputs/not-a-uuid",
            headers=headers
        )

        assert response.status_code == 422
