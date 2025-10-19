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

    # Should accept valid request (may return stub data)
    assert response.status_code in [200, 201]

    if response.status_code == 200:
        data = response.json()
        assert "query" in data or "response" in data or "sources" in data


def test_query_required_fields(client):
    """Test that query requires necessary fields."""
    # Missing query field
    response = client.post("/api/query", json={"audience": "federal_agency"})

    assert response.status_code == 422


def test_query_audience_validation(client):
    """Test audience field validation."""
    response = client.post(
        "/api/query",
        json={
            "query": "Test query",
            "audience": "federal_agency",
            "max_results": 5
        }
    )

    # Should accept valid audience
    assert response.status_code in [200, 201]


def test_query_max_results_validation(client):
    """Test max_results parameter validation."""
    response = client.post(
        "/api/query",
        json={
            "query": "Test query",
            "audience": "federal_agency",
            "max_results": 100  # Very large number
        }
    )

    # Should handle or validate max_results
    assert response.status_code in [200, 201, 422]


def test_streaming_endpoint_exists(client):
    """Test that the streaming query endpoint exists."""
    response = client.post("/api/query/stream")

    # Should get 422 (validation error) not 404
    assert response.status_code in [422, 400]


def test_streaming_with_valid_request(client, sample_query_request):
    """Test streaming endpoint with valid request."""
    response = client.post("/api/query/stream", json=sample_query_request)

    # Should accept request
    # Streaming responses have status 200 even if they stream errors
    assert response.status_code in [200, 201]


def test_query_with_filters(client):
    """Test query with metadata filters."""
    response = client.post(
        "/api/query",
        json={
            "query": "Test query",
            "audience": "foundation",
            "filters": {
                "doc_type": ["successful_proposal"],
                "year_range": [2020, 2024],
                "program": ["Education"]
            }
        }
    )

    assert response.status_code in [200, 201]


def test_query_empty_string(client):
    """Test that empty query strings are rejected."""
    response = client.post(
        "/api/query",
        json={
            "query": "",
            "audience": "federal_agency"
        }
    )

    # Should reject empty query
    assert response.status_code == 422


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
