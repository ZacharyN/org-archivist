"""
Test recency weighting implementation

Tests the _apply_recency_weight() method to ensure:
1. Recent documents are boosted correctly
2. Older documents are penalized appropriately
3. Recency weight parameter controls the effect
4. Results are re-sorted after adjustment
5. Edge cases are handled (missing year, future dates, etc.)
"""
import sys
import os

# Set up test environment variables before any imports
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key-for-testing')
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-testing')
os.environ.setdefault('QDRANT_HOST', 'localhost')
os.environ.setdefault('POSTGRES_HOST', 'localhost')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.services.retrieval_engine import RetrievalEngine, RetrievalResult, RetrievalConfig


class MockEmbedding:
    """Mock embedding model for testing"""
    def get_text_embedding(self, text):
        return [0.1] * 1536


class MockVectorStore:
    """Mock vector store for testing"""
    async def search_similar(self, *args, **kwargs):
        return []


def test_recency_weighting_basic():
    """Test basic recency weighting with different document ages"""
    print("\n[TEST 1] Basic Recency Weighting")
    print("=" * 60)

    # Create engine
    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig(recency_weight=1.0)  # Full recency weighting
    )

    current_year = datetime.now().year

    # Create test results with different years
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Current year document",
            score=0.8,
            metadata={"doc_id": "doc1", "year": current_year}
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            text="One year old document",
            score=0.8,
            metadata={"doc_id": "doc2", "year": current_year - 1}
        ),
        RetrievalResult(
            chunk_id="chunk_3",
            text="Two year old document",
            score=0.8,
            metadata={"doc_id": "doc3", "year": current_year - 2}
        ),
        RetrievalResult(
            chunk_id="chunk_4",
            text="Five year old document",
            score=0.8,
            metadata={"doc_id": "doc4", "year": current_year - 5}
        ),
    ]

    # Apply recency weighting
    weighted = engine._apply_recency_weight(results, recency_weight=1.0)

    # Verify scores
    print("\nOriginal score: 0.8 for all documents")
    print(f"\nExpected multipliers:")
    print(f"  Current year ({current_year}): 1.0x")
    print(f"  1 year old ({current_year - 1}): 0.95x")
    print(f"  2 years old ({current_year - 2}): 0.90x")
    print(f"  5 years old ({current_year - 5}): 0.85x")

    print(f"\nActual adjusted scores:")
    for result in weighted:
        year = result.metadata.get("year")
        multiplier = result.metadata.get("_age_multiplier")
        original = result.metadata.get("_original_score")
        print(f"  Year {year}: {original:.4f} -> {result.score:.4f} (multiplier: {multiplier:.2f}x)")

    # Verify scores are correctly adjusted
    assert weighted[0].metadata["year"] == current_year
    assert abs(weighted[0].score - 0.8) < 0.001, f"Current year should have score 0.8, got {weighted[0].score}"

    assert weighted[1].metadata["year"] == current_year - 1
    assert abs(weighted[1].score - 0.76) < 0.001, f"1 year old should have score 0.76, got {weighted[1].score}"

    assert weighted[2].metadata["year"] == current_year - 2
    assert abs(weighted[2].score - 0.72) < 0.001, f"2 years old should have score 0.72, got {weighted[2].score}"

    assert weighted[3].metadata["year"] == current_year - 5
    assert abs(weighted[3].score - 0.68) < 0.001, f"5 years old should have score 0.68, got {weighted[3].score}"

    print("\n[OK] All scores adjusted correctly")


def test_recency_weight_parameter():
    """Test that recency_weight parameter controls effect strength"""
    print("\n[TEST 2] Recency Weight Parameter Effect")
    print("=" * 60)

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig()
    )

    current_year = datetime.now().year

    # Create result with old document
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Old document",
            score=1.0,
            metadata={"doc_id": "doc1", "year": current_year - 5}
        ),
    ]

    # Test different recency weights
    weights_to_test = [0.0, 0.3, 0.5, 0.7, 1.0]

    print(f"\nOriginal score: 1.0, Document age: 5 years")
    print(f"Age multiplier: 0.85x\n")
    print("Recency Weight | Adjusted Score | Expected")
    print("-" * 50)

    for weight in weights_to_test:
        weighted = engine._apply_recency_weight(results, recency_weight=weight)
        adjusted_score = weighted[0].score

        # Expected: score * (1 + weight * (0.85 - 1))
        expected_score = 1.0 * (1 + weight * (0.85 - 1))

        print(f"     {weight:.1f}       |     {adjusted_score:.4f}     |  {expected_score:.4f}")

        assert abs(adjusted_score - expected_score) < 0.001, \
            f"Weight {weight}: expected {expected_score}, got {adjusted_score}"

    print("\n[OK] Recency weight parameter works correctly")


def test_resorting_after_weighting():
    """Test that results are re-sorted after recency adjustment"""
    print("\n[TEST 3] Re-sorting After Recency Weighting")
    print("=" * 60)

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig(recency_weight=1.0)
    )

    current_year = datetime.now().year

    # Create results where older doc has higher original score
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Old document with high score",
            score=0.9,  # High score
            metadata={"doc_id": "doc1", "year": current_year - 5}  # Old (0.85x)
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            text="Recent document with lower score",
            score=0.75,  # Lower score
            metadata={"doc_id": "doc2", "year": current_year}  # Current (1.0x)
        ),
    ]

    print("\nBefore weighting:")
    for r in results:
        print(f"  {r.chunk_id}: score={r.score:.4f}, year={r.metadata['year']}")

    # Apply recency weighting
    weighted = engine._apply_recency_weight(results, recency_weight=1.0)

    print("\nAfter weighting (should be re-sorted):")
    for r in weighted:
        original = r.metadata.get("_original_score")
        print(f"  {r.chunk_id}: score={r.score:.4f} (was {original:.4f}), year={r.metadata['year']}")

    # Expected scores:
    # Old doc: 0.9 * 0.85 = 0.765
    # Recent doc: 0.75 * 1.0 = 0.75

    # Old doc should still be first (0.765 > 0.75)
    assert weighted[0].chunk_id == "chunk_1", "Old doc with high score should still be first"
    assert weighted[1].chunk_id == "chunk_2", "Recent doc should be second"

    # But let's test a case where sorting changes
    results2 = [
        RetrievalResult(
            chunk_id="chunk_3",
            text="Old document with medium score",
            score=0.8,  # Medium score
            metadata={"doc_id": "doc3", "year": current_year - 5}  # Old (0.85x)
        ),
        RetrievalResult(
            chunk_id="chunk_4",
            text="Recent document with medium score",
            score=0.75,  # Slightly lower
            metadata={"doc_id": "doc4", "year": current_year}  # Current (1.0x)
        ),
    ]

    weighted2 = engine._apply_recency_weight(results2, recency_weight=1.0)

    # Expected scores:
    # Old doc: 0.8 * 0.85 = 0.68
    # Recent doc: 0.75 * 1.0 = 0.75

    print("\nSecond test (order should change):")
    for r in weighted2:
        original = r.metadata.get("_original_score")
        print(f"  {r.chunk_id}: score={r.score:.4f} (was {original:.4f}), year={r.metadata['year']}")

    # Recent doc should now be first (0.75 > 0.68)
    assert weighted2[0].chunk_id == "chunk_4", "Recent doc should be first after weighting"
    assert weighted2[1].chunk_id == "chunk_3", "Old doc should be second"

    print("\n[OK] Re-sorting works correctly")


def test_missing_year_metadata():
    """Test handling of documents with missing year metadata"""
    print("\n[TEST 4] Missing Year Metadata")
    print("=" * 60)

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig(recency_weight=1.0)
    )

    current_year = datetime.now().year

    # Create results with missing year
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Document without year",
            score=1.0,
            metadata={"doc_id": "doc1"}  # No year field
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            text="Document with year",
            score=0.9,
            metadata={"doc_id": "doc2", "year": current_year}
        ),
    ]

    print("\nBefore weighting:")
    for r in results:
        year = r.metadata.get("year", "missing")
        print(f"  {r.chunk_id}: score={r.score:.4f}, year={year}")

    # Apply recency weighting
    weighted = engine._apply_recency_weight(results, recency_weight=1.0)

    print("\nAfter weighting:")
    for r in weighted:
        year = r.metadata.get("year", "missing")
        multiplier = r.metadata.get("_age_multiplier")
        print(f"  {r.chunk_id}: score={r.score:.4f}, year={year}, multiplier={multiplier:.2f}x")

    # Expected scores:
    # No year: 1.0 * 0.85 = 0.85
    # Current year: 0.9 * 1.0 = 0.9

    # Recent doc should be first (after sorting)
    assert weighted[0].chunk_id == "chunk_2", "Document with recent year should be first"
    assert weighted[1].chunk_id == "chunk_1", "Document without year should be second"

    # Document without year should use default multiplier (0.85)
    doc_without_year = [r for r in weighted if r.chunk_id == "chunk_1"][0]
    assert doc_without_year.metadata.get("_age_multiplier") == 0.85, \
        "Missing year should use default multiplier 0.85"

    print("\n[OK] Missing year handled correctly")


def test_edge_cases():
    """Test edge cases: empty results, zero weight, future dates"""
    print("\n[TEST 5] Edge Cases")
    print("=" * 60)

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig(recency_weight=1.0)
    )

    current_year = datetime.now().year

    # Test 1: Empty results
    print("\n5a. Empty results:")
    empty_results = []
    weighted_empty = engine._apply_recency_weight(empty_results, recency_weight=1.0)
    assert len(weighted_empty) == 0, "Empty results should return empty"
    print("  [OK] Empty results handled correctly")

    # Test 2: Zero recency weight (no adjustment)
    print("\n5b. Zero recency weight:")
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Old document",
            score=0.8,
            metadata={"doc_id": "doc1", "year": current_year - 5}
        ),
    ]
    weighted_zero = engine._apply_recency_weight(results, recency_weight=0.0)
    assert weighted_zero[0].score == 0.8, "Score should be unchanged with weight=0"
    print(f"  Original score: 0.8, Weighted score: {weighted_zero[0].score}")
    print("  [OK] Zero weight handled correctly")

    # Test 3: Future date (shouldn't happen, but handle gracefully)
    print("\n5c. Future date:")
    results_future = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Future document",
            score=0.8,
            metadata={"doc_id": "doc1", "year": current_year + 1}
        ),
    ]
    weighted_future = engine._apply_recency_weight(results_future, recency_weight=1.0)
    assert weighted_future[0].metadata.get("_age_multiplier") == 1.0, \
        "Future dates should use multiplier 1.0"
    assert weighted_future[0].score == 0.8, "Future date should not be penalized"
    print(f"  Future year: {current_year + 1}, multiplier: 1.0x, score unchanged")
    print("  [OK] Future date handled correctly")

    print("\n[OK] All edge cases handled correctly")


def test_real_world_scenario():
    """Test a real-world scenario with mixed documents"""
    print("\n[TEST 6] Real-World Scenario")
    print("=" * 60)

    engine = RetrievalEngine(
        vector_store=MockVectorStore(),
        embedding_model=MockEmbedding(),
        config=RetrievalConfig(recency_weight=0.7)  # Realistic weight
    )

    current_year = datetime.now().year

    # Create realistic mix of documents
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="2020 Grant Proposal",
            score=0.92,
            metadata={"doc_id": "doc1", "year": 2020, "doc_type": "Grant Proposal"}
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            text="2023 Annual Report",
            score=0.88,
            metadata={"doc_id": "doc2", "year": 2023, "doc_type": "Annual Report"}
        ),
        RetrievalResult(
            chunk_id="chunk_3",
            text=f"{current_year} Budget Narrative",
            score=0.85,
            metadata={"doc_id": "doc3", "year": current_year, "doc_type": "Budget"}
        ),
        RetrievalResult(
            chunk_id="chunk_4",
            text="2021 Letter of Intent",
            score=0.90,
            metadata={"doc_id": "doc4", "year": 2021, "doc_type": "LOI"}
        ),
        RetrievalResult(
            chunk_id="chunk_5",
            text=f"{current_year - 1} Impact Report",
            score=0.87,
            metadata={"doc_id": "doc5", "year": current_year - 1, "doc_type": "Report"}
        ),
    ]

    print(f"\nScenario: Grant writing search with recency_weight=0.7")
    print(f"Current year: {current_year}\n")

    print("Original ranking (by relevance score):")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r.text:30} score={r.score:.4f}  year={r.metadata['year']}")

    # Apply recency weighting
    weighted = engine._apply_recency_weight(results, recency_weight=0.7)

    print(f"\nAfter recency weighting (weight=0.7):")
    for i, r in enumerate(weighted, 1):
        original = r.metadata.get("_original_score")
        age = current_year - r.metadata["year"]
        print(f"  {i}. {r.text:30} score={r.score:.4f} (was {original:.4f})  age={age}yr")

    # Verify current year doc got boosted
    current_year_doc = [r for r in weighted if r.metadata["year"] == current_year][0]
    assert current_year_doc.chunk_id == "chunk_3"
    print(f"\n[INSIGHT] Current year document moved from 3rd to position {weighted.index(current_year_doc) + 1}")

    # Verify old docs got penalized
    old_doc = [r for r in weighted if r.metadata["year"] == 2020][0]
    assert old_doc.score < 0.92, "Old document should have reduced score"
    print(f"[INSIGHT] 2020 document (high relevance) penalized: 0.92 -> {old_doc.score:.4f}")

    print("\n[OK] Real-world scenario works as expected")


def run_all_tests():
    """Run all recency weighting tests"""
    print("\n" + "=" * 60)
    print("RECENCY WEIGHTING TESTS")
    print("=" * 60)

    try:
        test_recency_weighting_basic()
        test_recency_weight_parameter()
        test_resorting_after_weighting()
        test_missing_year_metadata()
        test_edge_cases()
        test_real_world_scenario()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nRecency weighting implementation verified:")
        print("  - Age-based multipliers work correctly")
        print("  - Recency weight parameter controls effect strength")
        print("  - Results are properly re-sorted after adjustment")
        print("  - Edge cases handled gracefully")
        print("  - Real-world scenarios work as expected")

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
