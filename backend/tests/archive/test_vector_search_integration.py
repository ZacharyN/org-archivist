"""
Test script for vector search integration

Tests:
- Building Qdrant filters from DocumentFilters
- Vector search with no filters
- Vector search with various filter combinations
- Filter edge cases
"""
import sys
import os
from pathlib import Path

# Set dummy env vars
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'

sys.path.insert(0, str(Path(__file__).parent))

from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig
from app.models.document import DocumentFilters
from qdrant_client.models import Filter


class MockEmbedding:
    """Mock embedding model"""
    def get_text_embedding(self, text):
        return [0.1] * 1536


class MockVectorStore:
    """Mock vector store that returns test results"""

    def __init__(self):
        self.collection_name = "test_collection"
        self.client = MockQdrantClient()

    async def search_similar(self, *args, **kwargs):
        """Return mock search results"""
        return [
            {
                "id": "chunk1",
                "score": 0.95,
                "text": "Sample chunk text 1",
                "metadata": {"doc_id": "doc1", "chunk_index": 0, "year": 2023}
            },
            {
                "id": "chunk2",
                "score": 0.87,
                "text": "Sample chunk text 2",
                "metadata": {"doc_id": "doc2", "chunk_index": 1, "year": 2022}
            }
        ]


class MockQdrantClient:
    """Mock Qdrant client for filtered search"""

    def search(self, *args, **kwargs):
        """Return mock scored points"""
        class MockScoredPoint:
            def __init__(self, id, score, text, metadata):
                self.id = id
                self.score = score
                self.payload = {"text": text, **metadata}

        return [
            MockScoredPoint("chunk1", 0.95, "Filtered chunk 1",
                          {"doc_id": "doc1", "year": 2023, "doc_type": "Grant Proposal"}),
            MockScoredPoint("chunk2", 0.87, "Filtered chunk 2",
                          {"doc_id": "doc2", "year": 2024, "outcome": "Funded"})
        ]


def test_filter_builder():
    """Test building Qdrant filters from DocumentFilters"""
    print("\n[TEST] Building Qdrant Filters")

    engine = RetrievalEngine(MockVectorStore(), MockEmbedding())

    # Test 1: Empty filters
    filters = DocumentFilters()
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is None
    print("[OK] Empty filters return None")

    # Test 2: Document type filter
    filters = DocumentFilters(doc_types=["Grant Proposal", "Annual Report"])
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    assert isinstance(qdrant_filter, Filter)
    assert len(qdrant_filter.must) >= 1
    print("[OK] Document type filter created")

    # Test 3: Year filter
    filters = DocumentFilters(years=[2022, 2023, 2024])
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    print("[OK] Year filter created")

    # Test 4: Date range filter
    filters = DocumentFilters(date_range=(2020, 2024))
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    print("[OK] Date range filter created")

    # Test 5: Program filter
    filters = DocumentFilters(programs=["Early Childhood", "Youth Development"])
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    print("[OK] Program filter created")

    # Test 6: Outcome filter
    filters = DocumentFilters(outcomes=["Funded", "Pending"])
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    print("[OK] Outcome filter created")

    # Test 7: Exclude documents
    filters = DocumentFilters(exclude_docs=["doc1", "doc2", "doc3"])
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    assert hasattr(qdrant_filter, 'must_not')
    print("[OK] Exclude filter created")

    # Test 8: Combined filters
    filters = DocumentFilters(
        doc_types=["Grant Proposal"],
        years=[2023, 2024],
        programs=["Early Childhood"],
        outcomes=["Funded"],
        exclude_docs=["old_doc"]
    )
    qdrant_filter = engine._build_qdrant_filter(filters)
    assert qdrant_filter is not None
    assert len(qdrant_filter.must) >= 2  # Multiple conditions
    print("[OK] Combined filters created")


async def test_vector_search_no_filter():
    """Test vector search without filters"""
    print("\n[TEST] Vector Search Without Filters")

    engine = RetrievalEngine(MockVectorStore(), MockEmbedding())

    query_embedding = [0.1] * 1536
    results = await engine._vector_search(
        query_embedding=query_embedding,
        top_k=5,
        filters=None
    )

    assert isinstance(results, list)
    assert len(results) == 2  # Mock returns 2 results
    assert results[0].score == 0.95
    assert results[0].text == "Sample chunk text 1"
    assert results[0].metadata["year"] == 2023

    print(f"[OK] Retrieved {len(results)} results without filters")
    print(f"     Top result: score={results[0].score}, doc_id={results[0].doc_id}")


async def test_vector_search_with_filters():
    """Test vector search with metadata filters"""
    print("\n[TEST] Vector Search With Filters")

    engine = RetrievalEngine(MockVectorStore(), MockEmbedding())

    query_embedding = [0.1] * 1536

    # Test with doc_type filter
    filters = DocumentFilters(doc_types=["Grant Proposal"])
    results = await engine._vector_search(
        query_embedding=query_embedding,
        top_k=5,
        filters=filters
    )

    assert isinstance(results, list)
    assert len(results) >= 1
    print(f"[OK] Filtered by doc_type: {len(results)} results")

    # Test with year range filter
    filters = DocumentFilters(date_range=(2020, 2024))
    results = await engine._vector_search(
        query_embedding=query_embedding,
        top_k=5,
        filters=filters
    )

    assert isinstance(results, list)
    print(f"[OK] Filtered by date range: {len(results)} results")

    # Test with outcome filter
    filters = DocumentFilters(outcomes=["Funded"])
    results = await engine._vector_search(
        query_embedding=query_embedding,
        top_k=5,
        filters=filters
    )

    assert isinstance(results, list)
    print(f"[OK] Filtered by outcome: {len(results)} results")


async def test_end_to_end_retrieve():
    """Test full retrieve() pipeline with filters"""
    print("\n[TEST] End-to-End Retrieve with Filters")

    engine = RetrievalEngine(MockVectorStore(), MockEmbedding())

    query = "What are our early childhood program outcomes?"
    filters = DocumentFilters(
        programs=["Early Childhood"],
        years=[2023, 2024],
        outcomes=["Funded"]
    )

    results = await engine.retrieve(
        query=query,
        top_k=3,
        filters=filters
    )

    assert isinstance(results, list)
    # With mocks returning 2 results, and diversification, expect <= 2
    assert len(results) <= 2

    if results:
        print(f"[OK] End-to-end retrieve: {len(results)} results")
        print(f"     Query: '{query[:50]}...'")
        print(f"     Filters: programs={filters.programs}, years={filters.years}")
    else:
        print("[OK] End-to-end retrieve completed (no results from mock)")


def test_filter_edge_cases():
    """Test edge cases in filter building"""
    print("\n[TEST] Filter Edge Cases")

    engine = RetrievalEngine(MockVectorStore(), MockEmbedding())

    # None filters
    result = engine._build_qdrant_filter(None)
    assert result is None
    print("[OK] None filters handled")

    # Empty lists
    filters = DocumentFilters(doc_types=[], years=[], programs=[])
    result = engine._build_qdrant_filter(filters)
    assert result is None
    print("[OK] Empty list filters handled")

    # Single value lists
    filters = DocumentFilters(doc_types=["Grant Proposal"])
    result = engine._build_qdrant_filter(filters)
    assert result is not None
    print("[OK] Single value filters handled")

    # Date range edge case
    filters = DocumentFilters(date_range=(2024, 2024))  # Same year
    result = engine._build_qdrant_filter(filters)
    assert result is not None
    print("[OK] Same-year date range handled")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Vector Search Integration")
    print("=" * 60)

    # Synchronous tests
    test_filter_builder()
    test_filter_edge_cases()

    # Async tests
    import asyncio
    await test_vector_search_no_filter()
    await test_vector_search_with_filters()
    await test_end_to_end_retrieve()

    print("\n" + "=" * 60)
    print("All Vector Search Integration Tests Passed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
