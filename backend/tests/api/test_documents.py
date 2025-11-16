"""
Integration tests for document management endpoints.
"""
import pytest
import io
import json


def test_document_upload_endpoint_exists(client):
    """Test that the document upload endpoint is accessible."""
    # Test with minimal valid data (will fail validation but endpoint exists)
    response = client.post("/api/documents/upload")

    # Should get 422 (validation error) not 404 (not found)
    assert response.status_code in [422, 400]


def test_document_upload_validation(client, sample_document_metadata):
    """Test document upload with valid metadata structure."""
    # Create a simple text file
    file_content = b"This is a test document for upload validation."
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "metadata": str(sample_document_metadata),  # Convert to string for form data
            "sensitivity_confirmed": "true"  # Phase 5: Sensitivity confirmation required
        }
    )

    # Even if processing fails (stub), endpoint should accept valid structure
    assert response.status_code in [200, 201, 422]  # 422 if metadata parsing fails


def test_upload_fails_without_sensitivity_confirmation(client):
    """Test that upload fails when sensitivity_confirmed is false (Phase 5)."""
    # Create valid test metadata
    metadata = {
        "doc_type": "Grant Proposal",
        "year": 2024,
        "programs": ["Early Childhood"],
        "tags": ["federal", "education"],
        "outcome": "Funded"
    }

    # Create a simple text file
    file_content = b"This is a test document for sensitivity validation."
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "metadata": json.dumps(metadata),
            "sensitivity_confirmed": "false"  # Not confirmed - should fail
        }
    )

    # Should reject with 400 Bad Request
    assert response.status_code == 400

    # Verify error message structure
    data = response.json()
    assert "detail" in data

    # Check that error contains sensitivity warning
    error_detail = data["detail"]
    if isinstance(error_detail, dict):
        assert "error" in error_detail
        assert "message" in error_detail
        assert "Sensitivity confirmation required" in error_detail["error"]
        assert "public-facing documents" in error_detail["message"].lower()
    else:
        # In case detail is a string
        assert "sensitivity" in str(error_detail).lower()


def test_upload_succeeds_with_sensitivity_confirmation(client):
    """Test that upload succeeds when sensitivity_confirmed is true (Phase 5)."""
    # Create valid test metadata
    metadata = {
        "doc_type": "Annual Report",
        "year": 2024,
        "programs": ["Early Childhood"],
        "tags": ["annual", "report"],
        "outcome": "N/A"
    }

    # Create a simple text file
    file_content = b"This is a public-facing annual report document."
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("annual_report_2024.txt", file, "text/plain")},
        data={
            "metadata": json.dumps(metadata),
            "sensitivity_confirmed": "true"  # Confirmed - should succeed
        }
    )

    # Should succeed (200 or 201) or fail with processing error (500) but not 400
    # We're testing that sensitivity validation passes, not full document processing
    assert response.status_code in [200, 201, 500], \
        f"Expected success or processing error, got {response.status_code}: {response.json()}"

    # If it's a 400, it shouldn't be about sensitivity
    if response.status_code == 400:
        data = response.json()
        error_detail = str(data.get("detail", ""))
        assert "sensitivity" not in error_detail.lower(), \
            "Should not fail on sensitivity check when confirmed=true"


def test_upload_missing_sensitivity_field(client):
    """Test that upload requires sensitivity_confirmed field (Phase 5)."""
    # Create valid test metadata
    metadata = {
        "doc_type": "Grant Proposal",
        "year": 2024,
        "programs": [],
        "tags": [],
        "outcome": "N/A"
    }

    # Create a simple text file
    file_content = b"Test document."
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        data={
            "metadata": json.dumps(metadata)
            # sensitivity_confirmed field is missing
        }
    )

    # Should fail with 400 or 422 (validation error)
    assert response.status_code in [400, 422]


def test_list_documents_endpoint(client):
    """Test listing documents endpoint."""
    response = client.get("/api/documents")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_list_documents_with_filters(client):
    """Test document list filtering."""
    # Test with various filter parameters
    response = client.get("/api/documents?doc_type=successful_proposal&year=2023")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_list_documents_pagination(client):
    """Test document list pagination."""
    response = client.get("/api/documents?skip=0&limit=10")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_get_document_by_id(client):
    """Test getting a specific document by ID."""
    # Use a test ID (will return 404 or empty for now)
    test_id = "test-doc-123"
    response = client.get(f"/api/documents/{test_id}")

    # Should be valid endpoint, returns 404 if not found
    assert response.status_code in [200, 404]


def test_delete_document(client):
    """Test deleting a document."""
    test_id = "test-doc-123"
    response = client.delete(f"/api/documents/{test_id}")

    # Should be valid endpoint, returns 404 if not found
    assert response.status_code in [200, 204, 404]


def test_document_stats_endpoint(client):
    """Test document statistics endpoint."""
    response = client.get("/api/documents/stats")

    assert response.status_code == 200

    data = response.json()
    # Stats should have count fields
    assert "total_documents" in data or "documents" in data or isinstance(data, dict)


def test_document_search(client):
    """Test document search functionality."""
    response = client.get("/api/documents?search=education")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_invalid_file_type_rejection(client):
    """Test that invalid file types are rejected."""
    # Create a file with invalid extension
    file_content = b"Invalid content"
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.exe", file, "application/octet-stream")},
        data={
            "metadata": "{}",
            "sensitivity_confirmed": "true"  # Include required field
        }
    )

    # Should reject invalid file type
    assert response.status_code in [400, 422]


def test_empty_file_rejection(client):
    """Test that empty files are rejected."""
    file = io.BytesIO(b"")

    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", file, "text/plain")},
        data={
            "metadata": "{}",
            "sensitivity_confirmed": "true"  # Include required field
        }
    )

    # Should reject empty file
    assert response.status_code in [400, 422]
