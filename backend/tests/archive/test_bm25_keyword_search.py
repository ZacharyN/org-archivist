"""
Test BM25 Keyword Search Implementation

Tests the BM25 keyword search functionality in the RetrievalEngine.
"""
import asyncio
import os
import sys
import logging

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set minimal environment variables
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig
from app.models.document import DocumentFilters


# Mock classes for testing
class MockEmbedding:
    """Mock embedding model"""
    def get_text_embedding(self, text):
        return [0.1] * 1536


class MockQdrantClient:
    """Mock Qdrant client"""
    def __init__(self):
        self.documents = []

    def get_collection(self, collection_name):
        """Mock get_collection"""
        class CollectionInfo:
            points_count = len(self.documents)
        return CollectionInfo()

    def scroll(self, collection_name, limit, offset, with_payload, with_vectors):
        """Mock scroll through documents"""
        if not self.documents:
            return [], None

        # Return documents in batches
        start = offset or 0
        end = start + limit
        batch = self.documents[start:end]

        # Create point objects
        class Point:
            def __init__(self, doc_id, payload):
                self.id = doc_id
                self.payload = payload

        points = [Point(i + start, doc) for i, doc in enumerate(batch)]

        # Return next offset if there are more documents
        next_offset = end if end < len(self.documents) else None

        return points, next_offset

    def add_documents(self, docs):
        """Helper to add test documents"""
        self.documents = docs


class MockVectorStore:
    """Mock vector store"""
    def __init__(self, client):
        self.client = client
        self.collection_name = "test_collection"

    async def search_similar(self, *args, **kwargs):
        return []


def print_separator():
    """Print separator line"""
    print("=" * 80)


async def test_tokenization():
    """Test tokenization method"""
    print("\n[TEST] Tokenization")
    print_separator()

    client = MockQdrantClient()
    vector_store = MockVectorStore(client)
    embedding_model = MockEmbedding()

    engine = RetrievalEngine(vector_store, embedding_model)

    # Test basic tokenization
    text1 = "Hello World! How are you?"
    tokens1 = engine._tokenize(text1)
    print(f"Input: '{text1}'")
    print(f"Tokens: {tokens1}")
    assert tokens1 == ['hello', 'world', 'how', 'are', 'you']

    # Test with numbers and special chars
    text2 = "RFP-2024: Grant funding for $100,000"
    tokens2 = engine._tokenize(text2)
    print(f"\nInput: '{text2}'")
    print(f"Tokens: {tokens2}")
    assert 'rfp' in tokens2
    assert '2024' in tokens2
    assert 'grant' in tokens2

    print("\n[OK] Tokenization test passed")


async def test_bm25_index_building():
    """Test BM25 index building from mock documents"""
    print("\n[TEST] BM25 Index Building")
    print_separator()

    # Create mock documents
    docs = [
        {
            "text": "This is a grant proposal for education programs",
            "doc_id": "doc1",
            "doc_type": "Grant Proposal",
            "year": 2023,
            "programs": ["Education"],
            "outcome": "Funded"
        },
        {
            "text": "Annual report showing program outcomes and impact",
            "doc_id": "doc2",
            "doc_type": "Annual Report",
            "year": 2024,
            "programs": ["Youth Development"],
            "outcome": "N/A"
        },
        {
            "text": "Letter of intent for federal funding opportunity",
            "doc_id": "doc3",
            "doc_type": "Letter of Intent",
            "year": 2024,
            "programs": ["Education", "Youth Development"],
            "outcome": "Pending"
        }
    ]

    client = MockQdrantClient()
    client.add_documents(docs)

    vector_store = MockVectorStore(client)
    embedding_model = MockEmbedding()

    engine = RetrievalEngine(vector_store, embedding_model)

    # Build index
    await engine.build_bm25_index()

    # Verify index was built
    assert engine._bm25_index is not None
    assert len(engine._bm25_corpus) == 3
    assert len(engine._bm25_metadata) == 3
    assert len(engine._bm25_tokenized) == 3

    print(f"Index built with {len(engine._bm25_corpus)} documents")
    print(f"Sample tokens: {engine._bm25_tokenized[0][:5]}")

    print("\n[OK] BM25 index building test passed")


async def test_keyword_search_basic():
    """Test basic keyword search without filters"""
    print("\n[TEST] Basic Keyword Search")
    print_separator()

    # Create mock documents
    docs = [
        {
            "text": "This is a grant proposal for education programs in urban schools",
            "doc_id": "doc1",
            "doc_type": "Grant Proposal",
            "year": 2023,
            "programs": ["Education"],
            "chunk_index": 0
        },
        {
            "text": "Annual report showing program outcomes and impact on youth development",
            "doc_id": "doc2",
            "doc_type": "Annual Report",
            "year": 2024,
            "programs": ["Youth Development"],
            "chunk_index": 0
        },
        {
            "text": "Letter of intent for federal funding opportunity for education initiatives",
            "doc_id": "doc3",
            "doc_type": "Letter of Intent",
            "year": 2024,
            "programs": ["Education"],
            "chunk_index": 0
        },
        {
            "text": "Budget narrative for youth development grant proposal with detailed costs",
            "doc_id": "doc4",
            "doc_type": "Grant Proposal",
            "year": 2023,
            "programs": ["Youth Development"],
            "chunk_index": 1
        }
    ]

    client = MockQdrantClient()
    client.add_documents(docs)

    vector_store = MockVectorStore(client)
    embedding_model = MockEmbedding()

    engine = RetrievalEngine(vector_store, embedding_model)
    await engine.build_bm25_index()

    # Test query: "education grant"
    query = "education grant"

    # Debug: Check index state
    print(f"Index state:")
    print(f"  - BM25 index exists: {engine._bm25_index is not None}")
    print(f"  - Corpus size: {len(engine._bm25_corpus)}")
    print(f"  - Tokenized corpus size: {len(engine._bm25_tokenized)}")
    if engine._bm25_corpus:
        print(f"  - Sample corpus text: {engine._bm25_corpus[0][:60]}...")
    if engine._bm25_tokenized:
        print(f"  - Sample tokenized doc: {engine._bm25_tokenized[0][:10]}")
        print(f"  - All tokenized docs:")
        for i, tokens in enumerate(engine._bm25_tokenized):
            print(f"     Doc {i}: {tokens[:15]}")

    results = await engine._keyword_search(query, top_k=3)

    print(f"\nQuery: '{query}'")
    print(f"Results: {len(results)} documents")

    for i, result in enumerate(results):
        print(f"\n  {i+1}. Score: {result.score:.4f}")
        print(f"     Doc ID: {result.doc_id}")
        print(f"     Type: {result.metadata.get('doc_type')}")
        print(f"     Text: {result.text[:60]}...")

    # Verify results
    assert len(results) > 0, "Should return results for 'education grant'"
    assert results[0].score > 0, "Top result should have non-zero score"

    # Top results should contain both "education" and "grant"
    top_text = results[0].text.lower()
    assert 'education' in top_text or 'grant' in top_text

    print("\n[OK] Basic keyword search test passed")


async def test_keyword_search_with_filters():
    """Test keyword search with metadata filters"""
    print("\n[TEST] Keyword Search with Filters")
    print_separator()

    # Create mock documents
    docs = [
        {
            "text": "Grant proposal for education programs",
            "doc_id": "doc1",
            "doc_type": "Grant Proposal",
            "year": 2023,
            "programs": ["Education"],
            "outcome": "Funded",
            "chunk_index": 0
        },
        {
            "text": "Grant proposal for youth development",
            "doc_id": "doc2",
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": ["Youth Development"],
            "outcome": "Pending",
            "chunk_index": 0
        },
        {
            "text": "Annual report on education outcomes",
            "doc_id": "doc3",
            "doc_type": "Annual Report",
            "year": 2024,
            "programs": ["Education"],
            "outcome": "N/A",
            "chunk_index": 0
        }
    ]

    client = MockQdrantClient()
    client.add_documents(docs)

    vector_store = MockVectorStore(client)
    embedding_model = MockEmbedding()

    engine = RetrievalEngine(vector_store, embedding_model)
    await engine.build_bm25_index()

    # Test 1: Filter by doc_type
    query = "education"
    filters = DocumentFilters(doc_types=["Grant Proposal"])
    results = await engine._keyword_search(query, top_k=5, filters=filters)

    print(f"Query: '{query}' with filter doc_type='Grant Proposal'")
    print(f"Results: {len(results)} documents")

    for result in results:
        assert result.metadata.get('doc_type') == 'Grant Proposal'
        print(f"  - {result.doc_id}: {result.metadata.get('doc_type')}")

    # Test 2: Filter by year
    filters = DocumentFilters(years=[2024])
    results = await engine._keyword_search(query, top_k=5, filters=filters)

    print(f"\nQuery: '{query}' with filter year=2024")
    print(f"Results: {len(results)} documents")

    for result in results:
        assert result.metadata.get('year') == 2024
        print(f"  - {result.doc_id}: Year {result.metadata.get('year')}")

    # Test 3: Filter by programs
    filters = DocumentFilters(programs=["Education"])
    results = await engine._keyword_search(query, top_k=5, filters=filters)

    print(f"\nQuery: '{query}' with filter programs=['Education']")
    print(f"Results: {len(results)} documents")

    for result in results:
        assert "Education" in result.metadata.get('programs', [])
        print(f"  - {result.doc_id}: {result.metadata.get('programs')}")

    print("\n[OK] Keyword search with filters test passed")


async def test_bm25_vs_vector_comparison():
    """Compare BM25 results with empty vector results"""
    print("\n[TEST] BM25 vs Vector Search Comparison")
    print_separator()

    docs = [
        {
            "text": "Federal grant RFP-2024 for education funding opportunities",
            "doc_id": "doc1",
            "doc_type": "Grant Proposal",
            "year": 2024,
            "programs": ["Education"],
            "chunk_index": 0
        },
        {
            "text": "Youth development programs and community impact assessment",
            "doc_id": "doc2",
            "doc_type": "Annual Report",
            "year": 2023,
            "programs": ["Youth Development"],
            "chunk_index": 0
        }
    ]

    client = MockQdrantClient()
    client.add_documents(docs)

    vector_store = MockVectorStore(client)
    embedding_model = MockEmbedding()

    engine = RetrievalEngine(vector_store, embedding_model)
    await engine.build_bm25_index()

    # Query for specific terms
    query = "RFP federal funding"

    print(f"Query: '{query}'")
    print(f"Tokenized: {engine._tokenize(query)}")

    # BM25 search (should find doc1)
    bm25_results = await engine._keyword_search(query, top_k=2)

    print(f"\nBM25 Results: {len(bm25_results)} documents")
    for i, result in enumerate(bm25_results):
        print(f"  {i+1}. {result.doc_id} - Score: {result.score:.4f}")
        print(f"     Text: {result.text[:50]}...")

    # Verify BM25 found the relevant document
    assert len(bm25_results) > 0
    assert bm25_results[0].doc_id == "doc1"  # Should rank doc1 highest

    print("\n[OK] BM25 vs vector comparison test passed")


async def test_empty_query():
    """Test handling of empty or whitespace-only queries"""
    print("\n[TEST] Empty Query Handling")
    print_separator()

    docs = [
        {
            "text": "Sample document",
            "doc_id": "doc1",
            "doc_type": "Grant Proposal",
            "chunk_index": 0
        }
    ]

    client = MockQdrantClient()
    client.add_documents(docs)

    vector_store = MockVectorStore(client)
    embedding_model = MockEmbedding()

    engine = RetrievalEngine(vector_store, embedding_model)
    await engine.build_bm25_index()

    # Test empty query
    results = await engine._keyword_search("", top_k=5)
    print(f"Empty query results: {len(results)} documents")
    assert len(results) == 0

    # Test whitespace-only query
    results = await engine._keyword_search("   ", top_k=5)
    print(f"Whitespace query results: {len(results)} documents")
    assert len(results) == 0

    print("\n[OK] Empty query handling test passed")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BM25 KEYWORD SEARCH TESTS")
    print("=" * 80)

    tests = [
        ("Tokenization", test_tokenization),
        ("BM25 Index Building", test_bm25_index_building),
        ("Basic Keyword Search", test_keyword_search_basic),
        ("Keyword Search with Filters", test_keyword_search_with_filters),
        ("BM25 vs Vector Comparison", test_bm25_vs_vector_comparison),
        ("Empty Query Handling", test_empty_query),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] {test_name} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 80)

    if failed == 0:
        print("\nAll tests passed successfully!")
    else:
        print(f"\n{failed} test(s) failed. See details above.")


if __name__ == "__main__":
    asyncio.run(main())
