"""
Pytest configuration and fixtures for integration tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.

    Returns:
        TestClient: FastAPI test client for making HTTP requests
    """
    return TestClient(app)


@pytest.fixture
def sample_document_metadata():
    """
    Sample document metadata for testing.

    Returns:
        dict: Sample document metadata
    """
    return {
        "doc_type": "successful_proposal",
        "year": 2023,
        "program": ["Education", "Youth Development"],
        "outcome": "funded",
        "grant_amount": 50000.0,
        "tags": ["STEM", "After School"],
        "organization": "Test Foundation"
    }


@pytest.fixture
def sample_query_request():
    """
    Sample query request for testing.

    Returns:
        dict: Sample query request
    """
    return {
        "query": "How do we demonstrate impact in STEM education programs?",
        "audience": "federal_agency",
        "max_results": 5,
        "filters": {
            "doc_type": ["successful_proposal"],
            "year_range": [2020, 2024]
        }
    }


@pytest.fixture
def sample_chat_request():
    """
    Sample chat request for testing.

    Returns:
        dict: Sample chat request
    """
    return {
        "message": "What are best practices for writing a needs statement?",
        "conversation_id": None,
        "context_window": 10
    }


@pytest.fixture
def sample_prompt_template():
    """
    Sample prompt template for testing.

    Returns:
        dict: Sample prompt template
    """
    return {
        "name": "Test Template",
        "category": "custom",
        "content": "This is a test prompt for {audience} with {topic}.",
        "variables": ["audience", "topic"],
        "active": True
    }


@pytest.fixture
def sample_config_update():
    """
    Sample configuration update for testing.

    Returns:
        dict: Sample configuration update
    """
    return {
        "llm": {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.5,
            "max_tokens": 2048
        }
    }
