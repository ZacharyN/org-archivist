"""
Simple test for ChunkingService without requiring API keys

Tests sentence and token chunking strategies.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.chunking_service import (
    ChunkingService,
    ChunkingConfig,
    ChunkingStrategy,
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


def main():
    print("=" * 80)
    print("  CHUNKING SERVICE - SIMPLE TEST")
    print("=" * 80)

    # Test 1: Sentence chunking
    print("\n[TEST 1] Sentence-based chunking")
    print("-" * 80)

    config = ChunkingConfig(
        strategy=ChunkingStrategy.SENTENCE,
        chunk_size=200,
        chunk_overlap=20
    )

    service = ChunkingService(config)
    chunks = service.chunk_text(
        SAMPLE_TEXT,
        metadata={'doc_id': 'test-001', 'doc_type': 'sample'}
    )

    print(f"Created {len(chunks)} chunks using sentence strategy")
    print(f"\nFirst chunk preview:")
    print(f"  Length: {chunks[0]['char_count']} chars")
    print(f"  Text: {chunks[0]['text'][:150]}...")
    print(f"  Metadata: {chunks[0]['metadata']['chunking_strategy']}")

    assert len(chunks) > 0
    assert all('text' in c for c in chunks)
    print("[OK] Sentence chunking test PASSED")

    # Test 2: Token chunking
    print("\n[TEST 2] Token-based chunking")
    print("-" * 80)

    config2 = ChunkingConfig(
        strategy=ChunkingStrategy.TOKEN,
        chunk_size=100,
        chunk_overlap=10
    )

    service2 = ChunkingService(config2)
    chunks2 = service2.chunk_text(
        SAMPLE_TEXT,
        metadata={'doc_id': 'test-002', 'doc_type': 'sample'}
    )

    print(f"Created {len(chunks2)} chunks using token strategy")
    print(f"\nFirst chunk preview:")
    print(f"  Length: {chunks2[0]['char_count']} chars")
    print(f"  Text: {chunks2[0]['text'][:150]}...")
    print(f"  Metadata: {chunks2[0]['metadata']['chunking_strategy']}")

    assert len(chunks2) > 0
    print("[OK] Token chunking test PASSED")

    # Test 3: Edge cases
    print("\n[TEST 3] Edge cases")
    print("-" * 80)

    service3 = ChunkingService(ChunkingConfig(strategy=ChunkingStrategy.SENTENCE))

    # Empty text
    empty_chunks = service3.chunk_text("")
    assert len(empty_chunks) == 0
    print("[OK] Empty text handled correctly")

    # Short text
    short_chunks = service3.chunk_text("Short text.")
    assert len(short_chunks) >= 1
    print(f"[OK] Short text created {len(short_chunks)} chunk(s)")

    # Test 4: Metadata preservation
    print("\n[TEST 4] Metadata preservation")
    print("-" * 80)

    metadata = {
        'doc_id': 'meta-test',
        'doc_type': 'proposal',
        'year': 2024,
        'program': 'Education',
    }

    meta_chunks = service3.chunk_text(SAMPLE_TEXT[:200], metadata=metadata)

    # Check metadata is preserved
    for chunk in meta_chunks:
        assert chunk['metadata']['doc_id'] == 'meta-test'
        assert chunk['metadata']['doc_type'] == 'proposal'
        assert chunk['metadata']['year'] == 2024
        assert 'chunking_strategy' in chunk['metadata']

    print(f"[OK] Metadata preserved across {len(meta_chunks)} chunks")

    # Summary
    print("\n" + "=" * 80)
    print("  ALL TESTS PASSED [OK]")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Sentence chunking: {len(chunks)} chunks")
    print(f"  - Token chunking: {len(chunks2)} chunks")
    print(f"  - Edge cases: handled correctly")
    print(f"  - Metadata: preserved correctly")
    print(f"\n[OK] ChunkingService is working correctly!")
    print("\nNote: Semantic chunking requires OPENAI_API_KEY and was not tested here.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
