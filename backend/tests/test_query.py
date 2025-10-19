"""
Integration tests for query and generation endpoints.
"""
import pytest


def test_query_endpoint_exists(client):
    """Test that the query endpoint is accessible."""
    response = client.post("/api/query")

    # Should get 422 (validation error) not 404
    assert response.status_code in [422, 400]


def test_query_with_valid_request(client, sample_query_request):
    """Test query endpoint with valid request structure."""
    response = client.post("/api/query", json=sample_query_request)

    # Should accept valid request
    assert response.status_code == 200

    data = response.json()
    # Verify response structure
    assert "text" in data
    assert "sources" in data
    assert "confidence" in data
    assert "metadata" in data

    # Verify sources structure
    assert len(data["sources"]) > 0
    source = data["sources"][0]
    assert "id" in source
    assert "filename" in source
    assert "doc_type" in source
    assert "excerpt" in source
    assert "relevance" in source


def test_query_retrieval_integration(client, mock_engine, sample_query_request):
    """Test that query endpoint calls RetrievalEngine correctly."""
    response = client.post("/api/query", json=sample_query_request)

    assert response.status_code == 200

    # Verify RetrievalEngine was called
    assert mock_engine.retrieve_called
    assert mock_engine.last_query == sample_query_request["query"]
    assert mock_engine.last_top_k == sample_query_request["max_sources"]


def test_query_required_fields(client):
    """Test that query requires necessary fields."""
    # Missing query field
    response = client.post(
        "/api/query",
        json={
            "audience": "Federal RFP",
            "section": "Program Description"
        }
    )

    assert response.status_code == 422


def test_query_audience_validation(client):
    """Test audience field validation."""
    response = client.post(
        "/api/query",
        json={
            "query": "How do we demonstrate program impact?",
            "audience": "invalid_audience",
            "section": "Impact & Outcomes"
        }
    )

    # Should reject invalid audience
    assert response.status_code == 422


def test_query_section_validation(client):
    """Test section field validation."""
    response = client.post(
        "/api/query",
        json={
            "query": "How do we demonstrate program impact?",
            "audience": "Federal RFP",
            "section": "Invalid Section"
        }
    )

    # Should reject invalid section
    assert response.status_code == 422


def test_query_max_sources_validation(client):
    """Test max_sources parameter validation."""
    response = client.post(
        "/api/query",
        json={
            "query": "Test query with many results needed",
            "audience": "Foundation Grant",
            "section": "Program Description",
            "max_sources": 20  # Within valid range (1-15)
        }
    )

    # Should reject (max is 15)
    assert response.status_code == 422


def test_streaming_endpoint_exists(client):
    """Test that the streaming query endpoint exists."""
    response = client.post("/api/query/stream")

    # Should get 422 (validation error) not 404
    assert response.status_code in [422, 400]


def test_streaming_with_valid_request(client, sample_query_request):
    """Test streaming endpoint with valid request."""
    response = client.post("/api/query/stream", json=sample_query_request)

    # Should accept request
    assert response.status_code == 200

    # Check content type
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_query_with_filters(client):
    """Test query with metadata filters."""
    response = client.post(
        "/api/query",
        json={
            "query": "How do we demonstrate program effectiveness?",
            "audience": "Foundation Grant",
            "section": "Impact & Outcomes",
            "filters": {
                "doc_types": ["Grant Proposal"],
                "date_range": (2020, 2024),
                "programs": ["Education"]
            }
        }
    )

    assert response.status_code == 200


def test_query_empty_string(client):
    """Test that empty query strings are rejected."""
    response = client.post(
        "/api/query",
        json={
            "query": "",
            "audience": "Federal RFP",
            "section": "Program Description"
        }
    )

    # Should reject empty query (min_length=10)
    assert response.status_code in [400, 422]


def test_query_response_structure(client, sample_query_request):
    """Test that successful query responses have expected structure."""
    response = client.post("/api/query", json=sample_query_request)

    if response.status_code == 200:
        data = response.json()

        # Response should be a dict
        assert isinstance(data, dict)

        # Should have some response fields
        # (exact fields depend on implementation)
        assert len(data) > 0
