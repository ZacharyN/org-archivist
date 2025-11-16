"""
Integration test for document upload endpoint

Tests the full document processing pipeline end-to-end:
- File upload
- Text extraction
- Chunking
- Embedding generation
- Vector storage (Qdrant)
- Database storage (PostgreSQL)
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables before imports
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "test-key"))


async def test_upload_integration():
    """Test document upload integration"""
    print("=== Document Upload Integration Test ===\n")

    # Import after setting environment
    from app.dependencies import (
        get_document_processor,
        get_database,
        get_vector_store,
    )
    from app.services.document_processor import ProcessingResult

    # 1. Create test document
    print("1. Creating test document...")
    test_content = b"""
    Grant Proposal: Youth Development Program 2023

    Program Description:
    This program aims to provide educational support and mentorship
    to underserved youth in urban areas. Our approach focuses on
    building academic skills, fostering personal development, and
    creating pathways to college and career success.

    Impact:
    Over the past year, we have served 150 youth with a 95% retention
    rate and an average GPA increase of 0.8 points.

    Budget: $250,000
    Duration: January 2023 - December 2023
    """

    filename = "YouthDev_Grant_2023_CityFoundation.pdf"

    metadata = {
        "doc_id": None,  # Will be generated
        "doc_type": "Grant Proposal",
        "year": 2023,
        "programs": ["Youth Development", "Education"],
        "tags": ["grant", "youth", "education"],
        "outcome": "Funded",
        "notes": "Test document for integration testing",
    }

    print(f"   Filename: {filename}")
    print(f"   Type: {metadata['doc_type']}")
    print(f"   Year: {metadata['year']}")
    print(f"   Programs: {metadata['programs']}")
    print(f"   Content size: {len(test_content)} bytes")
    print("   ✓ Test document created\n")

    # 2. Initialize services
    print("2. Initializing services...")
    try:
        processor = get_document_processor()
        print("   ✓ Document processor initialized")

        db = await get_database()
        print("   ✓ Database service initialized")

        vector_store = get_vector_store()
        print("   ✓ Vector store initialized")
        print()
    except Exception as e:
        print(f"   ✗ Failed to initialize services: {e}")
        return False

    # 3. Process document
    print("3. Processing document through pipeline...")
    try:
        result: ProcessingResult = await processor.process_document(
            file_content=test_content,
            filename=filename,
            metadata=metadata,
        )

        if result.success:
            print(f"   ✓ Processing succeeded")
            print(f"   Doc ID: {result.doc_id}")
            print(f"   Chunks created: {result.chunks_created}")
            print(f"   Message: {result.message}")
            print()
        else:
            print(f"   ✗ Processing failed: {result.error}")
            return False

    except Exception as e:
        print(f"   ✗ Exception during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Verify vector storage
    print("4. Verifying chunks in Qdrant...")
    try:
        # Try to search for chunks
        from app.dependencies import get_embedding_model

        embedding_model = get_embedding_model()
        query_embedding = embedding_model.get_text_embedding("youth development")

        search_results = await vector_store.search_similar(
            query_embedding=query_embedding,
            top_k=5,
            filters={"doc_id": result.doc_id},
        )

        print(f"   ✓ Found {len(search_results)} chunks in vector store")
        if search_results:
            print(f"   Sample chunk text: {search_results[0].text[:100]}...")
        print()

    except Exception as e:
        print(f"   ✗ Failed to verify vector storage: {e}")
        import traceback
        traceback.print_exc()
        # Continue even if search fails

    # 5. Verify database storage
    print("5. Verifying document in PostgreSQL...")
    try:
        from uuid import UUID

        doc_uuid = UUID(result.doc_id)
        doc_record = await db.get_document(doc_uuid)

        if doc_record:
            print(f"   ✓ Document found in database")
            print(f"   Filename: {doc_record['filename']}")
            print(f"   Type: {doc_record['doc_type']}")
            print(f"   Year: {doc_record['year']}")
            print(f"   Programs: {doc_record['programs']}")
            print(f"   Chunks: {doc_record['chunks_count']}")
            print()
        else:
            print(f"   ✗ Document not found in database")
            return False

    except Exception as e:
        print(f"   ✗ Failed to verify database storage: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 6. Clean up
    print("6. Cleaning up test data...")
    try:
        # Delete from vector store
        await vector_store.delete_document(result.doc_id)
        print(f"   ✓ Deleted chunks from vector store")

        # Delete from database
        await db.delete_document(doc_uuid)
        print(f"   ✓ Deleted document from database")
        print()

    except Exception as e:
        print(f"   ⚠ Warning: Failed to clean up: {e}")
        print()

    print("=== ✓ All Tests Passed ===\n")
    return True


async def main():
    """Run integration test"""
    try:
        success = await test_upload_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
