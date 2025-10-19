"""
Pytest configuration and fixtures for integration tests.
"""
import pytest
from fastapi.testclient import TestClient
from typing import List

from app.main import app
from app.services.retrieval_engine import RetrievalResult
from app.dependencies import get_engine


class MockRetrievalEngine:
    """
    Mock RetrievalEngine for testing API endpoints
    """

    def __init__(self):
        self.retrieve_called = False
        self.last_query = None
        self.last_top_k = None
        self.last_filters = None

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters=None,
        recency_weight: float = None
    ) -> List[RetrievalResult]:
        """
        Mock retrieve method that returns fake results
        """
        self.retrieve_called = True
        self.last_query = query
        self.last_top_k = top_k
        self.last_filters = filters

        # Return mock results
        return [
            RetrievalResult(
                chunk_id="chunk_1",
                text="This is a sample text from a successful grant proposal about STEM education programs. Our organization has demonstrated significant impact through measurable outcomes.",
                score=0.92,
                metadata={
                    "doc_id": "doc_001",
                    "filename": "successful_proposal_2023.pdf",
                    "doc_type": "Grant Proposal",
                    "year": 2023,
                    "program": "Education"
                },
                doc_id="doc_001",
                chunk_index=0
            ),
            RetrievalResult(
                chunk_id="chunk_2",
                text="Our annual report shows the impact of youth development programs, including improved academic performance and increased engagement in STEM activities.",
                score=0.87,
                metadata={
                    "doc_id": "doc_002",
                    "filename": "annual_report_2022.pdf",
                    "doc_type": "Annual Report",
                    "year": 2022,
                    "program": "Youth Development"
                },
                doc_id="doc_002",
                chunk_index=5
            ),
            RetrievalResult(
                chunk_id="chunk_3",
                text="Evaluation data demonstrates that participants showed a 35% improvement in STEM knowledge and 40% increase in confidence.",
                score=0.85,
                metadata={
                    "doc_id": "doc_003",
                    "filename": "evaluation_report_2023.pdf",
                    "doc_type": "Evaluation Report",
                    "year": 2023,
                    "program": "STEM Education"
                },
                doc_id="doc_003",
                chunk_index=2
            )
        ]

    async def build_bm25_index(self):
        """Mock BM25 index building"""
        pass


@pytest.fixture
def mock_engine():
    """
    Create mock retrieval engine for testing

    Returns:
        MockRetrievalEngine: Mock engine instance
    """
    return MockRetrievalEngine()


@pytest.fixture
def client(mock_engine):
    """
    Create a test client for the FastAPI application with mocked dependencies.

    Args:
        mock_engine: Mock retrieval engine

    Returns:
        TestClient: FastAPI test client for making HTTP requests
    """
    # Override the dependency
    app.dependency_overrides[get_engine] = lambda: mock_engine

    client = TestClient(app)

    yield client

    # Clean up - remove the override
    app.dependency_overrides.clear()


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
        dict: Sample query request matching QueryRequest model
    """
    return {
        "query": "How do we demonstrate impact in STEM education programs?",
        "audience": "Federal RFP",
        "section": "Impact & Outcomes",
        "tone": "Professional",
        "max_sources": 5,
        "recency_weight": 0.7,
        "include_citations": True,
        "filters": {
            "doc_types": ["Grant Proposal"],
            "date_range": (2020, 2024)
        },
        "temperature": 0.3,
        "max_tokens": 4096
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
