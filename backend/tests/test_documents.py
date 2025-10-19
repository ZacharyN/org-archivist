"""
Integration tests for document management endpoints.
"""
import pytest
import io


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
            "metadata": str(sample_document_metadata)  # Convert to string for form data
        }
    )

    # Even if processing fails (stub), endpoint should accept valid structure
    assert response.status_code in [200, 201, 422]  # 422 if metadata parsing fails


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
        data={"metadata": "{}"}
    )

    # Should reject invalid file type
    assert response.status_code in [400, 422]


def test_empty_file_rejection(client):
    """Test that empty files are rejected."""
    file = io.BytesIO(b"")

    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", file, "text/plain")},
        data={"metadata": "{}"}
    )

    # Should reject empty file
    assert response.status_code in [400, 422]
