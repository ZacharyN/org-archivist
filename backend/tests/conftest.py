"""
Pytest configuration and fixtures for integration tests.

Provides shared fixtures for:
- PostgreSQL test database (mirrors production)
- FastAPI test client
- Mock retrieval engine
- Test users with different roles
"""
import os
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from uuid import uuid4

# Set DATABASE_URL for auth module BEFORE importing app modules
# This prevents the auth module from creating an engine with the wrong driver
# Note: Use postgres-test:5432 for Docker test environment (org-archivist-network)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Set individual PostgreSQL environment variables for DatabaseService
# DatabaseService constructs its connection URL from these individual settings
os.environ["POSTGRES_HOST"] = os.getenv("POSTGRES_HOST", "postgres-test")
os.environ["POSTGRES_PORT"] = os.getenv("POSTGRES_PORT", "5432")
os.environ["POSTGRES_USER"] = os.getenv("POSTGRES_USER", "test_user")
os.environ["POSTGRES_PASSWORD"] = os.getenv("POSTGRES_PASSWORD", "test_password")
os.environ["POSTGRES_DB"] = os.getenv("POSTGRES_DB", "org_archivist_test")

from app.main import app
from app.services.retrieval_engine import RetrievalResult
from app.dependencies import get_engine
from app.db.models import Base, User, UserRole, WritingStyle
from app.db.session import get_db
from app.services.auth_service import AuthService


# =============================================================================
# Database Fixtures (PostgreSQL)
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """
    Create a test database engine connected to PostgreSQL test database.

    Creates all tables at fixture start and drops them at teardown.
    Uses NullPool to ensure connections are closed properly after each test.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )

    # Create all tables before test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up - drop all tables and data after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """
    Create a test database session that commits data directly to database.

    Data persists during test execution so that TestClient (which creates
    separate connections) can see committed test data for authentication.
    Tables are dropped after each test by db_engine fixture for isolation.
    """
    # Create session factory
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create session that commits directly to database
    async with async_session() as session:
        yield session
        # No rollback - data persists and is cleaned up by dropping tables


# =============================================================================
# Mock Retrieval Engine (for RAG tests)
# =============================================================================

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


# =============================================================================
# FastAPI Test Client
# =============================================================================

# Mock lifespan context manager for tests (prevents DB connection during test init)
@asynccontextmanager
async def mock_lifespan(app):
    """Mock lifespan that does nothing (no DB connection)"""
    yield


@pytest.fixture
def client(mock_engine, db_session):
    """
    Create a test client for the FastAPI application with mocked dependencies.

    Args:
        mock_engine: Mock retrieval engine
        db_session: Test database session

    Returns:
        TestClient: FastAPI test client for making HTTP requests
    """
    # Import auth module's get_db to override it
    from app.api.auth import get_db as auth_get_db
    from app.dependencies import get_database
    from app.services.database import DatabaseService

    # Override the dependencies
    app.dependency_overrides[get_engine] = lambda: mock_engine

    # Override auth module's get_db with test database session
    async def override_auth_get_db():
        yield db_session

    app.dependency_overrides[auth_get_db] = override_auth_get_db
    app.dependency_overrides[get_db] = override_auth_get_db

    # Override get_database to return a properly configured DatabaseService
    # that uses the test database URL
    async def override_get_database() -> DatabaseService:
        """Provides DatabaseService connected to test database"""
        db = DatabaseService()
        # The DatabaseService will use the TEST_DATABASE_URL from environment
        # which was set at line 26 above
        if not db.pool:
            await db.connect()
        return db

    app.dependency_overrides[get_database] = override_get_database

    # Mock lifespan to prevent DB connection during test client init
    app.router.lifespan_context = mock_lifespan

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
