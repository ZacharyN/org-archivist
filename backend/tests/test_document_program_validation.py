"""
Test dynamic program validation in document upload endpoint

Tests the requirement that document uploads validate program names
against the database instead of using hardcoded values.
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID
import json
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.db.models import User, UserRole
from app.services.database import DatabaseService


@pytest.fixture
def sample_pdf_file():
    """
    Generate a sample PDF file for testing

    Returns:
        bytes: PDF file content
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Sample Document for Testing")
    c.drawString(100, 730, "This is a test document with minimal content.")
    c.showPage()
    c.save()
    return buffer.getvalue()


@pytest_asyncio.fixture
async def test_db():
    """DatabaseService instance for testing"""
    db = DatabaseService()
    await db.connect()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def editor_user(db_session):
    """Create an editor user for testing"""
    from app.services.auth_service import AuthService

    auth_service = AuthService()
    user = User(
        user_id=uuid4(),
        email=f"editor_{uuid4().hex[:8]}@test.com",
        role=UserRole.EDITOR,
        hashed_password=auth_service.hash_password("testpass123")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestDocumentProgramValidation:
    """Test dynamic program validation for document uploads"""

    async def test_upload_with_valid_program(
        self,
        client: AsyncClient,
        sample_pdf_file,
        test_db
    ):
        """Upload document with valid program should succeed"""
        # Ensure we have an active program
        programs = await test_db.list_programs(active_only=True)
        assert len(programs) > 0, "Need at least one active program for testing"

        valid_program = programs[0]['name']

        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": [valid_program],
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "doc_id" in data

    async def test_upload_with_invalid_program(
        self,
        client: AsyncClient,
        sample_pdf_file
    ):
        """Upload document with invalid program should fail with helpful error"""
        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": ["NonexistentProgram"],
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert "error" in detail
        assert detail["error"] == "Invalid programs"
        assert "invalid_programs" in detail
        assert "NonexistentProgram" in detail["invalid_programs"]
        assert "valid_programs" in detail
        assert "action" in detail

    async def test_upload_with_mixed_valid_invalid_programs(
        self,
        client: AsyncClient,
        sample_pdf_file,
        test_db
    ):
        """Upload document with mixed valid/invalid programs should fail"""
        # Get a valid program
        programs = await test_db.list_programs(active_only=True)
        valid_program = programs[0]['name']

        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": [valid_program, "InvalidProgram"],
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        assert response.status_code == 400
        data = response.json()
        detail = data["detail"]
        assert "InvalidProgram" in detail["invalid_programs"]

    async def test_upload_with_case_variation(
        self,
        client: AsyncClient,
        sample_pdf_file,
        test_db
    ):
        """Upload document with case variation should normalize program name"""
        # Get a valid program and convert to different case
        programs = await test_db.list_programs(active_only=True)
        assert len(programs) > 0

        canonical_name = programs[0]['name']
        # Test with lowercase version
        lowercase_name = canonical_name.lower()

        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": [lowercase_name],
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        # Should succeed and normalize the program name
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

        # Verify the document was saved with normalized program name
        doc_id = data["doc_id"]
        doc = await test_db.get_document(doc_id)
        assert canonical_name in doc["programs"]

    async def test_upload_with_newly_created_program(
        self,
        client: AsyncClient,
        sample_pdf_file,
        test_db,
        editor_user
    ):
        """Upload document with newly created custom program should succeed"""
        # Create a new program
        new_program_name = f"Test Program {uuid4().hex[:8]}"
        created = await test_db.create_program(
            name=new_program_name,
            description="Test program for validation",
            display_order=999,
            active=True,
            created_by=editor_user.user_id
        )

        # Upload document with this new program
        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": [new_program_name],
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

        # Cleanup
        await test_db.delete_program(created['program_id'], force=True)

    async def test_upload_with_inactive_program(
        self,
        client: AsyncClient,
        sample_pdf_file,
        test_db,
        editor_user
    ):
        """Upload document with inactive program should fail"""
        # Create a new inactive program
        inactive_program_name = f"Inactive Program {uuid4().hex[:8]}"
        created = await test_db.create_program(
            name=inactive_program_name,
            description="Inactive test program",
            display_order=999,
            active=False,  # Inactive!
            created_by=editor_user.user_id
        )

        # Try to upload document with inactive program
        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": [inactive_program_name],
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        # Should fail because program is not active
        assert response.status_code == 400
        data = response.json()
        detail = data["detail"]
        assert inactive_program_name in detail["invalid_programs"]

        # Cleanup
        await test_db.delete_program(created['program_id'], force=True)

    async def test_get_active_program_names_endpoint(
        self,
        client: AsyncClient,
        test_db,
        db_session
    ):
        """Test GET /api/programs/active endpoint requires authentication"""
        # Test unauthenticated request should fail
        response_unauth = await client.get("/api/programs/active")
        assert response_unauth.status_code == 401

        # Create and login a test user
        from app.services.auth_service import AuthService
        test_user = User(
            user_id=uuid4(),
            email=f"test_writer_{uuid4().hex[:8]}@test.com",
            role=UserRole.WRITER,
            hashed_password=AuthService.hash_password("testpass123"),
            is_active=True
        )
        db_session.add(test_user)
        await db_session.commit()
        await db_session.refresh(test_user)

        # Login to get token
        login_response = await client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "testpass123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test authenticated request should succeed
        response = await client.get(
            "/api/programs/active",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        program_names = response.json()

        # Should return a list of strings
        assert isinstance(program_names, list)
        assert len(program_names) > 0

        # All items should be strings
        for name in program_names:
            assert isinstance(name, str)

        # Should be sorted alphabetically
        assert program_names == sorted(program_names)

        # Verify against database
        db_programs = await test_db.list_programs(active_only=True)
        expected_names = sorted([p['name'] for p in db_programs])
        assert program_names == expected_names

    async def test_upload_with_empty_programs_list(
        self,
        client: AsyncClient,
        sample_pdf_file
    ):
        """Upload document with empty programs list should succeed"""
        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": [],  # Empty list
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    async def test_upload_with_multiple_valid_programs(
        self,
        client: AsyncClient,
        sample_pdf_file,
        test_db
    ):
        """Upload document with multiple valid programs should succeed"""
        # Get at least 2 active programs
        programs = await test_db.list_programs(active_only=True)
        assert len(programs) >= 2, "Need at least 2 active programs for this test"

        program_names = [programs[0]['name'], programs[1]['name']]

        metadata = {
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": program_names,
            "tags": ["test"],
            "outcome": "N/A"
        }

        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
            data={
                "metadata": json.dumps(metadata),
                "sensitivity_confirmed": "true"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

        # Verify both programs were saved
        doc_id = data["doc_id"]
        doc = await test_db.get_document(doc_id)
        for program_name in program_names:
            assert program_name in doc["programs"]
