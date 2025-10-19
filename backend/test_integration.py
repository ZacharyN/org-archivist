"""
Integration test to verify document processor works with all extractors
"""

import io
import sys
import asyncio
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.document_processor import DocumentProcessor, FileType, ProcessorFactory
from app.services.extractors.pdf_extractor import PDFExtractor
from app.services.extractors.docx_extractor import DOCXExtractor
from app.services.extractors.txt_extractor import TXTExtractor


async def test_integration():
    """Test DocumentProcessor with all three extractors registered"""

    print("\n" + "="*60)
    print("Testing Document Processor Integration")
    print("="*60 + "\n")

    # Create processor (with None for dependencies that aren't implemented yet)
    processor = ProcessorFactory.create_processor(
        vector_store=None,
        embedding_model=None,
        node_parser=None
    )

    # Register all extractors
    processor.register_extractor(FileType.PDF, PDFExtractor())
    processor.register_extractor(FileType.DOCX, DOCXExtractor())
    processor.register_extractor(FileType.TXT, TXTExtractor())

    print("[OK] Registered all three extractors")

    # Test 1: Create simple text file
    txt_content = "Test document for integration testing.\n\nThis is a simple text file.".encode('utf-8')

    metadata = {
        'doc_id': 'test-001',
        'doc_type': 'Test',
        'year': 2024,
        'programs': ['Testing'],
        'outcomes': ['Integration'],
    }

    print("\n--- Testing TXT file processing ---")
    result = await processor.process_document(
        file_content=txt_content,
        filename='test.txt',
        metadata=metadata
    )

    print(f"Success: {result.success}")
    print(f"Doc ID: {result.doc_id}")
    print(f"Chunks created: {result.chunks_created}")
    print(f"Message: {result.message}")
    if result.error:
        print(f"Error: {result.error}")

    if result.success and result.chunks_created > 0:
        print("[OK] TXT file processed successfully")
    else:
        print("[FAIL] TXT file processing failed")

    # Test 2: Test file type detection
    print("\n--- Testing file type detection ---")

    test_files = [
        ('document.pdf', FileType.PDF),
        ('report.docx', FileType.DOCX),
        ('notes.txt', FileType.TXT),
        ('data.TXT', FileType.TXT),  # Test case insensitivity
    ]

    for filename, expected_type in test_files:
        try:
            detected_type = processor._get_file_type(filename)
            if detected_type == expected_type:
                print(f"[OK] {filename} -> {detected_type.value}")
            else:
                print(f"[FAIL] {filename} -> expected {expected_type.value}, got {detected_type.value}")
        except ValueError as e:
            print(f"[FAIL] {filename} -> {str(e)}")

    # Test 3: Test unsupported file type
    print("\n--- Testing unsupported file type ---")
    try:
        processor._get_file_type('document.xlsx')
        print("[FAIL] Should have raised ValueError for unsupported type")
    except ValueError as e:
        print(f"[OK] Correctly rejected unsupported file: {str(e)[:60]}...")

    # Test 4: Test extractor retrieval
    print("\n--- Testing extractor retrieval ---")

    for file_type in FileType:
        try:
            extractor = processor._get_extractor(file_type)
            extractor_name = type(extractor).__name__
            print(f"[OK] {file_type.value} -> {extractor_name}")
        except ValueError as e:
            print(f"[FAIL] {file_type.value} -> {str(e)}")

    print("\n" + "="*60)
    print("Integration Test Complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_integration())
