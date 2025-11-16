"""
Test script for QdrantStore vector store service

Tests:
1. Connection to Qdrant
2. Collection creation
3. Storing chunks with embeddings
4. Searching similar chunks
5. Deleting documents
6. Health check
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set mock mode to bypass API key validation for this test
os.environ["MOCK_MODE"] = "true"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key-for-vector-store-testing"

from app.services.vector_store import QdrantStore, VectorStoreConfig, VectorStoreFactory


async def test_vector_store():
    """Test all QdrantStore functionality"""

    print("\n" + "="*60)
    print("Testing QdrantStore Service")
    print("="*60)

    # Test 1: Create store and connection
    print("\n[Test 1] Creating QdrantStore...")
    try:
        # Use localhost for testing from host machine
        config = VectorStoreConfig(
            host="localhost",
            port=6333,
            grpc_port=6334,
            collection_name="test_collection",
            vector_size=1024,
            prefer_grpc=False  # Use HTTP for simplicity in testing
        )
        store = VectorStoreFactory.create_store(config)
        print("[OK] QdrantStore created successfully")
        print(f"  - Host: {store.config.host}:{store.config.port}")
        print(f"  - Collection: {store.config.collection_name}")
        print(f"  - Vector size: {store.config.vector_size}")
    except Exception as e:
        print(f"[FAIL] Failed to create store: {e}")
        return

    # Test 2: Health check
    print("\n[Test 2] Running health check...")
    try:
        health = store.health_check()
        print(f"[OK] Health check complete")
        print(f"  - Healthy: {health['healthy']}")
        print(f"  - Connected: {health['connected']}")
        print(f"  - Collection exists: {health['collection_exists']}")
        print(f"  - Message: {health['message']}")
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")

    # Test 3: Ensure collection exists
    print("\n[Test 3] Ensuring collection exists...")
    try:
        exists = store.ensure_collection_exists()
        print(f"[OK] Collection ready: {exists}")
    except Exception as e:
        print(f"[FAIL] Collection creation failed: {e}")
        return

    # Test 4: Store sample chunks
    print("\n[Test 4] Storing sample chunks...")
    try:
        # Create sample chunks with embeddings
        # Using vector_size from config (should be 1024 for bge-large-en-v1.5)
        sample_chunks = [
            {
                "chunk_id": "test-doc-1-chunk-0",
                "text": "This is a sample document about grant writing for nonprofit organizations.",
                "embedding": [0.1] * store.config.vector_size,  # Dummy embedding
                "metadata": {
                    "doc_id": "test-doc-1",
                    "chunk_index": 0,
                    "doc_type": "grant",
                    "year": 2023,
                    "program": "Education",
                }
            },
            {
                "chunk_id": "test-doc-1-chunk-1",
                "text": "Grant proposals should clearly articulate the problem and proposed solution.",
                "embedding": [0.2] * store.config.vector_size,
                "metadata": {
                    "doc_id": "test-doc-1",
                    "chunk_index": 1,
                    "doc_type": "grant",
                    "year": 2023,
                    "program": "Education",
                }
            },
            {
                "chunk_id": "test-doc-2-chunk-0",
                "text": "Federal RFP responses require detailed budget justifications.",
                "embedding": [0.3] * store.config.vector_size,
                "metadata": {
                    "doc_id": "test-doc-2",
                    "chunk_index": 0,
                    "doc_type": "rfp",
                    "year": 2024,
                    "program": "Infrastructure",
                }
            },
        ]

        result = await store.store_chunks(sample_chunks)
        print(f"[OK] Chunks stored")
        print(f"  - Success: {result['success']}")
        print(f"  - Chunks stored: {result['chunks_stored']}")
        print(f"  - Collection: {result['collection']}")
    except Exception as e:
        print(f"[FAIL] Failed to store chunks: {e}")
        return

    # Test 5: Get collection info
    print("\n[Test 5] Getting collection info...")
    try:
        info = store.get_collection_info()
        print(f"[OK] Collection info retrieved")
        print(f"  - Name: {info['name']}")
        print(f"  - Points count: {info['points_count']}")
        print(f"  - Vectors count: {info['vectors_count']}")
        print(f"  - Status: {info['status']}")
    except Exception as e:
        print(f"[FAIL] Failed to get collection info: {e}")

    # Test 6: Search similar chunks
    print("\n[Test 6] Searching for similar chunks...")
    try:
        # Use a query vector similar to our first chunk
        query_vector = [0.15] * store.config.vector_size

        results = await store.search_similar(
            query_vector=query_vector,
            limit=3,
            score_threshold=0.0  # Accept all scores for testing
        )

        print(f"[OK] Search completed")
        print(f"  - Results found: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    - ID: {result['id']}")
            print(f"    - Score: {result['score']:.4f}")
            print(f"    - Text: {result['text'][:60]}...")
            print(f"    - Metadata: {result['metadata']}")
    except Exception as e:
        print(f"[FAIL] Search failed: {e}")

    # Test 7: Search with filters
    print("\n[Test 7] Searching with metadata filters...")
    try:
        results = await store.search_similar(
            query_vector=query_vector,
            limit=5,
            filter_conditions={"doc_type": "grant"}
        )

        print(f"[OK] Filtered search completed")
        print(f"  - Results found: {len(results)}")
        print(f"  - All results have doc_type='grant': {all(r['metadata'].get('doc_type') == 'grant' for r in results)}")
    except Exception as e:
        print(f"[FAIL] Filtered search failed: {e}")

    # Test 8: Delete document
    print("\n[Test 8] Deleting test document...")
    try:
        delete_result = await store.delete_document("test-doc-1")
        print(f"[OK] Document deleted")
        print(f"  - Success: {delete_result['success']}")
        print(f"  - Doc ID: {delete_result['doc_id']}")
        print(f"  - Message: {delete_result['message']}")
    except Exception as e:
        print(f"[FAIL] Delete failed: {e}")

    # Test 9: Verify deletion
    print("\n[Test 9] Verifying deletion...")
    try:
        results = await store.search_similar(
            query_vector=query_vector,
            limit=10,
            filter_conditions={"doc_id": "test-doc-1"}
        )

        print(f"[OK] Verification complete")
        print(f"  - Results with deleted doc_id: {len(results)}")
        print(f"  - Expected: 0")
        if len(results) == 0:
            print("  [OK] Deletion verified!")
        else:
            print("  [WARN] Some chunks still exist")
    except Exception as e:
        print(f"[FAIL] Verification failed: {e}")

    # Cleanup: Delete remaining test document
    print("\n[Cleanup] Removing remaining test data...")
    try:
        await store.delete_document("test-doc-2")
        print("[OK] Cleanup complete")
    except Exception as e:
        print(f"[WARN] Cleanup had issues: {e}")

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run async tests
    asyncio.run(test_vector_store())
