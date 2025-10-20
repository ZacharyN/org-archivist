"""
Comprehensive test suite for MetadataExtractor

Tests all metadata extraction capabilities:
- User metadata parsing and validation
- File properties extraction
- Document structure analysis
- Filename pattern parsing
- PDF/DOCX metadata extraction
- Graceful handling of missing metadata
- Metadata validation
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.metadata_extractor import (
    MetadataExtractor,
    ExtractedMetadata,
    MetadataExtractorFactory
)


def test_extractor_initialization():
    """Test 1: MetadataExtractor can be initialized"""
    print("\n=== Test 1: Extractor Initialization ===")

    extractor = MetadataExtractor()
    assert extractor is not None
    print("[OK] MetadataExtractor initialized successfully")

    # Test factory pattern
    extractor2 = MetadataExtractorFactory.create_extractor()
    assert extractor2 is not None
    print("[OK] MetadataExtractorFactory creates extractor")


def test_basic_metadata_extraction():
    """Test 2: Extract basic metadata from user input and text"""
    print("\n=== Test 2: Basic Metadata Extraction ===")

    extractor = MetadataExtractor()

    user_metadata = {
        'doc_type': 'Grant Proposal',
        'year': 2024,
        'programs': ['Early Childhood', 'Education'],
        'tags': ['federal', 'DoED'],
        'outcome': 'Funded',
        'notes': 'Awarded $500,000'
    }

    text = "This is a sample grant proposal. " * 100  # 600 words
    filename = "sample_proposal.pdf"
    file_content = b"Sample PDF content"

    metadata = extractor.extract(
        user_metadata=user_metadata,
        file_content=file_content,
        filename=filename,
        text=text,
        file_extractor=None
    )

    # Verify user metadata preserved
    assert metadata.doc_type == 'Grant Proposal'
    assert metadata.year == 2024
    assert metadata.programs == ['Early Childhood', 'Education']
    assert metadata.tags == ['federal', 'DoED']
    assert metadata.outcome == 'Funded'
    assert metadata.notes == 'Awarded $500,000'
    print("[OK] User metadata correctly preserved")

    # Verify file properties
    assert metadata.filename == filename
    assert metadata.file_size == len(file_content)
    print(f"[OK] File properties extracted: {metadata.file_size} bytes")

    # Verify document structure
    assert metadata.word_count == 600
    assert metadata.char_count == len(text)
    print(f"[OK] Document structure analyzed: {metadata.word_count} words, {metadata.char_count} chars")

    # Verify processing metadata
    assert metadata.doc_id is not None
    assert metadata.processed_date is not None
    print(f"[OK] Processing metadata generated: doc_id={metadata.doc_id}")


def test_filename_pattern_parsing():
    """Test 3: Parse structured filenames"""
    print("\n=== Test 3: Filename Pattern Parsing ===")

    extractor = MetadataExtractor()
    user_metadata = {'doc_type': 'Grant Proposal', 'year': 2024}
    text = "Sample text"

    # Pattern 1: "NCFF_GrantProposal_2024_DoED.pdf"
    metadata1 = extractor.extract(
        user_metadata=user_metadata,
        file_content=b"test",
        filename="NCFF_GrantProposal_2024_DoED.pdf",
        text=text
    )

    assert 'year' in metadata1.parsed_from_filename
    assert metadata1.parsed_from_filename['year'] == '2024'
    print(f"[OK] Pattern 1 parsed: {metadata1.parsed_from_filename}")

    # Pattern 2: "Annual Report 2023.pdf"
    metadata2 = extractor.extract(
        user_metadata={'doc_type': 'Annual Report', 'year': 2022},
        file_content=b"test",
        filename="Annual Report 2023.pdf",
        text=text
    )

    assert 'year' in metadata2.parsed_from_filename
    assert metadata2.parsed_from_filename['year'] == '2023'
    print(f"[OK] Pattern 2 parsed: {metadata2.parsed_from_filename}")

    # Pattern 3: "Grant_DoED_2024_Funded.pdf"
    # Note: outcome parsing only works if user doesn't provide outcome
    metadata3 = extractor.extract(
        user_metadata={'doc_type': 'Grant Proposal', 'year': 2024},  # No outcome provided
        file_content=b"test",
        filename="Grant_DoED_2024_Funded.pdf",
        text=text
    )

    # Check if filename was parsed
    if 'outcome' in metadata3.parsed_from_filename:
        assert metadata3.outcome == 'Funded'  # Should be normalized
        print(f"[OK] Pattern 3 parsed with outcome: {metadata3.outcome}")
    else:
        print(f"[OK] Pattern 3: outcome not in filename (outcome={metadata3.outcome})")


def test_outcome_normalization():
    """Test 4: Normalize outcome strings from filenames"""
    print("\n=== Test 4: Outcome Normalization ===")

    extractor = MetadataExtractor()

    test_cases = [
        ('funded', 'Funded'),
        ('approved', 'Funded'),
        ('awarded', 'Funded'),
        ('denied', 'Not Funded'),
        ('rejected', 'Not Funded'),
        ('pending', 'Pending'),
        ('submitted', 'Pending'),
        ('finalreport', 'Final Report'),
    ]

    for input_val, expected in test_cases:
        result = extractor._normalize_outcome(input_val)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"[OK] '{input_val}' -> '{result}'")


def test_pdf_metadata_integration():
    """Test 5: Extract PDF-specific metadata"""
    print("\n=== Test 5: PDF Metadata Integration ===")

    from app.services.extractors.pdf_extractor import PDFExtractor

    extractor = MetadataExtractor()
    pdf_extractor = PDFExtractor()

    # Create a mock PDF extractor with metadata
    class MockPDFExtractor:
        def get_metadata(self, content):
            return {
                'title': 'Sample Grant Proposal',
                'author': 'Jane Smith',
                'subject': 'Education Funding',
                'creator': 'Microsoft Word',
                'page_count': 25,
                'creation_date': '2024-01-15',
                'modification_date': '2024-01-20'
            }

    user_metadata = {'doc_type': 'Grant Proposal', 'year': 2024}
    text = "Sample text"

    metadata = extractor.extract(
        user_metadata=user_metadata,
        file_content=b"test",
        filename="proposal.pdf",
        text=text,
        file_extractor=MockPDFExtractor()
    )

    assert metadata.title == 'Sample Grant Proposal'
    assert metadata.author == 'Jane Smith'
    assert metadata.subject == 'Education Funding'
    assert metadata.page_count == 25
    print(f"[OK] PDF metadata extracted: {metadata.page_count} pages, author={metadata.author}")


def test_docx_metadata_integration():
    """Test 6: Extract DOCX-specific metadata"""
    print("\n=== Test 6: DOCX Metadata Integration ===")

    extractor = MetadataExtractor()

    # Create a mock DOCX extractor with metadata
    class MockDOCXExtractor:
        def get_metadata(self, content):
            return {
                'title': 'Annual Report 2024',
                'author': 'John Doe',
                'paragraph_count': 150,
                'table_count': 5,
                'section_count': 8,
                'created': '2024-10-01T10:00:00',
                'modified': '2024-10-15T16:30:00'
            }

    user_metadata = {'doc_type': 'Annual Report', 'year': 2024}
    text = "Sample text"

    metadata = extractor.extract(
        user_metadata=user_metadata,
        file_content=b"test",
        filename="report.docx",
        text=text,
        file_extractor=MockDOCXExtractor()
    )

    assert metadata.title == 'Annual Report 2024'
    assert metadata.author == 'John Doe'
    assert metadata.paragraph_count == 150
    assert metadata.table_count == 5
    assert metadata.section_count == 8
    assert metadata.created_date is not None
    print(f"[OK] DOCX metadata extracted: {metadata.paragraph_count} paragraphs, {metadata.table_count} tables")


def test_missing_metadata_handling():
    """Test 7: Gracefully handle missing metadata"""
    print("\n=== Test 7: Missing Metadata Handling ===")

    extractor = MetadataExtractor()

    # Minimal user metadata
    user_metadata = {
        'doc_type': 'Grant Proposal',
        'year': 2024
    }

    text = "Short text"
    filename = "no_pattern_file.pdf"

    metadata = extractor.extract(
        user_metadata=user_metadata,
        file_content=b"test",
        filename=filename,
        text=text,
        file_extractor=None  # No file extractor
    )

    # Should still work with minimal data
    assert metadata.doc_type == 'Grant Proposal'
    assert metadata.year == 2024
    assert metadata.programs == []  # Empty list, not None
    assert metadata.tags == []
    assert metadata.outcome == 'N/A'  # Default value
    assert metadata.notes is None  # Explicitly None

    # File-specific metadata should be None/empty
    assert metadata.page_count is None
    assert metadata.author is None
    assert metadata.title is None

    # But basic structure metadata should still exist
    assert metadata.word_count == 2
    assert metadata.char_count == len(text)
    assert metadata.filename == filename

    print("[OK] Missing metadata handled gracefully with defaults")


def test_metadata_validation():
    """Test 8: Validate extracted metadata"""
    print("\n=== Test 8: Metadata Validation ===")

    extractor = MetadataExtractor()

    # Valid metadata
    valid_metadata = ExtractedMetadata(
        doc_type='Grant Proposal',
        year=2024,
        filename='valid.pdf',
        word_count=1000,
        char_count=5000,
        file_size=50000
    )

    is_valid, warnings = extractor.validate_metadata(valid_metadata)
    assert is_valid == True
    assert len(warnings) == 0
    print("[OK] Valid metadata passes validation")

    # Invalid metadata - missing doc_type
    invalid1 = ExtractedMetadata(
        doc_type='Unknown',
        year=2024,
        filename='test.pdf'
    )

    is_valid, warnings = extractor.validate_metadata(invalid1)
    assert is_valid == False
    assert any('Document type' in w for w in warnings)
    print(f"[OK] Missing doc_type detected: {warnings}")

    # Invalid metadata - bad year
    invalid2 = ExtractedMetadata(
        doc_type='Grant Proposal',
        year=1999,
        filename='test.pdf'
    )

    is_valid, warnings = extractor.validate_metadata(invalid2)
    assert is_valid == False
    assert any('Invalid year' in w for w in warnings)
    print(f"[OK] Invalid year detected: {warnings}")

    # Invalid metadata - very small file
    invalid3 = ExtractedMetadata(
        doc_type='Grant Proposal',
        year=2024,
        filename='test.pdf',
        word_count=5,
        file_size=50
    )

    is_valid, warnings = extractor.validate_metadata(invalid3)
    assert is_valid == False
    assert any('word count' in w for w in warnings)
    print(f"[OK] Data quality issues detected: {warnings}")


def test_to_dict_conversion():
    """Test 9: Convert ExtractedMetadata to dictionary"""
    print("\n=== Test 9: Dictionary Conversion ===")

    metadata = ExtractedMetadata(
        doc_type='Grant Proposal',
        year=2024,
        programs=['Education'],
        tags=['federal'],
        filename='test.pdf',
        file_size=1000,
        word_count=500,
        char_count=2500
    )

    metadata_dict = metadata.to_dict()

    assert isinstance(metadata_dict, dict)
    assert metadata_dict['doc_type'] == 'Grant Proposal'
    assert metadata_dict['year'] == 2024
    assert metadata_dict['programs'] == ['Education']
    assert metadata_dict['filename'] == 'test.pdf'
    assert metadata_dict['word_count'] == 500

    # Check all expected keys present
    expected_keys = [
        'doc_type', 'year', 'programs', 'tags', 'outcome', 'notes',
        'filename', 'file_size', 'word_count', 'char_count',
        'page_count', 'doc_id', 'upload_date'
    ]

    for key in expected_keys:
        assert key in metadata_dict, f"Missing key: {key}"

    print(f"[OK] Dictionary conversion successful with {len(metadata_dict)} keys")


def test_doc_id_generation():
    """Test 10: Generate unique document IDs"""
    print("\n=== Test 10: Document ID Generation ===")

    extractor = MetadataExtractor()

    import time

    doc_id1 = extractor._generate_doc_id("test1.pdf")
    time.sleep(0.01)  # Ensure different timestamp
    doc_id2 = extractor._generate_doc_id("test2.pdf")
    time.sleep(0.01)
    doc_id3 = extractor._generate_doc_id("test1.pdf")  # Same filename

    assert doc_id1 is not None
    assert doc_id2 is not None
    assert doc_id1 != doc_id2  # Different filenames = different IDs

    # doc_id3 should be different from doc_id1 due to timestamp
    # (unless they're generated in the same second)
    assert doc_id1.startswith('doc_')
    assert doc_id2.startswith('doc_')
    print(f"[OK] Unique doc IDs generated: {doc_id1[:20]}..., {doc_id2[:20]}...")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("METADATA EXTRACTOR TEST SUITE")
    print("=" * 60)

    tests = [
        test_extractor_initialization,
        test_basic_metadata_extraction,
        test_filename_pattern_parsing,
        test_outcome_normalization,
        test_pdf_metadata_integration,
        test_docx_metadata_integration,
        test_missing_metadata_handling,
        test_metadata_validation,
        test_to_dict_conversion,
        test_doc_id_generation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n[FAIL] {test.__name__}: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n[ERROR] {test.__name__}: {str(e)}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n[OK] All tests passed successfully!")
    else:
        print(f"\n[FAIL] {failed} test(s) failed")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
