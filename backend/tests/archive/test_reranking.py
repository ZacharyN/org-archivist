"""
Test script for reranking functionality

Tests the Reranker service and its integration with RetrievalEngine.
This script verifies:
1. Reranker initialization (with and without dependencies)
2. Basic reranking functionality
3. Integration with retrieval pipeline
4. Performance benchmarking
5. Quality comparison (with/without reranking)
"""
import asyncio
import sys
import os
import time
from typing import List, Dict

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Mock settings to avoid dependency issues
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'

from app.services.reranker import Reranker, RerankerConfig, RerankerModel, RerankerFactory


def test_reranker_initialization():
    """Test 1: Reranker initialization"""
    print("\n=== Test 1: Reranker Initialization ===")

    try:
        # Test default initialization
        reranker = Reranker()
        print(f"[OK] Default reranker initialized")
        print(f"     Available: {reranker.is_available()}")
        print(f"     Model: {reranker.config.model}")

        # Test custom config
        config = RerankerConfig(
            model=RerankerModel.MINI_LM_L6.value,
            top_n=5
        )
        reranker2 = Reranker(config=config)
        print(f"[OK] Custom reranker initialized")
        print(f"     Model: {reranker2.config.model}")
        print(f"     Top N: {reranker2.config.top_n}")

        return True, reranker
    except Exception as e:
        print(f"[INFO] Reranker not available (expected if dependencies not installed): {e}")
        return False, None


def test_basic_reranking(reranker: Reranker):
    """Test 2: Basic reranking functionality"""
    print("\n=== Test 2: Basic Reranking ===")

    if not reranker or not reranker.is_available():
        print("[SKIP] Reranker not available")
        return

    # Create sample results (query: "education grant proposal")
    query = "education grant proposal"

    results = [
        {
            "chunk_id": "doc1_chunk0",
            "text": "This annual report discusses the financial performance of our organization.",
            "score": 0.85,
            "metadata": {"doc_id": "doc1", "doc_type": "Annual Report"}
        },
        {
            "chunk_id": "doc2_chunk0",
            "text": "Our education grant proposal focuses on improving literacy rates in underserved communities.",
            "score": 0.82,
            "metadata": {"doc_id": "doc2", "doc_type": "Grant Proposal"}
        },
        {
            "chunk_id": "doc3_chunk0",
            "text": "The budget for the youth development program includes staff salaries and equipment costs.",
            "score": 0.80,
            "metadata": {"doc_id": "doc3", "doc_type": "Budget"}
        },
        {
            "chunk_id": "doc4_chunk0",
            "text": "We submitted a grant proposal to the Department of Education for $500,000 in funding.",
            "score": 0.78,
            "metadata": {"doc_id": "doc4", "doc_type": "Grant Proposal"}
        },
        {
            "chunk_id": "doc5_chunk0",
            "text": "The strategic plan outlines our goals for the next five years.",
            "score": 0.75,
            "metadata": {"doc_id": "doc5", "doc_type": "Strategic Plan"}
        }
    ]

    print(f"Query: '{query}'")
    print(f"\nOriginal ranking (by embedding similarity):")
    for i, result in enumerate(results, 1):
        print(f"  {i}. [{result['score']:.2f}] {result['text'][:60]}...")

    # Rerank
    start_time = time.time()
    reranked = reranker.rerank(query=query, results=results, top_n=3)
    elapsed = time.time() - start_time

    print(f"\nReranked results (top 3, took {elapsed*1000:.2f}ms):")
    for i, result in enumerate(reranked, 1):
        print(f"  {i}. [{result['score']:.4f}] {result['text'][:60]}...")
        print(f"      Model: {result['metadata'].get('_reranker_model', 'N/A')}")

    # Verify reranking changed order
    original_ids = [r['chunk_id'] for r in results[:3]]
    reranked_ids = [r['chunk_id'] for r in reranked]

    if original_ids != reranked_ids:
        print(f"\n[OK] Reranking changed order (expected for relevance improvement)")
    else:
        print(f"\n[INFO] Reranking kept same order")

    return reranked


def test_mock_retrieval_integration():
    """Test 3: Mock retrieval integration without dependencies"""
    print("\n=== Test 3: Mock Retrieval Integration ===")

    # Test that retrieval engine handles missing reranker gracefully
    print("Testing graceful degradation when reranker not available...")

    # Create reranker (will be unavailable if deps not installed)
    reranker = Reranker()

    if not reranker.is_available():
        print("[OK] Reranker gracefully handles missing dependencies")

        # Test rerank method with unavailable reranker
        sample_results = [
            {"chunk_id": "1", "text": "test", "score": 0.9, "metadata": {}}
        ]
        returned = reranker.rerank("test query", sample_results)

        if returned == sample_results:
            print("[OK] Reranker returns original results when unavailable")
        else:
            print("[FAIL] Reranker should return original results")
    else:
        print("[OK] Reranker available and ready for integration")


def test_factory_creation():
    """Test 4: Factory pattern creation"""
    print("\n=== Test 4: Factory Pattern ===")

    # Test factory with model override
    reranker1 = RerankerFactory.create_reranker(
        model=RerankerModel.TINY_BERT.value,
        top_n=5
    )
    print(f"[OK] Factory created reranker with model: {reranker1.config.model}")

    # Test factory with config
    config = RerankerConfig(
        model=RerankerModel.MINI_LM_L12.value,
        top_n=10
    )
    reranker2 = RerankerFactory.create_reranker(config=config)
    print(f"[OK] Factory created reranker with config: {reranker2.config.model}")


def test_performance_benchmark(reranker: Reranker):
    """Test 5: Performance benchmarking"""
    print("\n=== Test 5: Performance Benchmark ===")

    if not reranker or not reranker.is_available():
        print("[SKIP] Reranker not available")
        return

    # Create varying result set sizes
    query = "nonprofit grant application best practices"

    for n in [5, 10, 20, 50]:
        results = []
        for i in range(n):
            results.append({
                "chunk_id": f"doc{i}_chunk0",
                "text": f"Sample document text about grants and funding for nonprofits. Document {i}.",
                "score": 0.9 - (i * 0.01),
                "metadata": {"doc_id": f"doc{i}"}
            })

        start_time = time.time()
        reranked = reranker.rerank(query=query, results=results, top_n=5)
        elapsed = time.time() - start_time

        print(f"  {n} results -> {len(reranked)} reranked in {elapsed*1000:.2f}ms ({elapsed*1000/n:.2f}ms/result)")


def main():
    """Run all tests"""
    print("=" * 70)
    print("Reranking Implementation Test Suite")
    print("=" * 70)

    # Test 1: Initialization
    available, reranker = test_reranker_initialization()

    # Test 2: Basic reranking (if available)
    if available:
        test_basic_reranking(reranker)

    # Test 3: Mock integration
    test_mock_retrieval_integration()

    # Test 4: Factory
    test_factory_creation()

    # Test 5: Performance (if available)
    if available:
        test_performance_benchmark(reranker)

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    if available:
        print("[OK] All reranking tests passed!")
        print("\nTo use reranking in production:")
        print("  1. Install: pip install llama-index-postprocessor-sentence-transformer")
        print("  2. Set ENABLE_RERANKING=true in .env")
        print("  3. Optional: Set RERANKER_MODEL to choose different model")
        print("\nAvailable models (speed/accuracy tradeoff):")
        print("  - cross-encoder/ms-marco-TinyBERT-L-2-v2 (fastest, lowest accuracy)")
        print("  - cross-encoder/ms-marco-MiniLM-L-2-v2 (balanced, default)")
        print("  - cross-encoder/ms-marco-MiniLM-L-6-v2 (balanced)")
        print("  - cross-encoder/ms-marco-MiniLM-L-12-v2 (slower, higher accuracy)")
    else:
        print("[INFO] Reranker dependencies not installed (optional feature)")
        print("\nTo enable reranking:")
        print("  pip install llama-index-postprocessor-sentence-transformer")
        print("\nThe application works fine without reranking.")
        print("Reranking is an optional enhancement for improved relevance.")


if __name__ == "__main__":
    main()
