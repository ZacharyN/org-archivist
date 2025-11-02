"""
End-to-End Workflow Tests for Outputs and Success Tracking

Tests complete workflows from output creation through success tracking and analytics.
Covers:
- Complete grant lifecycle (draft → submitted → pending → awarded/not_awarded)
- Success tracking with funder information and outcome recording
- Multi-user scenarios and permission enforcement
- Data consistency across relationships
- Analytics aggregation and reporting

Pattern: Full integration tests using TestClient and test database
"""

import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from uuid import uuid4

from backend.app.main import app
from backend.app.db.models import Base, User, UserRole, Output, WritingStyle, Conversation
from backend.app.db.session import get_db
from backend.app.services.auth_service import AuthService


# Test database URL (uses in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def db_engine():
    """Create a test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        connect_args={"check_same_thread": False}
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create a test database session"""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


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

    # Create writer users
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
        writing_style_id=uuid4(),
        name="Test Grant Style",
        description="A test writing style for grants",
        guidelines="Write clearly and concisely",
        sample_text="This is a sample grant proposal...",
        created_by=test_users["writer"]["user"].email,
    )
    db_session.add(style)
    await db_session.commit()
    await db_session.refresh(style)
    return style


@pytest.fixture(scope="function")
async def test_conversation(db_session, test_users):
    """Create a test conversation"""
    conversation = Conversation(
        conversation_id=uuid4(),
        title="Grant Writing Conversation",
        created_by=test_users["writer"]["user"].email,
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    return conversation


@pytest.fixture
def client(db_session):
    """Create a test client with database override"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def get_auth_header(client, email, password):
    """Helper to get authentication token and header"""
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==================== Complete Grant Lifecycle Tests ====================

class TestCompleteGrantLifecycle:
    """Test complete grant lifecycle workflows"""

    @pytest.mark.asyncio
    async def test_complete_workflow_draft_to_awarded(
        self, client, test_users, test_writing_style
    ):
        """Test complete success path: draft → submitted → pending → awarded"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Step 1: Create draft output
        create_data = {
            "output_type": "grant_proposal",
            "title": "NSF Research Grant Proposal",
            "content": "This is a comprehensive research proposal for NSF funding...",
            "word_count": 2500,
            "status": "draft",
            "writing_style_id": str(test_writing_style.writing_style_id),
            "funder_name": "National Science Foundation",
            "requested_amount": 500000.00,
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        assert response.status_code == 200
        output_id = response.json()["output_id"]

        # Step 2: Update to submitted with submission date
        update_data = {
            "status": "submitted",
            "submission_date": "2024-01-15",
        }
        response = client.put(f"/api/outputs/{output_id}", json=update_data, headers=writer_auth)
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"
        assert response.json()["submission_date"] == "2024-01-15"

        # Step 3: Update to pending
        update_data = {"status": "pending"}
        response = client.put(f"/api/outputs/{output_id}", json=update_data, headers=writer_auth)
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

        # Step 4: Update to awarded with decision data
        update_data = {
            "status": "awarded",
            "decision_date": "2024-03-15",
            "awarded_amount": 475000.00,
            "success_notes": "Excellent proposal! Reviewers praised the methodology.",
        }
        response = client.put(f"/api/outputs/{output_id}", json=update_data, headers=writer_auth)
        assert response.status_code == 200
        result = response.json()

        # Verify all data captured correctly
        assert result["status"] == "awarded"
        assert result["decision_date"] == "2024-03-15"
        assert result["awarded_amount"] == 475000.00
        assert result["requested_amount"] == 500000.00
        assert result["success_notes"] == "Excellent proposal! Reviewers praised the methodology."

    @pytest.mark.asyncio
    async def test_complete_workflow_draft_to_not_awarded(
        self, client, test_users, test_writing_style
    ):
        """Test rejection path: draft → submitted → pending → not_awarded"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create and submit output
        create_data = {
            "output_type": "grant_proposal",
            "title": "Department of Energy Grant",
            "content": "Proposal content...",
            "word_count": 3000,
            "status": "draft",
            "funder_name": "Department of Energy",
            "requested_amount": 750000.00,
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        output_id = response.json()["output_id"]

        # Submit
        client.put(
            f"/api/outputs/{output_id}",
            json={"status": "submitted", "submission_date": "2024-02-01"},
            headers=writer_auth
        )

        # Pending
        client.put(f"/api/outputs/{output_id}", json={"status": "pending"}, headers=writer_auth)

        # Not awarded with notes
        update_data = {
            "status": "not_awarded",
            "decision_date": "2024-04-01",
            "success_notes": "Competition was very strong this year. Encouraged to resubmit next cycle.",
        }
        response = client.put(f"/api/outputs/{output_id}", json=update_data, headers=writer_auth)
        assert response.status_code == 200
        result = response.json()

        assert result["status"] == "not_awarded"
        assert result["decision_date"] == "2024-04-01"
        assert result["awarded_amount"] is None
        assert "resubmit" in result["success_notes"]

    @pytest.mark.asyncio
    async def test_workflow_with_revisions(
        self, client, test_users, test_writing_style
    ):
        """Test back-and-forth workflow: submitted → draft → submitted → pending → awarded"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create and submit
        create_data = {
            "output_type": "grant_proposal",
            "title": "NIH Research Grant",
            "content": "Initial proposal content...",
            "word_count": 2000,
            "status": "submitted",
            "submission_date": "2024-01-10",
            "funder_name": "National Institutes of Health",
            "requested_amount": 400000.00,
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        output_id = response.json()["output_id"]

        # Back to draft for revisions
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "draft", "content": "Revised proposal content with improvements..."},
            headers=writer_auth
        )
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

        # Resubmit
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "submitted", "submission_date": "2024-01-25"},
            headers=writer_auth
        )
        assert response.status_code == 200

        # Pending → Awarded
        client.put(f"/api/outputs/{output_id}", json={"status": "pending"}, headers=writer_auth)
        response = client.put(
            f"/api/outputs/{output_id}",
            json={
                "status": "awarded",
                "decision_date": "2024-03-20",
                "awarded_amount": 400000.00,
            },
            headers=writer_auth
        )
        assert response.status_code == 200
        assert response.json()["status"] == "awarded"

    @pytest.mark.asyncio
    async def test_workflow_status_validation_enforcement(
        self, client, test_users, test_writing_style
    ):
        """Test that invalid status transitions are blocked"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create draft output
        create_data = {
            "output_type": "grant_proposal",
            "title": "Test Proposal",
            "content": "Content...",
            "word_count": 1000,
            "status": "draft",
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        output_id = response.json()["output_id"]

        # Try invalid transition: draft → awarded (should fail)
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "awarded"},
            headers=writer_auth
        )
        assert response.status_code == 422
        assert "transition" in response.json()["detail"].lower()

        # Try invalid transition: draft → pending (should fail)
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"status": "pending"},
            headers=writer_auth
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_workflow_admin_override(
        self, client, test_users, test_writing_style
    ):
        """Test that admin can override status transition rules"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )
        admin_auth = get_auth_header(
            client,
            test_users["admin"]["user"].email,
            test_users["admin"]["password"]
        )

        # Writer creates draft
        create_data = {
            "output_type": "grant_proposal",
            "title": "Admin Override Test",
            "content": "Content...",
            "word_count": 1000,
            "status": "draft",
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        output_id = response.json()["output_id"]

        # Admin can jump directly from draft → awarded
        response = client.put(
            f"/api/outputs/{output_id}",
            json={
                "status": "awarded",
                "decision_date": "2024-05-01",
                "awarded_amount": 100000.00,
            },
            headers=admin_auth
        )
        assert response.status_code == 200
        assert response.json()["status"] == "awarded"


# ==================== Success Tracking Integration Tests ====================

class TestSuccessTrackingIntegration:
    """Test success tracking workflows with complete funder data"""

    @pytest.mark.asyncio
    async def test_success_tracking_with_funder_info(
        self, client, test_users, test_writing_style
    ):
        """Test capturing complete funder data through the workflow"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create output with full funder information
        create_data = {
            "output_type": "grant_proposal",
            "title": "NASA Space Research Grant",
            "content": "Comprehensive space research proposal...",
            "word_count": 3500,
            "status": "submitted",
            "funder_name": "NASA - National Aeronautics and Space Administration",
            "requested_amount": 1000000.00,
            "submission_date": "2024-01-01",
            "writing_style_id": str(test_writing_style.writing_style_id),
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        output_id = response.json()["output_id"]

        # Update through workflow to awarded
        client.put(f"/api/outputs/{output_id}", json={"status": "pending"}, headers=writer_auth)

        update_data = {
            "status": "awarded",
            "decision_date": "2024-03-15",
            "awarded_amount": 950000.00,
            "success_notes": "Outstanding proposal with innovative methodology.",
        }
        response = client.put(f"/api/outputs/{output_id}", json=update_data, headers=writer_auth)
        result = response.json()

        # Verify data consistency
        assert result["funder_name"] == "NASA - National Aeronautics and Space Administration"
        assert result["requested_amount"] == 1000000.00
        assert result["awarded_amount"] == 950000.00
        assert result["submission_date"] == "2024-01-01"
        assert result["decision_date"] == "2024-03-15"

    @pytest.mark.asyncio
    async def test_success_tracking_multiple_grants_statistics(
        self, client, test_users, test_writing_style
    ):
        """Test statistics calculation with multiple grants"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create 5 outputs: 3 awarded, 2 not_awarded
        outputs = []
        for i in range(5):
            awarded = i < 3
            create_data = {
                "output_type": "grant_proposal",
                "title": f"Grant Proposal {i+1}",
                "content": f"Content for proposal {i+1}...",
                "word_count": 2000,
                "status": "awarded" if awarded else "not_awarded",
                "funder_name": f"Funder {i+1}",
                "requested_amount": 100000.00,
                "awarded_amount": 95000.00 if awarded else None,
                "submission_date": "2024-01-01",
                "decision_date": "2024-03-01",
            }
            response = client.post("/api/outputs", json=create_data, headers=writer_auth)
            outputs.append(response.json())

        # Get statistics
        response = client.get("/api/outputs/stats", headers=writer_auth)
        assert response.status_code == 200
        stats = response.json()

        # Verify success rate calculation (3/5 = 60%)
        assert stats["total_count"] == 5
        assert stats["awarded_count"] == 3
        assert stats["success_rate"] == 60.0
        assert stats["total_awarded_amount"] == 285000.00  # 3 * 95000
        assert stats["avg_awarded_amount"] == 95000.00

    @pytest.mark.asyncio
    async def test_success_tracking_by_writing_style(
        self, client, test_users, db_session
    ):
        """Test style-based analytics with different writing styles"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create two writing styles
        style1 = WritingStyle(
            writing_style_id=uuid4(),
            name="Formal Academic Style",
            description="Formal academic writing",
            guidelines="Use formal language",
            sample_text="Sample text...",
            created_by=test_users["writer"]["user"].email,
        )
        style2 = WritingStyle(
            writing_style_id=uuid4(),
            name="Conversational Style",
            description="More conversational approach",
            guidelines="Use accessible language",
            sample_text="Sample text...",
            created_by=test_users["writer"]["user"].email,
        )
        db_session.add(style1)
        db_session.add(style2)
        await db_session.commit()
        await db_session.refresh(style1)
        await db_session.refresh(style2)

        # Create outputs with style1 (2 awarded, 1 not_awarded)
        for i in range(3):
            create_data = {
                "output_type": "grant_proposal",
                "title": f"Style1 Grant {i+1}",
                "content": f"Content {i+1}...",
                "word_count": 2000,
                "status": "awarded" if i < 2 else "not_awarded",
                "writing_style_id": str(style1.writing_style_id),
                "requested_amount": 100000.00,
                "awarded_amount": 100000.00 if i < 2 else None,
            }
            client.post("/api/outputs", json=create_data, headers=writer_auth)

        # Create outputs with style2 (1 awarded, 2 not_awarded)
        for i in range(3):
            create_data = {
                "output_type": "grant_proposal",
                "title": f"Style2 Grant {i+1}",
                "content": f"Content {i+1}...",
                "word_count": 2000,
                "status": "awarded" if i < 1 else "not_awarded",
                "writing_style_id": str(style2.writing_style_id),
                "requested_amount": 100000.00,
                "awarded_amount": 100000.00 if i < 1 else None,
            }
            client.post("/api/outputs", json=create_data, headers=writer_auth)

        # Get analytics by style
        response = client.get(
            f"/api/outputs/analytics/style/{style1.writing_style_id}",
            headers=writer_auth
        )
        assert response.status_code == 200
        style1_analytics = response.json()
        assert style1_analytics["success_rate"] == pytest.approx(66.67, rel=0.1)  # 2/3

        response = client.get(
            f"/api/outputs/analytics/style/{style2.writing_style_id}",
            headers=writer_auth
        )
        assert response.status_code == 200
        style2_analytics = response.json()
        assert style2_analytics["success_rate"] == pytest.approx(33.33, rel=0.1)  # 1/3


# ==================== Multi-User Scenarios ====================

class TestMultiUserScenarios:
    """Test multi-user workflows and permission enforcement"""

    @pytest.mark.asyncio
    async def test_multi_user_data_isolation(
        self, client, test_users, test_writing_style
    ):
        """Test that writers see only their own outputs"""
        writer1_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )
        writer2_auth = get_auth_header(
            client,
            test_users["writer2"]["user"].email,
            test_users["writer2"]["password"]
        )

        # Writer 1 creates 3 outputs
        for i in range(3):
            create_data = {
                "output_type": "grant_proposal",
                "title": f"Writer1 Grant {i+1}",
                "content": "Content...",
                "word_count": 1000,
                "status": "draft",
            }
            client.post("/api/outputs", json=create_data, headers=writer1_auth)

        # Writer 2 creates 2 outputs
        for i in range(2):
            create_data = {
                "output_type": "grant_proposal",
                "title": f"Writer2 Grant {i+1}",
                "content": "Content...",
                "word_count": 1000,
                "status": "draft",
            }
            client.post("/api/outputs", json=create_data, headers=writer2_auth)

        # Writer 1 should see only their 3 outputs
        response = client.get("/api/outputs", headers=writer1_auth)
        assert response.status_code == 200
        assert len(response.json()) == 3
        for output in response.json():
            assert "Writer1" in output["title"]

        # Writer 2 should see only their 2 outputs
        response = client.get("/api/outputs", headers=writer2_auth)
        assert response.status_code == 200
        assert len(response.json()) == 2
        for output in response.json():
            assert "Writer2" in output["title"]

    @pytest.mark.asyncio
    async def test_multi_user_editor_visibility(
        self, client, test_users, test_writing_style
    ):
        """Test that editors can see all outputs"""
        writer1_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )
        writer2_auth = get_auth_header(
            client,
            test_users["writer2"]["user"].email,
            test_users["writer2"]["password"]
        )
        editor_auth = get_auth_header(
            client,
            test_users["editor"]["user"].email,
            test_users["editor"]["password"]
        )

        # Writers create outputs
        client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Writer1 Grant",
                "content": "Content...",
                "word_count": 1000,
                "status": "draft",
            },
            headers=writer1_auth
        )
        client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Writer2 Grant",
                "content": "Content...",
                "word_count": 1000,
                "status": "draft",
            },
            headers=writer2_auth
        )

        # Editor should see all outputs
        response = client.get("/api/outputs", headers=editor_auth)
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_multi_user_permissions_enforcement(
        self, client, test_users, test_writing_style
    ):
        """Test that permission checks work correctly across users"""
        writer1_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )
        writer2_auth = get_auth_header(
            client,
            test_users["writer2"]["user"].email,
            test_users["writer2"]["password"]
        )
        editor_auth = get_auth_header(
            client,
            test_users["editor"]["user"].email,
            test_users["editor"]["password"]
        )
        admin_auth = get_auth_header(
            client,
            test_users["admin"]["user"].email,
            test_users["admin"]["password"]
        )

        # Writer1 creates output
        response = client.post(
            "/api/outputs",
            json={
                "output_type": "grant_proposal",
                "title": "Writer1 Grant",
                "content": "Content...",
                "word_count": 1000,
                "status": "draft",
            },
            headers=writer1_auth
        )
        output_id = response.json()["output_id"]

        # Writer2 cannot edit Writer1's output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"title": "Modified by Writer2"},
            headers=writer2_auth
        )
        assert response.status_code == 403

        # Editor can edit Writer1's output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"title": "Modified by Editor"},
            headers=editor_auth
        )
        assert response.status_code == 200

        # Admin can edit and delete any output
        response = client.put(
            f"/api/outputs/{output_id}",
            json={"title": "Modified by Admin"},
            headers=admin_auth
        )
        assert response.status_code == 200

        response = client.delete(f"/api/outputs/{output_id}", headers=admin_auth)
        assert response.status_code == 200


# ==================== Data Consistency Tests ====================

class TestDataConsistency:
    """Test data consistency across relationships"""

    @pytest.mark.asyncio
    async def test_output_conversation_linking(
        self, client, test_users, test_conversation
    ):
        """Test linking output to conversation"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create output linked to conversation
        create_data = {
            "output_type": "grant_proposal",
            "title": "Grant from Conversation",
            "content": "Content generated from conversation...",
            "word_count": 2000,
            "status": "draft",
            "conversation_id": str(test_conversation.conversation_id),
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        assert response.status_code == 200

        output = response.json()
        assert output["conversation_id"] == str(test_conversation.conversation_id)

        # Retrieve output and verify relationship
        response = client.get(f"/api/outputs/{output['output_id']}", headers=writer_auth)
        assert response.status_code == 200
        assert response.json()["conversation_id"] == str(test_conversation.conversation_id)

    @pytest.mark.asyncio
    async def test_output_writing_style_linking(
        self, client, test_users, test_writing_style
    ):
        """Test linking output to writing style and analytics"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create output with writing style
        create_data = {
            "output_type": "grant_proposal",
            "title": "Grant with Style",
            "content": "Content using the writing style...",
            "word_count": 2500,
            "status": "awarded",
            "writing_style_id": str(test_writing_style.writing_style_id),
            "requested_amount": 200000.00,
            "awarded_amount": 200000.00,
        }
        response = client.post("/api/outputs", json=create_data, headers=writer_auth)
        assert response.status_code == 200

        output = response.json()
        assert output["writing_style_id"] == str(test_writing_style.writing_style_id)

        # Verify analytics by style include this output
        response = client.get(
            f"/api/outputs/analytics/style/{test_writing_style.writing_style_id}",
            headers=writer_auth
        )
        assert response.status_code == 200
        analytics = response.json()
        assert analytics["total_count"] >= 1
        assert analytics["awarded_count"] >= 1


# ==================== Analytics Aggregation Tests ====================

class TestAnalyticsAggregation:
    """Test analytics aggregation across outputs"""

    @pytest.mark.asyncio
    async def test_e2e_analytics_summary(
        self, client, test_users, db_session
    ):
        """Test dashboard summary endpoint with diverse data"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create diverse output data
        # Different funders with varying success rates
        funders = [
            ("NSF", 3, 2),  # 2 awarded out of 3
            ("NIH", 2, 2),  # 2 awarded out of 2 (100%)
            ("DOE", 4, 1),  # 1 awarded out of 4 (25%)
        ]

        for funder_name, total, awarded in funders:
            for i in range(total):
                is_awarded = i < awarded
                create_data = {
                    "output_type": "grant_proposal",
                    "title": f"{funder_name} Grant {i+1}",
                    "content": "Content...",
                    "word_count": 2000,
                    "status": "awarded" if is_awarded else "not_awarded",
                    "funder_name": funder_name,
                    "requested_amount": 100000.00,
                    "awarded_amount": 100000.00 if is_awarded else None,
                    "submission_date": "2024-01-01",
                    "decision_date": "2024-03-01",
                }
                client.post("/api/outputs", json=create_data, headers=writer_auth)

        # Get analytics summary
        response = client.get("/api/outputs/analytics/summary", headers=writer_auth)
        assert response.status_code == 200
        summary = response.json()

        # Verify summary includes overall metrics
        assert summary["total_outputs"] == 9
        assert summary["total_awarded"] == 5
        assert summary["success_rate"] == pytest.approx(55.56, rel=0.1)  # 5/9

    @pytest.mark.asyncio
    async def test_e2e_funder_performance(
        self, client, test_users, test_writing_style
    ):
        """Test funder performance rankings"""
        writer_auth = get_auth_header(
            client,
            test_users["writer"]["user"].email,
            test_users["writer"]["password"]
        )

        # Create outputs for multiple funders with different success rates
        funders_data = [
            ("NASA", 5, 4),   # 80% success rate
            ("NSF", 3, 2),    # 66.67% success rate
            ("NIH", 4, 1),    # 25% success rate
        ]

        for funder_name, total, awarded in funders_data:
            for i in range(total):
                is_awarded = i < awarded
                create_data = {
                    "output_type": "grant_proposal",
                    "title": f"{funder_name} Proposal {i+1}",
                    "content": "Content...",
                    "word_count": 2000,
                    "status": "awarded" if is_awarded else "not_awarded",
                    "funder_name": funder_name,
                    "requested_amount": 150000.00,
                    "awarded_amount": 150000.00 if is_awarded else None,
                }
                client.post("/api/outputs", json=create_data, headers=writer_auth)

        # Get funder performance rankings
        response = client.get("/api/outputs/analytics/funders", headers=writer_auth)
        assert response.status_code == 200
        funders = response.json()["funders"]

        # Verify rankings are ordered by success rate (descending)
        assert len(funders) == 3
        assert funders[0]["funder_name"] == "NASA"
        assert funders[0]["success_rate"] == 80.0
        assert funders[1]["funder_name"] == "NSF"
        assert funders[1]["success_rate"] == pytest.approx(66.67, rel=0.1)
        assert funders[2]["funder_name"] == "NIH"
        assert funders[2]["success_rate"] == 25.0
