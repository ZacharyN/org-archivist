"""
Simple test script to verify embedding generation works correctly

This script tests the _generate_embeddings method in DocumentProcessor
with mock embedding models to ensure the implementation is correct.
"""

import asyncio
from typing import List
from app.services.document_processor import DocumentProcessor, DocumentChunk


class MockEmbeddingModel:
    """Mock embedding model for testing"""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions
        self.call_count = 0

    def get_text_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings"""
        self.call_count += 1
        # Return mock embeddings (list of floats with correct dimensions)
        return [[0.1] * self.dimensions for _ in texts]


async def test_embedding_generation():
    """Test that embeddings are generated and assigned correctly"""

    print("Test 1: Basic embedding generation")
    print("-" * 60)

    # Create mock embedding model
    mock_model = MockEmbeddingModel(dimensions=1536)

    # Create processor with mock model
    processor = DocumentProcessor(
        vector_store=None,
        embedding_model=mock_model,
        chunking_service=None
    )

    # Create test chunks
    chunks = [
        DocumentChunk(
            chunk_id="chunk_1",
            text="This is test chunk 1",
            chunk_index=0,
            metadata={"doc_id": "test_doc"},
            embedding=None
        ),
        DocumentChunk(
            chunk_id="chunk_2",
            text="This is test chunk 2",
            chunk_index=1,
            metadata={"doc_id": "test_doc"},
            embedding=None
        ),
        DocumentChunk(
            chunk_id="chunk_3",
            text="This is test chunk 3",
            chunk_index=2,
            metadata={"doc_id": "test_doc"},
            embedding=None
        )
    ]

    # Verify all chunks start with None embeddings
    assert all(chunk.embedding is None for chunk in chunks), "Chunks should start with None embeddings"
    print("[OK] All chunks initialized with None embeddings")

    # Generate embeddings
    await processor._generate_embeddings(chunks)

    # Verify embeddings were generated
    assert all(chunk.embedding is not None for chunk in chunks), "All chunks should have embeddings"
    print("[OK] All chunks now have embeddings")

    # Verify embedding dimensions
    assert all(len(chunk.embedding) == 1536 for chunk in chunks), "Embeddings should have correct dimensions"
    print("[OK] All embeddings have correct dimensions (1536)")

    # Verify batch processing was used (should be called once for all chunks)
    assert mock_model.call_count == 1, "Should use batch processing (single call)"
    print("[OK] Batch processing used (single API call for all chunks)")

    print(f"\n[PASS] Test 1: Generated {len(chunks)} embeddings successfully\n")


async def test_empty_chunks():
    """Test handling of empty chunk list"""

    print("Test 2: Empty chunk list handling")
    print("-" * 60)

    mock_model = MockEmbeddingModel()
    processor = DocumentProcessor(
        vector_store=None,
        embedding_model=mock_model,
        chunking_service=None
    )

    chunks = []
    await processor._generate_embeddings(chunks)

    assert mock_model.call_count == 0, "Should not call model for empty chunks"
    print("[OK] Empty chunk list handled correctly (no API calls)")
    print("[PASS] Test 2\n")


async def test_no_embedding_model():
    """Test handling when no embedding model is available"""

    print("Test 3: No embedding model available")
    print("-" * 60)

    processor = DocumentProcessor(
        vector_store=None,
        embedding_model=None,  # No model
        chunking_service=None
    )

    chunks = [
        DocumentChunk(
            chunk_id="chunk_1",
            text="Test chunk",
            chunk_index=0,
            metadata={},
            embedding=None
        )
    ]

    # Should not raise an error
    await processor._generate_embeddings(chunks)

    # Embeddings should still be None
    assert chunks[0].embedding is None, "Embedding should remain None when no model"
    print("[OK] Gracefully handles missing embedding model")
    print("[PASS] Test 3\n")


async def test_error_handling():
    """Test error handling when embedding generation fails"""

    print("Test 4: Error handling during embedding generation")
    print("-" * 60)

    class FailingEmbeddingModel:
        """Mock model that always fails"""

        def get_text_embedding_batch(self, texts: List[str]) -> List[List[float]]:
            raise Exception("API error: Rate limit exceeded")

    failing_model = FailingEmbeddingModel()
    processor = DocumentProcessor(
        vector_store=None,
        embedding_model=failing_model,
        chunking_service=None
    )

    chunks = [
        DocumentChunk(
            chunk_id="chunk_1",
            text="Test chunk",
            chunk_index=0,
            metadata={},
            embedding=None
        )
    ]

    # Should not raise an error (graceful degradation)
    await processor._generate_embeddings(chunks)

    # Embeddings should still be None (fallback behavior)
    assert chunks[0].embedding is None, "Embedding should remain None on error"
    print("[OK] Gracefully handles API errors")
    print("[PASS] Test 4\n")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Testing Embedding Generation Implementation")
    print("=" * 60 + "\n")

    try:
        await test_embedding_generation()
        await test_empty_chunks()
        await test_no_embedding_model()
        await test_error_handling()

        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        print("\nEmbedding generation is working correctly!")
        print("- Batch processing implemented")
        print("- Error handling in place")
        print("- Graceful degradation supported")
        print("\nReady for integration with real embedding models.")

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
