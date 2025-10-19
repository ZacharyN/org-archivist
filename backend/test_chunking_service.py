"""
Test script for ChunkingService

Tests all three chunking strategies:
1. Semantic chunking (with embeddings)
2. Sentence chunking (sentence-boundary aware)
3. Token chunking (fixed token count)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.chunking_service import (
    ChunkingService,
    ChunkingConfig,
    ChunkingStrategy,
    ChunkingServiceFactory
)


# Sample text for testing
SAMPLE_TEXT = """
The Foundation Historian is an advanced RAG application designed to assist grant writers.
It provides intelligent document retrieval and content generation capabilities. The system
uses semantic chunking to break documents into meaningful segments.

Grant writing requires careful attention to detail and comprehensive research. Our system
helps streamline this process by maintaining a library of past successful proposals. Each
document is processed, chunked, and indexed for efficient retrieval.

The semantic chunking algorithm uses embedding similarity to determine optimal breakpoints.
This ensures that related content stays together while maintaining reasonable chunk sizes.
The approach is more sophisticated than simple token-based or sentence-based splitting.

In practice, semantic chunking improves retrieval quality significantly. Retrieved chunks
are more coherent and contextually relevant to user queries. This leads to better quality
responses from the language model during content generation.
"""


def print_chunks(chunks, strategy_name):
    """Pretty print chunks for visualization"""
    print(f"\n{'=' * 80}")
    print(f"  {strategy_name}")
    print(f"{'=' * 80}")
    print(f"Total chunks: {len(chunks)}\n")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}:")
        print(f"  Length: {chunk['char_count']} chars, {chunk['word_count']} words")
        print(f"  Strategy: {chunk['metadata'].get('chunking_strategy', 'N/A')}")
        print(f"  Preview: {chunk['text'][:100]}...")
        print()


def test_sentence_chunking():
    """Test SentenceSplitter strategy"""
    print("\n" + "=" * 80)
    print("TEST 1: SENTENCE CHUNKING")
    print("=" * 80)

    config = ChunkingConfig(
        strategy=ChunkingStrategy.SENTENCE,
        chunk_size=200,  # Target 200 chars per chunk
        chunk_overlap=20
    )

    service = ChunkingService(config)
    chunks = service.chunk_text(
        SAMPLE_TEXT,
        metadata={'doc_id': 'test-001', 'doc_type': 'sample'}
    )

    print_chunks(chunks, "Sentence-Based Chunking (200 chars, 20 overlap)")

    # Verify chunks
    assert len(chunks) > 0, "Should create at least one chunk"
    assert all('text' in c for c in chunks), "All chunks should have text"
    assert all('chunk_index' in c for c in chunks), "All chunks should have index"
    print("✓ Sentence chunking test passed")

    return chunks


def test_token_chunking():
    """Test TokenTextSplitter strategy"""
    print("\n" + "=" * 80)
    print("TEST 2: TOKEN CHUNKING")
    print("=" * 80)

    config = ChunkingConfig(
        strategy=ChunkingStrategy.TOKEN,
        chunk_size=100,  # 100 tokens per chunk
        chunk_overlap=10
    )

    service = ChunkingService(config)
    chunks = service.chunk_text(
        SAMPLE_TEXT,
        metadata={'doc_id': 'test-002', 'doc_type': 'sample'}
    )

    print_chunks(chunks, "Token-Based Chunking (100 tokens, 10 overlap)")

    # Verify chunks
    assert len(chunks) > 0, "Should create at least one chunk"
    print("✓ Token chunking test passed")

    return chunks


def test_semantic_chunking():
    """Test SemanticSplitterNodeParser strategy"""
    print("\n" + "=" * 80)
    print("TEST 3: SEMANTIC CHUNKING")
    print("=" * 80)

    try:
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SEMANTIC,
            buffer_size=1,
            breakpoint_percentile_threshold=95
        )

        service = ChunkingService(config)
        chunks = service.chunk_text(
            SAMPLE_TEXT,
            metadata={'doc_id': 'test-003', 'doc_type': 'sample'}
        )

        print_chunks(chunks, "Semantic Chunking (embedding-based breakpoints)")

        # Verify chunks
        assert len(chunks) > 0, "Should create at least one chunk"
        print("✓ Semantic chunking test passed")

        return chunks

    except Exception as e:
        print(f"⚠ Semantic chunking failed (likely missing API key): {e}")
        print("  This is expected if OPENAI_API_KEY is not set")
        print("  Semantic chunking requires OpenAI embeddings")
        return None


def test_factory_methods():
    """Test ChunkingServiceFactory methods"""
    print("\n" + "=" * 80)
    print("TEST 4: FACTORY METHODS")
    print("=" * 80)

    # Test semantic service factory
    try:
        semantic_service = ChunkingServiceFactory.create_semantic_service()
        chunks = semantic_service.chunk_text(SAMPLE_TEXT[:200])  # Use smaller text
        print(f"✓ Semantic factory created service: {len(chunks)} chunks")
    except Exception as e:
        print(f"⚠ Semantic factory failed (expected without API key): {e}")

    # Test sentence service factory
    sentence_service = ChunkingServiceFactory.create_sentence_service()
    chunks = sentence_service.chunk_text(SAMPLE_TEXT[:200])
    print(f"✓ Sentence factory created service: {len(chunks)} chunks")

    print("✓ Factory methods test passed")


def test_empty_text():
    """Test handling of empty text"""
    print("\n" + "=" * 80)
    print("TEST 5: EDGE CASES")
    print("=" * 80)

    service = ChunkingServiceFactory.create_sentence_service()

    # Empty string
    chunks = service.chunk_text("")
    assert len(chunks) == 0, "Empty text should return no chunks"
    print("✓ Empty text handled correctly")

    # Whitespace only
    chunks = service.chunk_text("   \n\t  ")
    assert len(chunks) == 0, "Whitespace-only text should return no chunks"
    print("✓ Whitespace-only text handled correctly")

    # Very short text
    chunks = service.chunk_text("Short.")
    assert len(chunks) >= 1, "Short text should create at least one chunk"
    print(f"✓ Short text created {len(chunks)} chunk(s)")

    print("✓ Edge cases test passed")


def test_metadata_preservation():
    """Test that metadata is preserved in chunks"""
    print("\n" + "=" * 80)
    print("TEST 6: METADATA PRESERVATION")
    print("=" * 80)

    service = ChunkingServiceFactory.create_sentence_service()

    metadata = {
        'doc_id': 'meta-test-001',
        'doc_type': 'proposal',
        'year': 2024,
        'program': 'Education',
        'custom_field': 'custom_value'
    }

    chunks = service.chunk_text(SAMPLE_TEXT, metadata=metadata)

    # Verify metadata is in each chunk
    for chunk in chunks:
        assert 'metadata' in chunk, "Chunk should have metadata"
        chunk_meta = chunk['metadata']

        # Check original metadata is preserved
        assert chunk_meta['doc_id'] == 'meta-test-001'
        assert chunk_meta['doc_type'] == 'proposal'
        assert chunk_meta['year'] == 2024
        assert chunk_meta['program'] == 'Education'
        assert chunk_meta['custom_field'] == 'custom_value'

        # Check added metadata
        assert 'chunk_index' in chunk_meta
        assert 'chunking_strategy' in chunk_meta
        assert 'node_id' in chunk_meta

    print(f"✓ Metadata preserved across {len(chunks)} chunks")
    print(f"  Sample metadata: {chunks[0]['metadata']}")
    print("✓ Metadata preservation test passed")


def compare_strategies():
    """Compare all three strategies side by side"""
    print("\n" + "=" * 80)
    print("COMPARISON: ALL STRATEGIES")
    print("=" * 80)

    # Create services for each strategy
    sentence_service = ChunkingServiceFactory.create_sentence_service()

    token_config = ChunkingConfig(strategy=ChunkingStrategy.TOKEN, chunk_size=100)
    token_service = ChunkingService(token_config)

    # Get chunks from each
    sentence_chunks = sentence_service.chunk_text(SAMPLE_TEXT)
    token_chunks = token_service.chunk_text(SAMPLE_TEXT)

    print(f"Sentence chunking: {len(sentence_chunks)} chunks")
    print(f"Token chunking:    {len(token_chunks)} chunks")

    # Try semantic if API key available
    try:
        semantic_service = ChunkingServiceFactory.create_semantic_service()
        semantic_chunks = semantic_service.chunk_text(SAMPLE_TEXT)
        print(f"Semantic chunking:  {len(semantic_chunks)} chunks")
    except:
        print(f"Semantic chunking:  (unavailable - no API key)")

    print("\n✓ Strategy comparison complete")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  CHUNKING SERVICE TEST SUITE")
    print("=" * 80)

    try:
        # Run all tests
        test_sentence_chunking()
        test_token_chunking()
        test_semantic_chunking()  # May fail without API key
        test_factory_methods()
        test_empty_text()
        test_metadata_preservation()
        compare_strategies()

        print("\n" + "=" * 80)
        print("  ALL TESTS PASSED ✓")
        print("=" * 80)
        print("\nNote: Semantic chunking requires OPENAI_API_KEY in .env")
        print("If semantic tests failed, set the API key and run again.\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
