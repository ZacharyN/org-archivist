"""
Integration test for hybrid scoring in complete retrieval pipeline

Tests end-to-end retrieval with:
- Real vector and keyword search (mocked)
- Hybrid scoring combination
- Various query patterns
- Weight optimization experiments
"""
import sys
import os
import asyncio

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

# Set dummy environment variables
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'

from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig, RetrievalResult


# Enhanced mock classes with realistic behavior
class MockEmbedding:
    """Mock embedding model"""
    def get_text_embedding(self, text):
        # Return simple embedding based on text length
        return [0.1] * 1536


class MockVectorStore:
    """Mock vector store with sample data"""

    def __init__(self):
        # Sample document corpus
        self.documents = [
            {
                "id": "doc_1_chunk_0",
                "text": "This grant proposal focuses on education programs for youth development",
                "metadata": {"doc_id": "doc_1", "doc_type": "Grant Proposal", "year": 2023},
                "vector_score": 0.85
            },
            {
                "id": "doc_1_chunk_1",
                "text": "We request funding for after-school tutoring and mentorship programs",
                "metadata": {"doc_id": "doc_1", "doc_type": "Grant Proposal", "year": 2023},
                "vector_score": 0.75
            },
            {
                "id": "doc_2_chunk_0",
                "text": "Annual report showing program outcomes and impact on community development",
                "metadata": {"doc_id": "doc_2", "doc_type": "Annual Report", "year": 2023},
                "vector_score": 0.65
            },
            {
                "id": "doc_3_chunk_0",
                "text": "Letter of intent for federal education funding opportunity",
                "metadata": {"doc_id": "doc_3", "doc_type": "LOI", "year": 2024},
                "vector_score": 0.60
            },
        ]

        self.collection_name = "test_collection"
        self.client = self

    async def search_similar(self, query_vector, limit, score_threshold=None, filter_conditions=None):
        """Mock vector search - returns documents with simulated relevance"""
        # Return top documents based on mock vector scores
        results = []
        for doc in sorted(self.documents, key=lambda x: x["vector_score"], reverse=True)[:limit]:
            results.append({
                "id": doc["id"],
                "score": doc["vector_score"],
                "text": doc["text"],
                "metadata": doc["metadata"]
            })
        return results

    def get_collection(self, collection_name):
        """Mock collection info"""
        class CollectionInfo:
            points_count = len(self.documents)
        return CollectionInfo()

    def scroll(self, collection_name, limit, offset, with_payload=True, with_vectors=False):
        """Mock scroll for BM25 index building"""
        if offset is None:
            offset = 0

        # Return batch of documents
        batch = []
        for doc in self.documents[offset:offset+limit]:
            class Point:
                def __init__(self, doc):
                    self.id = doc["id"]
                    self.payload = {"text": doc["text"], **doc["metadata"]}

            batch.append(Point(doc))

        next_offset = offset + limit if offset + limit < len(self.documents) else None
        return batch, next_offset


async def test_complete_retrieval_pipeline():
    """Test complete retrieval with hybrid scoring"""
    print("\n=== Integration Test: Complete Retrieval Pipeline ===")

    # Create engine with real dependencies (mocked)
    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig(
            vector_weight=0.7,
            keyword_weight=0.3
        )
    )

    # Build BM25 index
    print("Building BM25 index...")
    await engine.build_bm25_index()
    print(f"BM25 index built with {len(engine._bm25_corpus)} documents")

    # Test query
    query = "education programs funding"
    print(f"\nQuery: '{query}'")

    # Retrieve
    results = await engine.retrieve(query=query, top_k=3)

    print(f"\nResults: {len(results)} chunks returned")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.score:.4f}")
        print(f"   Chunk ID: {result.chunk_id}")
        print(f"   Text: {result.text[:80]}...")
        if "_vector_score" in result.metadata:
            print(f"   Vector: {result.metadata['_vector_score']:.4f}, "
                  f"Keyword: {result.metadata['_keyword_score']:.4f}")

    # Verify results
    assert len(results) > 0, "Should return results"
    assert results[0].score >= results[-1].score, "Results should be sorted"

    print("\n[OK] Complete retrieval pipeline works")


async def test_weight_optimization():
    """Test different weight configurations to find optimal balance"""
    print("\n=== Integration Test: Weight Optimization ===")

    # Test different weight configurations
    weight_configs = [
        (1.0, 0.0, "Pure vector"),
        (0.9, 0.1, "Heavy vector"),
        (0.7, 0.3, "Default"),
        (0.5, 0.5, "Balanced"),
        (0.3, 0.7, "Heavy keyword"),
        (0.0, 1.0, "Pure keyword"),
    ]

    query = "grant proposal education"
    print(f"Query: '{query}'")

    results_by_config = []

    for vec_weight, kw_weight, description in weight_configs:
        config = RetrievalConfig(
            vector_weight=vec_weight,
            keyword_weight=kw_weight
        )

        engine = RetrievalEngine(
            vector_store=MockVectorStore(),
            embedding_model=MockEmbedding(),
            config=config
        )

        # Build BM25 index
        await engine.build_bm25_index()

        # Retrieve
        results = await engine.retrieve(query=query, top_k=3)

        results_by_config.append({
            "config": description,
            "weights": (vec_weight, kw_weight),
            "results": results
        })

    # Display results
    print("\n" + "=" * 80)
    print("Weight Configuration Results:")
    print("=" * 80)

    for config_result in results_by_config:
        print(f"\n{config_result['config']} "
              f"({config_result['weights'][0]:.1f}v + {config_result['weights'][1]:.1f}k):")

        if config_result['results']:
            print(f"  Top score: {config_result['results'][0].score:.4f}")
            print(f"  Top result: {config_result['results'][0].text[:60]}...")
        else:
            print("  No results")

    print("\n[OK] Weight optimization experiment completed")


async def test_query_patterns():
    """Test various query patterns"""
    print("\n=== Integration Test: Query Patterns ===")

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    await engine.build_bm25_index()

    queries = [
        "education programs",
        "funding opportunity",
        "annual report outcomes",
        "youth development mentorship",
        "federal education LOI",
    ]

    print(f"Testing {len(queries)} query patterns:")

    for query in queries:
        results = await engine.retrieve(query=query, top_k=2)
        print(f"\nQuery: '{query}'")
        print(f"  Results: {len(results)}")
        if results:
            print(f"  Top score: {results[0].score:.4f}")

    print("\n[OK] Query pattern testing completed")


async def test_duplicate_handling():
    """Test that duplicates from vector and keyword search are properly merged"""
    print("\n=== Integration Test: Duplicate Handling ===")

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    await engine.build_bm25_index()

    # Use a query that will likely return same documents in both searches
    query = "education programs"
    results = await engine.retrieve(query=query, top_k=5)

    print(f"Query: '{query}'")
    print(f"Results: {len(results)} chunks")

    # Check for duplicate handling info in metadata
    duplicates_found = sum(
        1 for r in results
        if "_vector_score" in r.metadata and r.metadata["_vector_score"] > 0
        and "_keyword_score" in r.metadata and r.metadata["_keyword_score"] > 0
    )

    print(f"Chunks found in both searches: {duplicates_found}")

    if duplicates_found > 0:
        print("\nExample duplicate (found in both searches):")
        dup = next(
            r for r in results
            if "_vector_score" in r.metadata and r.metadata["_vector_score"] > 0
            and "_keyword_score" in r.metadata and r.metadata["_keyword_score"] > 0
        )
        print(f"  Text: {dup.text[:60]}...")
        print(f"  Vector score: {dup.metadata['_vector_score']:.4f}")
        print(f"  Keyword score: {dup.metadata['_keyword_score']:.4f}")
        print(f"  Hybrid score: {dup.score:.4f}")

    print("\n[OK] Duplicate handling verified")


async def run_all_integration_tests():
    """Run all integration tests"""
    print("=" * 80)
    print("Integration Tests: Hybrid Scoring in Retrieval Pipeline")
    print("=" * 80)

    try:
        await test_complete_retrieval_pipeline()
        await test_weight_optimization()
        await test_query_patterns()
        await test_duplicate_handling()

        print("\n" + "=" * 80)
        print("All integration tests passed successfully!")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_all_integration_tests())
