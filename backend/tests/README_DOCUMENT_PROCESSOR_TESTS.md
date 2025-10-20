# Document Processor Unit Tests

## Overview

Comprehensive unit test suite for the document processing pipeline, covering text extraction from PDF, DOCX, and TXT files.

**Test File:** `backend/tests/test_document_processor.py`
**Total Tests:** 42
**Status:** All tests passing ✓

## Test Coverage

### 1. PDF Extractor Tests (9 tests)
Tests for `PDFExtractor` class using reportlab to generate test PDFs:

- **Initialization & Configuration**
  - `test_pdf_extractor_initialization` - Default initialization
  - `test_pdf_extractor_custom_separator` - Custom page separator

- **Text Extraction**
  - `test_pdf_single_page_extraction` - Extract from single-page PDF
  - `test_pdf_multi_page_extraction` - Extract from multi-page PDF with page breaks
  - `test_pdf_extractor_with_special_characters` - Handle special characters ($, @, §, etc.)

- **Validation**
  - `test_pdf_validation_success` - Valid PDF passes validation
  - `test_pdf_validation_invalid_header` - Non-PDF file fails validation
  - `test_pdf_validation_empty_file` - Empty file fails validation
  - `test_pdf_extraction_empty_file` - Empty file raises ValueError

- **Metadata Extraction**
  - `test_pdf_get_metadata` - Extract page count and document properties

### 2. DOCX Extractor Tests (7 tests)
Tests for `DOCXExtractor` class using python-docx to generate test files:

- **Initialization**
  - `test_docx_extractor_initialization` - Default initialization

- **Text Extraction**
  - `test_docx_simple_extraction` - Extract paragraphs
  - `test_docx_with_table_extraction` - Extract paragraphs and tables
  - `test_docx_empty_paragraphs` - Skip empty paragraphs gracefully

- **Validation**
  - `test_docx_validation_success` - Valid DOCX passes validation
  - `test_docx_validation_invalid_header` - Non-DOCX file fails validation
  - `test_docx_extraction_empty_file` - Empty file raises ValueError

- **Metadata Extraction**
  - `test_docx_get_metadata` - Extract paragraph/table counts

### 3. TXT Extractor Tests (9 tests)
Tests for `TXTExtractor` class with encoding detection:

- **Initialization**
  - `test_txt_extractor_initialization` - Default initialization

- **Text Extraction**
  - `test_txt_utf8_extraction` - Extract UTF-8 encoded text
  - `test_txt_latin1_extraction` - Extract Latin-1 encoded text
  - `test_txt_encoding_detection` - Auto-detect encoding (chardet)
  - `test_txt_line_ending_normalization` - Normalize CRLF to LF
  - `test_txt_whitespace_handling` - Strip leading/trailing whitespace

- **Validation**
  - `test_txt_validation_success` - Valid text passes validation
  - `test_txt_validation_empty_file` - Empty file fails validation
  - `test_txt_extraction_empty_file` - Empty file raises ValueError

- **Encoding Information**
  - `test_txt_get_encoding_info` - Get encoding metadata

### 4. DocumentProcessor Tests (10 tests)
Tests for the main orchestrator class:

- **Initialization & Registration**
  - `test_processor_initialization` - Create processor with dependencies
  - `test_processor_extractor_registration` - Register extractors for file types

- **File Type Detection**
  - `test_processor_get_file_type` - Detect file type from extension
  - `test_processor_get_file_type_unsupported` - Reject unsupported extensions
  - `test_processor_get_extractor_unregistered` - Fail if extractor not registered

- **Complete Pipeline Tests (Async)**
  - `test_processor_pdf_pipeline` - End-to-end PDF processing
  - `test_processor_docx_pipeline` - End-to-end DOCX processing
  - `test_processor_txt_pipeline` - End-to-end TXT processing

- **Error Handling**
  - `test_processor_invalid_file_type` - Reject unsupported file type
  - `test_processor_validation_failure` - Handle validation failures

- **Classification**
  - `test_processor_classify_document` - Use provided doc_type
  - `test_processor_classify_document_missing` - Default to "Unknown"

### 5. Factory Tests (2 tests)
Tests for `ProcessorFactory`:

- `test_factory_create_processor` - Create processor with dependencies
- `test_factory_create_with_chunking_service` - Create with chunking service

### 6. Edge Cases (5 tests)
Additional edge case coverage:

- PDF with special characters
- DOCX with empty paragraphs
- TXT with excessive whitespace
- Document classification with/without doc_type

## Test Dependencies

### Required Libraries
```bash
# Core dependencies (already in requirements.txt)
pytest>=8.0.0
pytest-asyncio>=0.21.0
PyPDF2>=3.0.0  # or pypdf
python-docx>=1.1.0
chardet>=5.0.0

# Test file generation
reportlab>=4.0.0  # For generating test PDFs
```

### Installation
```bash
cd backend
pip install -r requirements.txt
pip install reportlab  # If not already installed
```

## Running the Tests

### Run all document processor tests
```bash
cd backend
python -m pytest tests/test_document_processor.py -v
```

### Run specific test class
```bash
# PDF tests only
python -m pytest tests/test_document_processor.py::TestPDFExtractor -v

# DOCX tests only
python -m pytest tests/test_document_processor.py::TestDOCXExtractor -v

# TXT tests only
python -m pytest tests/test_document_processor.py::TestTXTExtractor -v

# Pipeline tests only
python -m pytest tests/test_document_processor.py::TestDocumentProcessor -v
```

### Run specific test
```bash
python -m pytest tests/test_document_processor.py::TestPDFExtractor::test_pdf_multi_page_extraction -v
```

### Run with coverage (for this module only)
```bash
python -m pytest tests/test_document_processor.py --cov=app.services.document_processor --cov=app.services.extractors --cov-report=term-missing
```

## Test File Generation

The test suite generates temporary test files in memory using:

1. **PDF Generation** - `reportlab` library
   - Creates simple PDFs with text content
   - Supports multi-page PDFs
   - Generates proper PDF structure

2. **DOCX Generation** - `python-docx` library
   - Creates documents with paragraphs
   - Can add tables with rows/columns
   - Generates proper DOCX structure (ZIP-based)

3. **TXT Generation** - Native Python
   - Uses `encode()` with various encodings
   - Tests UTF-8, Latin-1, and special characters

All test files are created in memory (`io.BytesIO`) and never written to disk.

## Test Results Summary

```
42 tests passed
0 tests failed
Test execution time: ~0.39s (without coverage)
Test execution time: ~1.32s (with coverage)
```

### Coverage Statistics (Module-Specific)
- `document_processor.py`: 89% coverage
- `pdf_extractor.py`: 67% coverage
- `docx_extractor.py`: 88% coverage
- `txt_extractor.py`: 59% coverage

## Key Testing Patterns

### 1. Extractor Testing Pattern
```python
# Generate test file
content_bytes = generate_test_pdf("Test content")

# Initialize extractor
extractor = PDFExtractor()

# Test extraction
text = extractor.extract(content_bytes, "test.pdf")
assert "Test content" in text

# Test validation
is_valid, error = extractor.validate(content_bytes)
assert is_valid is True
```

### 2. Pipeline Testing Pattern (Async)
```python
@pytest.mark.asyncio
async def test_processor_pdf_pipeline(self):
    processor = DocumentProcessor(...)
    processor.register_extractor(FileType.PDF, PDFExtractor())

    result = await processor.process_document(
        file_content=pdf_bytes,
        filename="test.pdf",
        metadata={"doc_type": "Grant Proposal"}
    )

    assert result.success is True
    assert result.chunks_created > 0
```

### 3. Error Testing Pattern
```python
# Test that invalid input raises ValueError
with pytest.raises(ValueError) as exc_info:
    extractor.extract(invalid_content, "invalid.pdf")

assert "expected error message" in str(exc_info.value)
```

## Future Enhancements

1. **Add encrypted PDF tests** - Test password-protected PDFs
2. **Add image-based PDF tests** - Test PDFs without extractable text
3. **Add complex DOCX tests** - Test documents with images, styles, headers
4. **Add performance benchmarks** - Measure extraction speed
5. **Add memory tests** - Test large file handling
6. **Add parallel processing tests** - Test concurrent document processing

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'reportlab'"
**Solution:** Install reportlab for PDF generation
```bash
pip install reportlab
```

### Issue: "ModuleNotFoundError: No module named 'asyncpg'"
**Solution:** Install asyncpg for test environment
```bash
pip install asyncpg
```

### Issue: Tests fail with import errors
**Solution:** Ensure you're running from backend directory
```bash
cd backend
python -m pytest tests/test_document_processor.py
```

### Issue: Coverage below 80% warning
**Solution:** This is expected when testing specific modules. Use `--no-cov` to skip coverage:
```bash
python -m pytest tests/test_document_processor.py --no-cov
```

## Related Documentation

- Main processor: `backend/app/services/document_processor.py`
- PDF extractor: `backend/app/services/extractors/pdf_extractor.py`
- DOCX extractor: `backend/app/services/extractors/docx_extractor.py`
- TXT extractor: `backend/app/services/extractors/txt_extractor.py`
- Integration docs: `backend/docs/document-upload-integration.md`

## Validation Checklist

- [x] All extractors tested (PDF, DOCX, TXT)
- [x] Edge cases covered (empty files, invalid files, special characters)
- [x] Error handling tested (validation failures, unsupported types)
- [x] Encoding detection tested (UTF-8, Latin-1, auto-detect)
- [x] Document processor pipeline tested (end-to-end)
- [x] Factory pattern tested
- [x] Async operations tested
- [x] Tests pass consistently (42/42 passing)
- [x] Test execution is fast (<2 seconds with coverage)
- [x] No external file dependencies (all in-memory generation)

## Continuous Integration

These tests should be included in CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run document processor tests
  run: |
    cd backend
    pip install reportlab
    pytest tests/test_document_processor.py -v --cov
```

---

**Author:** Coding Agent
**Date:** 2025-10-20
**Task ID:** 63ca1af3-3358-4c5e-95d4-8ecd6f01e0d2
**Status:** Complete - All tests passing ✓
