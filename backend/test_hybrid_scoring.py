"""
Test hybrid scoring and result combination

Tests the _combine_results() method with various scenarios:
- Vector and keyword results with duplicates
- Empty result sets
- Score normalization
- Weighted combination
- Various weight configurations
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

# Set dummy environment variables
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'

from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig, RetrievalResult


# Mock classes for dependencies
class MockEmbedding:
    """Mock embedding model"""
    def get_text_embedding(self, text):
        return [0.1] * 1536


class MockVectorStore:
    """Mock vector store"""
    async def search_similar(self, *args, **kwargs):
        return []


def test_normalize_scores():
    """Test score normalization"""
    print("\n=== Test 1: Score Normalization ===")

    # Create engine
    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    # Create test results with varying scores
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Test text 1",
            score=0.95,
            metadata={"doc_id": "doc_1"}
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            text="Test text 2",
            score=0.75,
            metadata={"doc_id": "doc_2"}
        ),
        RetrievalResult(
            chunk_id="chunk_3",
            text="Test text 3",
            score=0.50,
            metadata={"doc_id": "doc_3"}
        ),
    ]

    # Normalize
    normalized = engine._normalize_scores(results)

    print(f"Original scores: {[r.score for r in results]}")
    print(f"Normalized scores: {[r.score for r in normalized]}")

    # Verify normalization
    assert normalized[0].score == 1.0, "Max score should be 1.0"
    assert normalized[2].score == 0.0, "Min score should be 0.0"
    assert 0.0 <= normalized[1].score <= 1.0, "Middle score should be between 0 and 1"

    print("[OK] Score normalization works correctly")


def test_combine_no_duplicates():
    """Test combining results with no duplicates"""
    print("\n=== Test 2: Combine Results (No Duplicates) ===")

    # Create engine with default weights (0.7 vector, 0.3 keyword)
    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    # Vector results
    vector_results = [
        RetrievalResult(
            chunk_id="vec_1",
            text="Vector result 1",
            score=0.9,
            metadata={"doc_id": "doc_1", "source": "vector"}
        ),
        RetrievalResult(
            chunk_id="vec_2",
            text="Vector result 2",
            score=0.8,
            metadata={"doc_id": "doc_2", "source": "vector"}
        ),
    ]

    # Keyword results
    keyword_results = [
        RetrievalResult(
            chunk_id="kw_1",
            text="Keyword result 1",
            score=10.5,  # Different scale (BM25 scores)
            metadata={"doc_id": "doc_3", "source": "keyword"}
        ),
        RetrievalResult(
            chunk_id="kw_2",
            text="Keyword result 2",
            score=8.2,
            metadata={"doc_id": "doc_4", "source": "keyword"}
        ),
    ]

    # Combine
    combined = engine._combine_results(vector_results, keyword_results)

    print(f"Vector results: {len(vector_results)}")
    print(f"Keyword results: {len(keyword_results)}")
    print(f"Combined results: {len(combined)}")
    print(f"Top 3 scores: {[r.score for r in combined[:3]]}")

    # Verify
    assert len(combined) == 4, "Should have 4 unique chunks"
    assert combined[0].score >= combined[1].score, "Results should be sorted by score"
    assert all(0.0 <= r.score <= 1.0 for r in combined), "Scores should be in [0, 1] range"

    print("[OK] No-duplicate combination works correctly")


def test_combine_with_duplicates():
    """Test combining results with duplicates"""
    print("\n=== Test 3: Combine Results (With Duplicates) ===")

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    # Vector results
    vector_results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Duplicate chunk",
            score=0.9,
            metadata={"doc_id": "doc_1"}
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            text="Unique vector",
            score=0.7,
            metadata={"doc_id": "doc_2"}
        ),
    ]

    # Keyword results (chunk_1 appears in both)
    keyword_results = [
        RetrievalResult(
            chunk_id="chunk_1",  # DUPLICATE
            text="Duplicate chunk",
            score=15.0,
            metadata={"doc_id": "doc_1"}
        ),
        RetrievalResult(
            chunk_id="chunk_3",
            text="Unique keyword",
            score=12.0,
            metadata={"doc_id": "doc_3"}
        ),
    ]

    # Combine
    combined = engine._combine_results(vector_results, keyword_results)

    print(f"Vector results: {len(vector_results)}")
    print(f"Keyword results: {len(keyword_results)}")
    print(f"Combined results: {len(combined)}")
    print(f"Expected duplicates: 1")

    # Verify
    assert len(combined) == 3, "Should have 3 unique chunks (1 duplicate)"

    # Find the duplicate chunk
    duplicate = next(r for r in combined if r.chunk_id == "chunk_1")

    # Verify it has scores from both sources
    assert "_vector_score" in duplicate.metadata, "Should have vector score"
    assert "_keyword_score" in duplicate.metadata, "Should have keyword score"
    assert duplicate.metadata["_vector_score"] > 0.0, "Vector score should be > 0"
    assert duplicate.metadata["_keyword_score"] > 0.0, "Keyword score should be > 0"

    print(f"Duplicate chunk scores:")
    print(f"  Vector: {duplicate.metadata['_vector_score']:.4f}")
    print(f"  Keyword: {duplicate.metadata['_keyword_score']:.4f}")
    print(f"  Hybrid: {duplicate.metadata['_hybrid_score']:.4f}")

    print("[OK] Duplicate detection and score aggregation works correctly")


def test_weight_configurations():
    """Test different weight configurations"""
    print("\n=== Test 4: Different Weight Configurations ===")

    # Prepare test data
    vector_results = [
        RetrievalResult(chunk_id="chunk_1", text="Test", score=0.9, metadata={}),
        RetrievalResult(chunk_id="chunk_2", text="Test", score=0.7, metadata={}),
    ]

    keyword_results = [
        RetrievalResult(chunk_id="chunk_3", text="Test", score=15.0, metadata={}),
        RetrievalResult(chunk_id="chunk_4", text="Test", score=10.0, metadata={}),
    ]

    # Test different weight configurations
    configs = [
        (1.0, 0.0, "Vector only"),
        (0.0, 1.0, "Keyword only"),
        (0.7, 0.3, "Balanced (default)"),
        (0.5, 0.5, "Equal weights"),
    ]

    for vec_weight, kw_weight, description in configs:
        config = RetrievalConfig(
            vector_weight=vec_weight,
            keyword_weight=kw_weight
        )

        engine = RetrievalEngine(
            vector_store=MockVectorStore(),
            embedding_model=MockEmbedding(),
            config=config
        )

        combined = engine._combine_results(vector_results, keyword_results)

        print(f"\n{description} ({vec_weight:.1f}v + {kw_weight:.1f}k):")
        print(f"  Top score: {combined[0].score:.4f}")
        print(f"  Top chunk: {combined[0].chunk_id}")

    print("\n[OK] Weight configurations tested successfully")


def test_empty_results():
    """Test handling of empty result sets"""
    print("\n=== Test 5: Empty Result Sets ===")

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    # Test empty vector results
    vector_results = []
    keyword_results = [
        RetrievalResult(chunk_id="kw_1", text="Test", score=10.0, metadata={})
    ]
    combined = engine._combine_results(vector_results, keyword_results)
    assert len(combined) == 1, "Should return keyword results only"
    print("[OK] Empty vector results handled correctly")

    # Test empty keyword results
    vector_results = [
        RetrievalResult(chunk_id="vec_1", text="Test", score=0.9, metadata={})
    ]
    keyword_results = []
    combined = engine._combine_results(vector_results, keyword_results)
    assert len(combined) == 1, "Should return vector results only"
    print("[OK] Empty keyword results handled correctly")

    # Test both empty
    combined = engine._combine_results([], [])
    assert len(combined) == 0, "Should return empty list"
    print("[OK] Both empty handled correctly")


def test_score_distribution():
    """Test that scores are properly distributed after combination"""
    print("\n=== Test 6: Score Distribution ===")

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding()
    )

    # Create results with clear score patterns
    vector_results = [
        RetrievalResult(chunk_id=f"v_{i}", text="Test", score=1.0 - (i * 0.1), metadata={})
        for i in range(5)
    ]

    keyword_results = [
        RetrievalResult(chunk_id=f"k_{i}", text="Test", score=20.0 - (i * 2.0), metadata={})
        for i in range(5)
    ]

    combined = engine._combine_results(vector_results, keyword_results)

    print(f"Combined {len(combined)} results")
    print(f"Score range: [{min(r.score for r in combined):.4f}, {max(r.score for r in combined):.4f}]")

    # Check that scores are monotonically decreasing (or equal)
    for i in range(len(combined) - 1):
        assert combined[i].score >= combined[i + 1].score, "Scores should be sorted descending"

    print("[OK] Score distribution is correct")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Testing Hybrid Scoring Implementation")
    print("=" * 60)

    try:
        test_normalize_scores()
        test_combine_no_duplicates()
        test_combine_with_duplicates()
        test_weight_configurations()
        test_empty_results()
        test_score_distribution()

        print("\n" + "=" * 60)
        print("All tests passed successfully!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
